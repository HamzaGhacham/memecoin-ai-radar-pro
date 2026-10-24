"""Fail-closed Solana mint permission checks. Full strict security gate is future work."""
from .models import CheckStatus, RuleCheck, SecurityDecision, SecurityEvaluation
from .validation import is_valid_mint

TOKEN_CLASSIC = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

# Until on-chain LP / distribution / execution adapters are implemented,
# these checks MUST remain UNKNOWN and every candidate MUST remain on HOLD.
MANDATORY_CHECKS = ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "L02", "L07", "L08", "W01", "W02", "T01", "T04")


def _check(code: str, status: CheckStatus, explanation: str) -> RuleCheck:
    return RuleCheck(code=code, status=status, explanation=explanation, source="solana_rpc" if code.startswith("C") else "not_implemented")

# Extension names observed in Solana getAccountInfo(jsonParsed) mint responses.
# Treat unsupported/new names as UNKNOWN; informational names are NOT a claim
# that the project's metadata, team or website is trustworthy.
INFORMATIONAL_EXTENSIONS = frozenset({
    "metadataPointer", "tokenMetadata", "mintCloseAuthority",
    "groupPointer", "groupMemberPointer", "tokenGroup", "tokenGroupMember",
})
SENSITIVE_EXTENSIONS = frozenset({
    "permanentDelegate", "nonTransferable", "defaultAccountState",
    "pausable", "transferHook", "transferFeeConfig",
})


def _parse_bp(value):
    # RPC JSON numbers are sometimes integers and sometimes decimal strings.
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    try:
        number = int(value)
    except ValueError:
        return None
    return number if 0 <= number <= 10000 and str(value).strip() == str(number) else None


def _extension_checks(info: dict) -> dict[str, RuleCheck]:
    codes = ("C03", "C04", "C05", "C06", "C07", "C08", "C09")
    if "extensions" not in info or not isinstance(info["extensions"], list):
        return {code: _check(code, CheckStatus.UNKNOWN,
                "Token-2022 extension inventory absent/unparsed") for code in codes}

    records = info["extensions"]
    checks = {code: _check(code, CheckStatus.NOT_APPLICABLE,
                          "Explicit parsed extension inventory: extension absent") for code in codes}
    seen = set()
    bad = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("extension"), str):
            bad.append("malformed entry")
            continue
        kind = record["extension"]
        if kind in seen:
            bad.append("duplicate: " + kind)
            continue
        seen.add(kind)
        state = record.get("state")
        if kind == "permanentDelegate":
            checks["C03"] = _check("C03", CheckStatus.HARD_REJECT,
                            "Permanent delegate extension present: policy exclusion")
        elif kind == "nonTransferable":
            checks["C04"] = _check("C04", CheckStatus.HARD_REJECT,
                            "Non-transferable token extension present")
        elif kind == "defaultAccountState":
            value = state.get("accountState") if isinstance(state, dict) else None
            if isinstance(value, str) and value.lower() == "frozen":
                status, reason = CheckStatus.HARD_REJECT, "New token accounts default to frozen"
            elif isinstance(value, str) and value.lower() in {"initialized", "uninitialized"}:
                status, reason = CheckStatus.WARNING, "Default account-state extension present; verify account behavior"
            else:
                status, reason = CheckStatus.UNKNOWN, "Default account state missing or unsupported"
            checks["C05"] = _check("C05", status, reason)
        elif kind == "pausable":
            checks["C06"] = _check("C06", CheckStatus.HARD_REJECT,
                            "Pausable extension present: transfers may be stopped")
        elif kind == "transferHook":
            checks["C07"] = _check("C07", CheckStatus.HARD_REJECT,
                            "Transfer Hook present; no audited allowlist available")
        elif kind == "transferFeeConfig":
            if not isinstance(state, dict):
                checks["C08"] = _check("C08", CheckStatus.UNKNOWN,
                                "Transfer fee state unreadable")
                continue
            authority = state.get("transferFeeConfigAuthority", "MISSING")
            old = state.get("olderTransferFee")
            new = state.get("newerTransferFee")
            old_bp = _parse_bp(old.get("transferFeeBasisPoints")) if isinstance(old, dict) else None
            new_bp = _parse_bp(new.get("transferFeeBasisPoints")) if isinstance(new, dict) else None
            if authority == "MISSING" or old_bp is None or new_bp is None:
                checks["C08"] = _check("C08", CheckStatus.UNKNOWN,
                            "Transfer fee authority or epoch fee schedule missing")
            elif isinstance(authority, str) and authority:
                checks["C08"] = _check("C08", CheckStatus.HARD_REJECT,
                            "Mutable fee authority can increase future transfer fees")
            elif authority is not None:
                checks["C08"] = _check("C08", CheckStatus.UNKNOWN,
                            "Invalid fee authority representation")
            elif max(old_bp, new_bp) > 500:
                checks["C08"] = _check("C08", CheckStatus.HARD_REJECT,
                            f"Configured transfer fee exceeds 5% (max {max(old_bp,new_bp)} bps)")
            elif max(old_bp, new_bp) > 100:
                checks["C08"] = _check("C08", CheckStatus.WARNING,
                            f"Transfer fee above 1% (max {max(old_bp,new_bp)} bps)")
            else:
                checks["C08"] = _check("C08", CheckStatus.WARNING if max(old_bp,new_bp) > 0 else CheckStatus.PASS,
                            f"Fixed transfer fee schedule, max {max(old_bp,new_bp)} bps; max-fee cap and sell execution not tested")
        elif kind not in INFORMATIONAL_EXTENSIONS:
            bad.append("unsupported: " + kind)
    if bad:
        checks["C09"] = _check("C09", CheckStatus.UNKNOWN,
                 "Unrecognized/malformed/duplicate extension inventory: " + ", ".join(bad[:8]))
    return checks


