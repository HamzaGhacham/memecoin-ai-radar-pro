"""Read-only PumpSwap Pool identity decoder, sourced from the official Pump AMM IDL.

ONLY verify account structure and recorded addresses. Pool vault balances,
withdraw rights and LP lock/burn must be independently checked and remain UNKNOWN.
"""
import base64
import binascii
from .validation import ALPHABET, is_valid_mint

PUMPSWAP_POOL_DISCRIMINATOR = bytes([241,154,109,4,17,177,109,188])
WSOL_MINT = 'So11111111111111111111111111111111111111112'
# Anchor account discriminator (8), bump (1), index (2), then 6 Pubkeys (32 each), LP supply (8).
MIN_POOL_PREFIX_SIZE = 8 + 1 + 2 + 6 * 32 + 8


def pubkey_from_bytes(raw: bytes) -> str:
    if len(raw) != 32:
        raise ValueError('Pubkey must contain 32 bytes')
    n = int.from_bytes(raw, 'big')
    chars = ''
    while n:
        n, rem = divmod(n, 58)
        chars = ALPHABET[rem] + chars
    return ('1' * (len(raw) - len(raw.lstrip(b'\x00')))) + chars


def read_pumpswap_pool_data(account_data: object, *, expected_mint: str) -> dict:
    """Decode verified-structure identity only; never return a liquidity/security PASS.

    Unknown/new appended fields are ignored; any truncated/malformed prefix fails closed.
    """
    if not is_valid_mint(expected_mint):
        return {'status':'UNKNOWN', 'reason':'Invalid expected mint'}
    if not (isinstance(account_data, list) and len(account_data)==2
            and account_data[1]=='base64' and isinstance(account_data[0], str)):
        return {'status':'UNKNOWN', 'reason':'Pool binary data not available in base64'}
    try:
        blob = base64.b64decode(account_data[0], validate=True)
    except (ValueError,binascii.Error):
        return {'status':'UNKNOWN', 'reason':'Malformed pool base64 payload'}
    if len(blob) < MIN_POOL_PREFIX_SIZE:
        return {'status':'UNKNOWN', 'reason':'Pool account data truncated or unsupported'}
    if blob[:8] != PUMPSWAP_POOL_DISCRIMINATOR:
        return {'status':'UNKNOWN', 'reason':'Unexpected PumpSwap Pool discriminator'}
    index = int.from_bytes(blob[9:11], 'little')
    names = ('creator','base_mint','quote_mint','lp_mint','base_vault','quote_vault')
    keys = {name:pubkey_from_bytes(blob[11+i*32:11+(i+1)*32]) for i,name in enumerate(names)}
    if (any(not is_valid_mint(keys[n]) for n in names)
            or keys['base_mint']==keys['quote_mint']
            or keys['base_vault']==keys['quote_vault']
            or keys['lp_mint'] in (keys['base_mint'],keys['quote_mint'])):
        return {'status':'UNKNOWN', 'reason':'Pool identity fields invalid or contradictory'}
    # The discovery provider can select either side of a real AMM pair as the
    # candidate.  Never silently assume its base token is the on-chain base.
    # A quote-side candidate with WSOL as base is non-canonical for the usual
    # PumpSwap meme-token/SOL layout, but membership is not a scam verdict.
    if expected_mint not in (keys['base_mint'], keys['quote_mint']):
        return {'status':'MINT_MISMATCH',
                'reason':'Discovered token is not a member of the on-chain Pool pair; verify provider mapping',
                'onchain_base_mint':keys['base_mint'],'onchain_quote_mint':keys['quote_mint']}
    token_side = 'BASE' if expected_mint == keys['base_mint'] else 'QUOTE'
    orientation = ('STANDARD_WSOL_PAIR' if keys['quote_mint'] == WSOL_MINT else
                   'REVERSED_WSOL_PAIR' if keys['base_mint'] == WSOL_MINT else
                   'CUSTOM_PAIR')
    unusual = token_side == 'QUOTE'
    return {'status':'POOL_LAYOUT_VERIFIED', 'pool_index':index,
            'pool_creator':keys['creator'], 'base_mint':keys['base_mint'],
            'quote_mint':keys['quote_mint'], 'lp_mint':keys['lp_mint'],
            'base_vault_address':keys['base_vault'],'quote_vault_address':keys['quote_vault'],
            'candidate_token_side':token_side, 'pair_orientation':orientation,
            'unusual_pair_orientation':unusual,
            'candidate_vault_address':keys['base_vault'] if token_side == 'BASE' else keys['quote_vault'],
            'lp_supply_raw':str(int.from_bytes(blob[203:211], 'little')),
            'note':('On-chain Pool layout decoded; candidate is a pool member. '
                    'Token is on quote side; review non-canonical orientation. ' if unusual else
                    'On-chain Pool layout decoded; candidate is pool base mint. ')
                    + 'Vault state, reserves and LP withdrawal rights remain UNKNOWN.'}
