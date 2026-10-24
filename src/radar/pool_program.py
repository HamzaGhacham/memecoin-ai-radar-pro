"""Pool *program-owner* diagnostic only, NOT pool/vault/LP ownership verification.

Cross-check the RPC owner of a discovered pool account using the existing
getMultipleAccounts batch. An owner that matches an AMM program ID does NOT
prove the account is a valid pool or that its vaults / LP are safe.
"""
from .validation import is_valid_mint
from .pumpswap_layout import read_pumpswap_pool_data

# Documented on-chain mainnet AMM program IDs. Version the allowlist and
# distinguish unknown programs from malicious ones.
KNOWN_PROGRAMS = {
    'pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA': 'PUMPSWAP_AMM',
    'CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C': 'RAYDIUM_CPMM',
    'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK': 'RAYDIUM_CLMM',
    '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8': 'RAYDIUM_AMM_V4',
}


def inspect_pool_program(pool: str, largest_payload: dict | None, batched_payload: dict | None,
                         *, owner_batch_includes_pool: bool, expected_mint: str | None = None) -> dict:
    """Return diagnostic data, with L02/L07/L08 and W01/W02 ALWAYS UNKNOWN.

    The selected pool address is a provider claim. Verify existence and owner,
    but NOT pool type/state or token pair, vaults, withdrawal rights, liquidity.
    """
    def unknown(reason: str) -> dict:
        return {
            'status': 'UNKNOWN', 'reason': reason, 'pool_account_verified': False,
            'pool_vaults_classified': False, 'liquidity_withdrawal_verified': False,
            'l02_l07_l08_security_status': 'UNKNOWN', 'w01_w02_security_status': 'UNKNOWN',
        }

    if not is_valid_mint(pool):
        return unknown('GeckoTerminal pool address is not a valid 32-byte Solana public key')
    if not owner_batch_includes_pool:
        return unknown('Selected pool account not included in RPC batch')
    largest_result = largest_payload.get('result') if isinstance(largest_payload, dict) else None
    largest_rows = largest_result.get('value') if isinstance(largest_result, dict) else None
    if not isinstance(largest_rows, list) or not 1 <= len(largest_rows) <= 20:
        return unknown('Largest-token-accounts snapshot missing')
    if not isinstance(batched_payload, dict) or batched_payload.get('error') is not None:
        return unknown('Pool account RPC batch missing or failed')
    batched_result = batched_payload.get('result')
    rows = batched_result.get('value') if isinstance(batched_result, dict) else None
    if not isinstance(rows, list) or len(rows) != len(largest_rows) + 1:
        return unknown('Pool account batch length mismatch')
    slot_meta = batched_result.get('context') if isinstance(batched_result, dict) else None
    slot = slot_meta.get('slot') if isinstance(slot_meta, dict) else None
    largest_context = largest_result.get('context') if isinstance(largest_result, dict) else None
    largest_slot = largest_context.get('slot') if isinstance(largest_context, dict) else None
    if type(slot) is not int or type(largest_slot) is not int or slot < 0 or largest_slot < 0 or abs(slot - largest_slot) > 300:
        return unknown('Pool and largest-account snapshots lack compatible RPC slots')
    account = rows[-1]
    if account is None:
        return unknown('Selected pool account does not exist at the RPC slot')
    if not isinstance(account, dict):
        return unknown('Malformed pool account response')
    program_id = account.get('owner')
    if not is_valid_mint(program_id or ''):
        return unknown('Pool program owner missing or invalid')
    if account.get('executable') is not False:
        return unknown('Pool address is executable or executable flag missing')
    result = {
        'status': 'PROGRAM_RECOGNIZED_NOT_POOL_VERIFIED' if program_id in KNOWN_PROGRAMS else 'PROGRAM_UNRECOGNIZED',
        'pool_account_verified': True, 'pool_program_id': program_id,
        'program_family': KNOWN_PROGRAMS.get(program_id, 'UNKNOWN'),
        'pool_rpc_slot': slot, 'pool_layout_verified': False,
        'pool_vaults_classified': False, 'liquidity_withdrawal_verified': False,
        'l02_l07_l08_security_status': 'UNKNOWN', 'w01_w02_security_status': 'UNKNOWN',
        'note': 'Account existence and program-owner identity only. Pool layout, token pair, vaults, LP token controls and withdrawal rights NOT checked; not a security PASS.'
    }
    if program_id in KNOWN_PROGRAMS and KNOWN_PROGRAMS[program_id] == 'PUMPSWAP_AMM' and expected_mint is not None:
        parsed = read_pumpswap_pool_data(account.get('data'), expected_mint=expected_mint)
        result['pool_layout_diagnostics'] = parsed
        if parsed['status'] == 'POOL_LAYOUT_VERIFIED':
            side = parsed.get('candidate_token_side')
            result['status'] = ('POOL_LAYOUT_VERIFIED_QUOTE_TOKEN_VAULTS_UNCHECKED'
                                if side == 'QUOTE' else 'POOL_LAYOUT_VERIFIED_VAULTS_UNCHECKED')
            result['pool_layout_verified'] = True
            result['candidate_token_side'] = side
            result['unusual_pair_orientation'] = parsed.get('unusual_pair_orientation', False)
            # Compare the recorded vault address with already-fetched top token
            # account addresses; this does not verify vault mint/owner/state.
            candidate_vault = parsed['candidate_vault_address']
            matches = [i for i,row in enumerate(largest_rows) if isinstance(row, dict)
                       and row.get('address') == candidate_vault]
            result['vault_address_diagnostics'] = {
                'status': 'ADDRESS_MATCH_ONLY' if matches else 'NOT_OBSERVED_IN_TOP20',
                'recorded_candidate_vault_address': candidate_vault,
                'appears_in_largest_accounts': bool(matches),
                'rank_in_top20': (matches[0] + 1) if matches else None,
                'recorded_account_amount_raw': (largest_rows[matches[0]].get('amount') if matches else None),
                'vault_account_state_verified': False,
                'pool_vaults_classified': False,
                'note': 'Address-only comparison. Pool vault token account mint/authority/balance NOT independently validated.'
            }
        elif parsed['status'] == 'MINT_MISMATCH':
            result['status'] = 'POOL_TOKEN_PAIR_MISMATCH'
        # No decoded pool identity ever proves LP ownership or withdrawal safety.
    return result