def evaluate_mint_rpc(mint: str, rpc_payload: dict | None) -> SecurityEvaluation:
    """Assess on-chain parsed mint, never claim a full security pass."""
    if not is_valid_mint(mint):
        raise ValueError("Invalid mint address: must be a 32-byte Base58 key")
    checks: dict[str, RuleCheck] = {code: _check(code, CheckStatus.UNKNOWN, "Required check not implemented or evidence unavailable") for code in MANDATORY_CHECKS}
    result = rpc_payload.get("result") if isinstance(rpc_payload, dict) else None
    data = result.get("value") if isinstance(result, dict) else None
    if not isinstance(data, dict):
        checks["C10"] = _check("C10", CheckStatus.UNKNOWN, "Solana mint account data missing")
    elif data.get("owner") not in (TOKEN_CLASSIC, TOKEN_2022):
        checks["C10"] = _check("C10", CheckStatus.HARD_REJECT, "Account is not owned by an accepted Solana token program")
    else:
        program = data["owner"]
        parsed = data.get("data", {}).get("parsed", {}) if isinstance(data.get("data"), dict) else {}
        info = parsed.get("info") if isinstance(parsed, dict) else None
        if not isinstance(info, dict) or parsed.get("type") != "mint":
            checks["C10"] = _check("C10", CheckStatus.UNKNOWN, "Unparsed or unsupported mint format")
        else:
            checks["C10"] = _check("C10", CheckStatus.PASS, "Validated token program and parsed mint account")
            for code, field in (("C01", "mintAuthority"), ("C02", "freezeAuthority")):
                if field not in info:
                    checks[code] = _check(code, CheckStatus.UNKNOWN, f"Missing parsed {field} field")
                elif info[field] is None:
                    checks[code] = _check(code, CheckStatus.PASS, f"{field} revoked")
                elif isinstance(info[field], str) and info[field]:
                    checks[code] = _check(code, CheckStatus.HARD_REJECT, f"Active {field} (policy exclusion; not proof of fraud)")
                else:
                    checks[code] = _check(code, CheckStatus.UNKNOWN, f"Invalid {field} value")
            if program == TOKEN_CLASSIC:
                for code in ("C03","C04","C05","C06","C07","C08","C09"):
                    checks[code] = _check(code, CheckStatus.NOT_APPLICABLE, "Token-2022 extension rule does not apply to classic SPL Token")
            else:
                checks.update(_extension_checks(info))
    result = tuple(checks[k] for k in MANDATORY_CHECKS)
    decision = (SecurityDecision.REJECT_SECURITY if any(c.status == CheckStatus.HARD_REJECT for c in result)
                else SecurityDecision.HOLD_UNKNOWN)
    return SecurityEvaluation(mint=mint, decision=decision, checks=result,
                              risk_score=None, data_coverage_pct=None, mandatory_complete=False)

def get_account_info_request(mint: str) -> dict:
    if not is_valid_mint(mint):
        raise ValueError("Invalid Solana address")
    return {"jsonrpc":"2.0", "id":1, "method":"getAccountInfo", "params":[mint,{"encoding":"jsonParsed", "commitment":"confirmed"}]}
