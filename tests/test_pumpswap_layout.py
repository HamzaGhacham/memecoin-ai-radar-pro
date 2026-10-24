"""v0.1.8 PumpSwap IDL account layout tests. No network, no trading."""
import base64
import unittest
from radar.pumpswap_layout import (WSOL_MINT, PUMPSWAP_POOL_DISCRIMINATOR, MIN_POOL_PREFIX_SIZE,
                                   read_pumpswap_pool_data, pubkey_from_bytes)
from radar.pool_program import inspect_pool_program
from test_pool_program import largest, owners, POOL, PUMPSWAP
from test_owner_cli import MINT, OTHER, AUTH
from radar.validation import ALPHABET


def to_bytes(key):
    n=0
    for c in key: n=n*58+ALPHABET.index(c)
    raw=n.to_bytes((n.bit_length()+7)//8,'big') if n else b''
    return b'\x00'*(len(key)-len(key.lstrip('1')))+raw


def pool_blob(base=MINT,quote=OTHER):
    # creator, base, quote, lp, base_vault, quote_vault
    keys=(AUTH,base,quote,POOL,AUTH,OTHER)
    return (PUMPSWAP_POOL_DISCRIMINATOR + b'\xfe' + (0).to_bytes(2,'little')
            + b''.join(to_bytes(k) for k in keys) + (123456).to_bytes(8,'little'))


def batch_with_pool(data):
    batch=owners()
    batch['result']['value'][-1]['data']=[base64.b64encode(data).decode(),'base64']
    return batch


class PumpSwapIdentityTests(unittest.TestCase):
    def test_size_and_discriminator(self):
        self.assertEqual(MIN_POOL_PREFIX_SIZE,211)
        self.assertEqual(len(PUMPSWAP_POOL_DISCRIMINATOR),8)

    def test_base58_roundtrip(self):
        for key in (MINT, OTHER, POOL,AUTH,'11111111111111111111111111111111'):
            self.assertEqual(pubkey_from_bytes(to_bytes(key)),key)

    def test_valid_pool_layout(self):
        r=read_pumpswap_pool_data([base64.b64encode(pool_blob()).decode(),'base64'], expected_mint=MINT)
        self.assertEqual(r['status'],'POOL_LAYOUT_VERIFIED')
        self.assertEqual(r['base_mint'],MINT)
        self.assertEqual(r['quote_mint'],OTHER)
        self.assertEqual(r['lp_supply_raw'],'123456')

    def test_quote_side_is_member_not_mismatch(self):
        r=read_pumpswap_pool_data([base64.b64encode(pool_blob()).decode(),'base64'],expected_mint=OTHER)
        self.assertEqual(r['status'],'POOL_LAYOUT_VERIFIED')
        self.assertEqual(r['candidate_token_side'],'QUOTE')
        self.assertTrue(r['unusual_pair_orientation'])
        self.assertEqual(r['candidate_vault_address'], OTHER)

    def test_true_mint_mismatch(self):
        r=read_pumpswap_pool_data([base64.b64encode(pool_blob()).decode(),'base64'],expected_mint=POOL)
        self.assertEqual(r['status'],'MINT_MISMATCH')

    def test_wsol_base_with_candidate_quote(self):
        r=read_pumpswap_pool_data([base64.b64encode(pool_blob(base=WSOL_MINT,quote=MINT)).decode(),'base64'], expected_mint=MINT)
        self.assertEqual(r['status'],'POOL_LAYOUT_VERIFIED')
        self.assertEqual(r['candidate_token_side'],'QUOTE')
        self.assertEqual(r['pair_orientation'],'REVERSED_WSOL_PAIR')

    def test_fail_closed_invalid_base64(self):
        self.assertEqual(read_pumpswap_pool_data(['invalid***','base64'],expected_mint=MINT)['status'],'UNKNOWN')

    def test_fail_closed_wrong_discriminator(self):
        blob=b'xxxxxxxx'+pool_blob()[8:]
        self.assertEqual(read_pumpswap_pool_data([base64.b64encode(blob).decode(),'base64'],expected_mint=MINT)['status'],'UNKNOWN')

    def test_fail_closed_truncated(self):
        r=read_pumpswap_pool_data([base64.b64encode(pool_blob()[:-1]).decode(),'base64'],expected_mint=MINT)
        self.assertEqual(r['status'],'UNKNOWN')

    def test_fail_closed_unparsed_rpc_data(self):
        self.assertEqual(read_pumpswap_pool_data({'parsed':{}},expected_mint=MINT)['status'],'UNKNOWN')

    def test_pool_program_still_no_liquidity_pass(self):
        r=inspect_pool_program(POOL,largest(),batch_with_pool(pool_blob()),
                owner_batch_includes_pool=True,expected_mint=MINT)
        self.assertTrue(r['pool_layout_verified'])
        self.assertEqual(r['status'],'POOL_LAYOUT_VERIFIED_VAULTS_UNCHECKED')
        self.assertEqual(r['pool_layout_diagnostics']['base_vault_address'],AUTH)
        self.assertFalse(r['pool_vaults_classified'])
        self.assertFalse(r['liquidity_withdrawal_verified'])
        self.assertEqual(r['l02_l07_l08_security_status'],'UNKNOWN')
        self.assertEqual(r['w01_w02_security_status'],'UNKNOWN')

    def test_onchain_vault_address_matches_top20_without_security_pass(self):
        # The recorded quote vault is OTHER, which is the second raw account.
        # Address matching does NOT verify LP/vault safety.
        blob=pool_blob(base=OTHER, quote=MINT)
        r=inspect_pool_program(POOL,largest(),batch_with_pool(blob),
                owner_batch_includes_pool=True,expected_mint=MINT)
        self.assertTrue(r['pool_layout_verified'])
        self.assertEqual(r['candidate_token_side'], 'QUOTE')
        self.assertTrue(r['vault_address_diagnostics']['appears_in_largest_accounts'])
        self.assertEqual(r['vault_address_diagnostics']['rank_in_top20'], 2)  # quote_vault is OTHER
        self.assertFalse(r['vault_address_diagnostics']['vault_account_state_verified'])
        self.assertFalse(r['pool_vaults_classified'])
        self.assertEqual(r['l02_l07_l08_security_status'], 'UNKNOWN')

    def test_reversed_wsol_pool_vault_matches_top1_without_wallet_pass(self):
        # Candidate is OTHER on quote side; recorded quote vault is the first
        # largest token account MINT. Address matching alone is not vault proof.
        blob = bytearray(pool_blob(base=WSOL_MINT, quote=OTHER))
        blob[11 + 5 * 32:11 + 6 * 32] = to_bytes(MINT)
        r=inspect_pool_program(POOL, largest(), batch_with_pool(bytes(blob)),
            owner_batch_includes_pool=True,expected_mint=OTHER)
        self.assertEqual(r['status'], 'POOL_LAYOUT_VERIFIED_QUOTE_TOKEN_VAULTS_UNCHECKED')
        self.assertEqual(r['pool_layout_diagnostics']['pair_orientation'], 'REVERSED_WSOL_PAIR')
        self.assertEqual(r['vault_address_diagnostics']['rank_in_top20'], 1)
        self.assertFalse(r['pool_vaults_classified'])
        self.assertEqual(r['w01_w02_security_status'], 'UNKNOWN')
        self.assertEqual(r['l02_l07_l08_security_status'], 'UNKNOWN')

    def test_vault_outside_top20_is_just_not_observed(self):
        blob=pool_blob(base=MINT, quote=OTHER)
        r=inspect_pool_program(POOL, largest(), batch_with_pool(blob),
            owner_batch_includes_pool=True,expected_mint=MINT)
        self.assertFalse(r['vault_address_diagnostics']['appears_in_largest_accounts'])
        self.assertEqual(r['vault_address_diagnostics']['status'], 'NOT_OBSERVED_IN_TOP20')
        self.assertIsNone(r['vault_address_diagnostics']['rank_in_top20'])
        self.assertEqual(r['w01_w02_security_status'], 'UNKNOWN')

    def test_non_member_still_mismatch(self):
        r=inspect_pool_program(POOL,largest(),batch_with_pool(pool_blob()),
                owner_batch_includes_pool=True,expected_mint=POOL)
        self.assertEqual(r['status'], 'POOL_TOKEN_PAIR_MISMATCH')
        self.assertFalse(r['pool_layout_verified'])

    def test_program_id_only_still_not_pass(self):
        r=inspect_pool_program(POOL,largest(),owners(),owner_batch_includes_pool=True,expected_mint=MINT)
        self.assertFalse(r['pool_layout_verified'])
        self.assertEqual(r['l02_l07_l08_security_status'],'UNKNOWN')

    def test_quote_side_not_false_mismatch_and_not_security_pass(self):
        r=inspect_pool_program(POOL,largest(),batch_with_pool(pool_blob()),
                owner_batch_includes_pool=True,expected_mint=OTHER)
        self.assertEqual(r['status'],'POOL_LAYOUT_VERIFIED_QUOTE_TOKEN_VAULTS_UNCHECKED')
        self.assertTrue(r['pool_layout_verified'])
        self.assertTrue(r['unusual_pair_orientation'])
        self.assertEqual(r['l02_l07_l08_security_status'],'UNKNOWN')

if __name__=='__main__': unittest.main()
