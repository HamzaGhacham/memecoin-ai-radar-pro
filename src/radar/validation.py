"""Validate Solana public mint addresses as 32-byte Base58 keys."""
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def is_valid_mint(value: str) -> bool:
    if not isinstance(value, str) or len(value) < 32 or len(value) > 44:
        return False
    n = 0
    for c in value:
        idx = ALPHABET.find(c)
        if idx == -1:
            return False
        n = n * 58 + idx
    raw_len = (n.bit_length() + 7) // 8
    leading_zero = len(value) - len(value.lstrip("1"))
    return leading_zero + raw_len == 32
