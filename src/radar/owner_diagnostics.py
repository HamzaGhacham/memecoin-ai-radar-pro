"""Optional read-only token-account authority aggregation.

Only aggregates owners among the 20 LARGEST token accounts, not all token
accounts held by a wallet. Unidentified pool vaults and escrow prevent security
PASS. No signing, trading or sensitive credential output.
"""
from collections import defaultdict
from decimal import Decimal
from .holders import _amount, _percent
from .validation import is_valid_mint
from .security import TOKEN_CLASSIC, TOKEN_2022


def owner_accounts_request(largest_payload: dict, pool_address: str | None = None) -> dict:
    """One batched RPC call to resolve parsed owners (up to 20 accounts)."""
    result = largest_payload.get("result") if isinstance(largest_payload, dict) else None
    rows = result.get("value") if isinstance(result, dict) else None
    if not isinstance(rows, list) or not (1 <= len(rows) <= 20):
        raise ValueError("Largest-account response missing or invalid")
    addresses = [r.get("address") if isinstance(r, dict) else None for r in rows]
    if any(not isinstance(x, str) or not is_valid_mint(x) for x in addresses) or len(addresses) != len(set(addresses)):
        raise ValueError("Token-account addresses invalid or duplicated")
    if pool_address is not None:
        if not is_valid_mint(pool_address) or pool_address in addresses:
            raise ValueError("Invalid pool address or pool address duplicates top token account")
        addresses.append(pool_address)
    # A minimum context slot prevents silently reading an older account state.
    # It does NOT guarantee that balances match a prior getTokenLargestAccounts snapshot.
    config = {"encoding": "jsonParsed", "commitment": "confirmed"}
    slot = result.get("context", {}).get("slot") if isinstance(result.get("context"), dict) else None
    if type(slot) is int and slot >= 0:
        config["minContextSlot"] = slot
    return {"jsonrpc": "2.0", "id": 3, "method": "getMultipleAccounts", "params": [addresses, config]}


