"""Read-only largest token-account concentration diagnostic.

This is deliberately NOT a holder/wallet security check: pool vaults, burn
accounts, token-account owners and clusters are not classified here. W01/W02
stay UNKNOWN until these are verified. No transaction signing or trading.
"""
from decimal import Decimal, ROUND_HALF_UP
from .validation import is_valid_mint

MAX_RAW_AMOUNT = 2**64 - 1


def largest_accounts_request(mint: str) -> dict:
    if not is_valid_mint(mint):
        raise ValueError("Invalid Solana mint address")
    return {"jsonrpc": "2.0", "id": 2, "method": "getTokenLargestAccounts",
            "params": [mint, {"commitment": "confirmed"}]}


def _amount(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or len(value) > 20:
        return None
    parsed = int(value)
    if parsed > MAX_RAW_AMOUNT:
        return None
    return parsed


def _percent(raw: int, supply: int) -> str:
    return str((Decimal(raw) * 100 / Decimal(supply)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _unknown(reason: str) -> dict:
    return {"status": "UNKNOWN", "reason": reason,
            "wallet_concentration_verified": False,
            "w01_w02_security_status": "UNKNOWN"}


def inspect_raw_account_concentration(mint_payload: dict | None, largest_payload: dict | None) -> dict:
    """Calculate raw largest-account shares without ever declaring W01/W02 PASS.

    Supply is read from the SAME previous getAccountInfo mint payload to avoid
    an unnecessary third RPC request. Slots are reported, not silently equated.
    """
    if not isinstance(mint_payload, dict) or "error" in mint_payload:
        return _unknown("Mint RPC response absent or failed")
    mint_result = mint_payload.get("result")
    mint_value = mint_result.get("value") if isinstance(mint_result, dict) else None
    parsed = (mint_value.get("data") or {}).get("parsed") if isinstance(mint_value, dict) and isinstance(mint_value.get("data"), dict) else None
    mint_info = parsed.get("info") if isinstance(parsed, dict) and parsed.get("type") == "mint" else None
    supply = _amount(mint_info.get("supply")) if isinstance(mint_info, dict) else None
    if supply is None or supply == 0:
        return _unknown("Mint raw supply missing, zero or invalid")
    if not isinstance(largest_payload, dict) or "error" in largest_payload:
        return _unknown("getTokenLargestAccounts response missing or contains RPC error")
    result = largest_payload.get("result")
    accounts = result.get("value") if isinstance(result, dict) else None
    if not isinstance(accounts, list) or not 1 <= len(accounts) <= 20:
        return _unknown("Largest accounts list invalid or empty")
    seen = set()
    balances = []
    for entry in accounts:
        if not isinstance(entry, dict) or not is_valid_mint(entry.get("address", "")):
            return _unknown("Largest token account address invalid")
        address = entry["address"]
        amount = _amount(entry.get("amount"))
        if address in seen or amount is None or amount > supply:
            return _unknown("Largest accounts are duplicated or amounts invalid")
        seen.add(address)
        balances.append(amount)
    if balances != sorted(balances, reverse=True) or sum(balances) > supply:
        return _unknown("Largest account balances inconsistent with mint supply")
    mint_ctx = mint_result.get("context") if isinstance(mint_result, dict) else None
    top_ctx = result.get("context") if isinstance(result, dict) else None
    mint_slot = mint_ctx.get("slot") if isinstance(mint_ctx, dict) else None
    top_slot = top_ctx.get("slot") if isinstance(top_ctx, dict) else None
    if any(not isinstance(s, int) or isinstance(s, bool) or s < 0 for s in (mint_slot, top_slot)):
        return _unknown("RPC slots unavailable; cannot validate snapshot consistency")
    if abs(mint_slot - top_slot) > 300:
        return _unknown("RPC snapshots too far apart (>300 slots)")
    top_one_pct = _percent(balances[0], supply)
    top_ten_pct = _percent(sum(balances[:10]), supply)
    raw_flags = []
    if Decimal(top_one_pct) > 15:
        raw_flags.append("RAW_TOP1_ACCOUNT_ABOVE_15_PCT")
    if Decimal(top_ten_pct) > 40:
        raw_flags.append("RAW_TOP10_ACCOUNTS_ABOVE_40_PCT")
    return {"status": "RAW_ACCOUNTS_ONLY", "top_1_token_account_pct": top_one_pct,
            "top_10_token_accounts_pct": top_ten_pct, "accounts_observed": len(balances),
            "mint_rpc_slot": mint_slot, "largest_accounts_rpc_slot": top_slot,
            "raw_flags": raw_flags, "wallet_concentration_verified": False,
            "w01_w02_security_status": "UNKNOWN",
            "note": "Not adjusted for pool vaults, burn/escrow accounts, or multiple token accounts owned by one wallet; not suitable for PASS or wallet-cluster claims"}