def inspect_observed_owners(mint: str, mint_payload: dict, largest_payload: dict, owners_payload: dict | None, *, expect_pool: bool = False) -> dict:
    """Group the observed top accounts by authority; never declare W01/W02 PASS.

    Any parsing uncertainty or mismatching balances/slots yields UNKNOWN.
    Percentages include *unclassified* LP vaults or escrows and are diagnostics,
    NOT verified wallet ownership percentages.
    """
    def unknown(reason, code="UNSPECIFIED", **details):
        # All failure results remain fail-closed, with stable machine-readable
        # diagnostic codes; do not expose RPC endpoint URLs or credentials.
        return {"status": "UNKNOWN", "error_code": code, "reason": reason,
                "wallet_concentration_verified": False,
                "w01_w02_security_status": "UNKNOWN", **details}
    mint_result = mint_payload.get("result") if isinstance(mint_payload, dict) else None
    mint_value = mint_result.get("value") if isinstance(mint_result, dict) else None
    mint_owner = mint_value.get("owner") if isinstance(mint_value, dict) else None
    mint_data = mint_value.get("data") if isinstance(mint_value, dict) else None
    parsed_mint = mint_data.get("parsed") if isinstance(mint_data, dict) else None
    mint_info = parsed_mint.get("info") if isinstance(parsed_mint, dict) and parsed_mint.get("type") == "mint" else None
    supply = _amount(mint_info.get("supply")) if isinstance(mint_info, dict) else None
    if supply is None or supply == 0 or mint_owner not in (TOKEN_CLASSIC, TOKEN_2022):
        return unknown("Mint supply or token program unverified", "MINT_UNVERIFIED")
    largest_result = largest_payload.get("result") if isinstance(largest_payload, dict) else None
    largest = largest_result.get("value") if isinstance(largest_result, dict) else None
    if not isinstance(largest, list) or not (1 <= len(largest) <= 20):
        return unknown("Largest accounts unavailable", "LARGEST_ACCOUNTS_UNAVAILABLE")
    if not isinstance(owners_payload, dict) or "error" in owners_payload:
        return unknown("getMultipleAccounts RPC returned error or no response", "OWNER_RPC_UNAVAILABLE")
    owner_result = owners_payload.get("result")
    accounts = owner_result.get("value") if isinstance(owner_result, dict) else None
    if not isinstance(accounts, list) or len(accounts) != len(largest) + (1 if expect_pool else 0):
        return unknown("Owner account responses missing or incomplete", "OWNER_BATCH_INCOMPLETE",
                       expected=len(largest) + (1 if expect_pool else 0), received=len(accounts) if isinstance(accounts, list) else None)
    # The optional last item can be a pool account. Never aggregate it as
    # a token account authority; pool_program.inspect_pool_program handles it.
    accounts = accounts[:len(largest)]
    contexts = [r.get("context") if isinstance(r, dict) else None for r in (mint_result,largest_result,owner_result)]
    slots = [r.get("slot") if isinstance(r, dict) else None for r in contexts]
    if any(type(s) is not int or s < 0 for s in slots) or max(slots)-min(slots)>300:
        return unknown("RPC slots missing or too far apart", "RPC_SLOT_DIVERGENCE", rpc_slots=slots)
    groups = defaultdict(int)
    counts = defaultdict(int)
    observed_sum = 0
    addresses = set()
    balance_drift_count = 0
    for orig,account in zip(largest, accounts):
        if not isinstance(orig,dict) or not is_valid_mint(orig.get("address", "")) or not isinstance(account,dict):
            return unknown("Invalid or closed token account", "ACCOUNT_MISSING_OR_INVALID", rpc_slots=slots)
        address = orig["address"]
        if address in addresses: return unknown("Duplicate token account", "DUPLICATE_ACCOUNT", rpc_slots=slots)
        addresses.add(address)
        parsed_container = account.get("data")
        parsed = parsed_container.get("parsed") if isinstance(parsed_container,dict) else None
        info = parsed.get("info") if isinstance(parsed,dict) and parsed.get("type") == "account" else None
        token_amount = info.get("tokenAmount") if isinstance(info,dict) else None
        authority = info.get("owner") if isinstance(info,dict) else None
        amount = _amount(orig.get("amount"))
        amount2 = _amount(token_amount.get("amount")) if isinstance(token_amount,dict) else None
        if account.get("owner") != mint_owner:
            return unknown("Token account belongs to unexpected token program", "TOKEN_PROGRAM_MISMATCH", rpc_slots=slots)
        if not isinstance(info, dict):
            return unknown("Token account data missing or not parsed", "UNPARSED_TOKEN_ACCOUNT", rpc_slots=slots)
        if info.get("mint") != mint:
            return unknown("Token account mint does not match candidate", "TOKEN_MINT_MISMATCH", rpc_slots=slots)
        if not is_valid_mint(authority or ""):
            return unknown("Token account authority is missing or invalid", "OWNER_AUTHORITY_INVALID", rpc_slots=slots)
        if amount is None or amount2 is None:
            return unknown("Token account amount is missing or invalid", "TOKEN_AMOUNT_INVALID", rpc_slots=slots)
        if amount != amount2:
            balance_drift_count += 1
        # Only include exact-balance-consistent observations in aggregation.
        # Any drift invalidates the entire grouping for concentration purposes.
        groups[authority] += amount2
        counts[authority] += 1
        observed_sum += amount2
    if balance_drift_count:
        return unknown("Token account balances changed between independent RPC snapshots; refresh is required",
                       "ACCOUNT_BALANCE_DRIFT", balance_mismatch_count=balance_drift_count,
                       rpc_slots=slots)

    if observed_sum > supply:
        return unknown("Observed balances exceed mint supply", "SUPPLY_INCONSISTENT", rpc_slots=slots)
    grouped = sorted(groups.values(),reverse=True)
    return {"status":"OBSERVED_ACCOUNT_AUTHORITIES_ONLY",
            "unique_authorities_in_top_accounts": len(groups),
            "accounts_observed": len(accounts),
            "authorities_with_multiple_top_accounts": sum(c>1 for c in counts.values()),
            "top_1_observed_authority_pct":_percent(grouped[0],supply),
            "top_10_observed_authorities_pct":_percent(sum(grouped[:10]),supply),
            "observed_accounts_supply_pct":_percent(observed_sum,supply),
            "owner_rpc_slot": slots[2],"pool_vaults_classified":False,
            "wallet_concentration_verified":False,"w01_w02_security_status":"UNKNOWN",
            "note":"Top-20 TOKEN ACCOUNT authorities only; unclassified pool vaults, custodians, PDAs and accounts outside top20. Not a verified wallet distribution; W01/W02 remain UNKNOWN."}
