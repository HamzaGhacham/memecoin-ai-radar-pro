"""GeckoTerminal new-pool read-only adapter and discovery prefilters."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from .models import Candidate
from .validation import is_valid_mint
from .transport import SourceError

GECKO_NEW_POOLS_TEMPLATE = "https://api.geckoterminal.com/api/v2/networks/solana/new_pools?page={page}"
GECKO_NEW_POOLS = GECKO_NEW_POOLS_TEMPLATE.format(page=1)
GECKO_TRENDING_POOLS_TEMPLATE = "https://api.geckoterminal.com/api/v2/networks/solana/trending_pools?duration=1h&page={page}"

def _number(value) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        v = Decimal(str(value))
        return v if v.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None

def _integer(value) -> int | None:
    try:
        v = int(value)
        return v if v >= 0 and str(value).strip() == str(v) else None
    except (ValueError, TypeError):
        return None

def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Pool timestamp has no timezone")
    return parsed.astimezone(timezone.utc)

def parse_new_pools(payload: dict, *, observed_at: datetime) -> list[Candidate]:
    """Never silently invent missing market fields or token identities."""
    if observed_at.tzinfo is None:
        raise ValueError("Observed time must have timezone")
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise SourceError("Unexpected GeckoTerminal response shape")
    candidates = []
    for row in payload["data"]:
        try:
            if not isinstance(row, dict):
                continue
            attr = row["attributes"]
            related = row["relationships"]["base_token"]["data"]["id"]
            # Example GeckoTerminal relationship ID: solana_<MINT>
            if not isinstance(related, str) or not related.startswith("solana_"):
                continue
            mint = related[len("solana_"):]
            if not is_valid_mint(mint):
                continue
            created = _time(attr["pool_created_at"])
            pool = attr.get("address") or row.get("id", "")
            if not isinstance(pool, str) or not pool:
                continue
            volume = attr.get("volume_usd") or {}
            txns = attr.get("transactions") or {}
            m5 = txns.get("m5") if isinstance(txns, dict) else None
            h1 = txns.get("h1") if isinstance(txns, dict) else None
            if not isinstance(m5, dict): m5 = {}
            if not isinstance(h1, dict): h1 = {}
            changes = attr.get("price_change_percentage")
            if not isinstance(changes, dict): changes = {}
            b5, s5 = _integer(m5.get("buys")), _integer(m5.get("sells"))
            b1, s1 = _integer(h1.get("buys")), _integer(h1.get("sells"))
            candidates.append(Candidate(
                mint=mint, pool=pool, dex=str(attr.get("dex_id", "unknown")),
                created_at=created, observed_at=observed_at.astimezone(timezone.utc),
                liquidity_usd=_number(attr.get("reserve_in_usd")),
                volume_5m_usd=_number(volume.get("m5") if isinstance(volume, dict) else None),
                volume_1h_usd=_number(volume.get("h1") if isinstance(volume, dict) else None),
                buys_5m=b5, sells_5m=s5,
                trades_1h=(b1 + s1) if b1 is not None and s1 is not None else None,
                price_change_1h_pct=_number(changes.get("h1")),
            ))
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    return candidates

def discovery_prefilter(candidate: Candidate, policy: dict) -> tuple[str, str]:
    """Only static preselection; full acceleration/security checks are still pending."""
    age = candidate.age_minutes
    if age < 0:
        return "HOLD_UNKNOWN", "Pool timestamp is in the future"
    if age < 360:
        scanner, limits = "EARLY", policy["discovery"]["early"]
    elif age <= 43200:
        scanner, limits = "MOMENTUM", policy["discovery"]["momentum"]
    else:
        return "INELIGIBLE_DISCOVERY", "Pool older than 30 days"
    if age < limits["age_min_minutes"] or age > limits["age_max_minutes"]:
        return "INELIGIBLE_DISCOVERY", f"{scanner}: pool age outside configured range"
    if candidate.liquidity_usd is None:
        return "HOLD_UNKNOWN", "Liquidity missing"
    if candidate.liquidity_usd < Decimal(limits["liquidity_usd_min"]):
        return "INELIGIBLE_DISCOVERY", f"{scanner}: liquidity below discovery floor"
    if scanner == "EARLY":
        tx = (candidate.buys_5m + candidate.sells_5m) if candidate.buys_5m is not None and candidate.sells_5m is not None else None
        if tx is None or candidate.volume_5m_usd is None:
            return "HOLD_UNKNOWN", "Missing 5-minute volume or trades"
        if candidate.volume_5m_usd < Decimal(limits["volume_5m_usd_min"]):
            return "INELIGIBLE_DISCOVERY", "EARLY: 5m volume below floor"
        if tx < limits["trades_5m_min"]:
            return "INELIGIBLE_DISCOVERY", "EARLY: 5m trades below floor"
        if not candidate.sells_5m:
            return "PENDING_HISTORY", "EARLY preselected: zero sells; ratio/acceleration need confirmation"
        if Decimal(candidate.buys_5m) / Decimal(candidate.sells_5m) < Decimal(str(limits["buy_sell_count_ratio_min"])):
            return "INELIGIBLE_DISCOVERY", "EARLY: buy/sell count ratio below floor"
    else:
        if candidate.trades_1h is None or candidate.volume_1h_usd is None or candidate.price_change_1h_pct is None:
            return "HOLD_UNKNOWN", "Missing 1-hour volume/trades/price change"
        if candidate.volume_1h_usd < Decimal(limits["volume_1h_usd_min"]):
            return "INELIGIBLE_DISCOVERY", "MOMENTUM: 1h volume below floor"
        if candidate.trades_1h < limits["trades_1h_min"]:
            return "INELIGIBLE_DISCOVERY", "MOMENTUM: 1h trades below floor"
        if candidate.price_change_1h_pct < Decimal(limits["price_change_1h_min_pct"]):
            return "INELIGIBLE_DISCOVERY", "MOMENTUM: 1h price change below floor"
    return "PENDING_HISTORY", f"{scanner} preselected; acceleration and 2 fresh observations not yet verified"


def select_live_candidates(transport, policy: dict, *, observed_at: datetime, limit: int) -> tuple[list[tuple[Candidate, str, str]], dict]:
    """Read a bounded number of new-pool pages; select *after* prefiltering.

    One source page contains up to 20 pools. It can be entirely younger than
    the configured age floor. This scanner only discovers preselected candidates:
    it does NOT confirm 2 scans, security, opportunity scores or safety.
    """
    if limit < 0:
        raise ValueError("Candidate limit cannot be negative")
    budget = policy["budget"]["geckoterminal_requests_per_run"]
    if not isinstance(budget, int) or isinstance(budget, bool) or not (1 <= budget <= 3):
        raise ValueError("GeckoTerminal page budget must be between 1 and 3")
    report = {"pages_requested": 0, "pages_ok": 0, "unique_tokens_seen": 0,
              "discovery_preselected": 0, "discovery_ineligible": 0,
              "discovery_unknown": 0, "partial_error": None}
    if limit == 0:
        return [], report
    by_mint: dict[str, Candidate] = {}
    for page in range(1, budget + 1):
        report["pages_requested"] += 1
        try:
            payload = transport.request(GECKO_NEW_POOLS_TEMPLATE.format(page=page))
            candidates = parse_new_pools(payload, observed_at=observed_at)
        except SourceError as exc:
            if page == 1:
                raise
            # Page 1 remains usable; never conceal a partial source failure.
            report["partial_error"] = str(exc)
            break
        report["pages_ok"] += 1
        for candidate in candidates:
            prev = by_mint.get(candidate.mint)
            # Multiple pools can share a mint. Prefer one that meets discovery
            # prefilters, then one with more verifiable USD liquidity.
            def priority(c):
                status, _ = discovery_prefilter(c, policy)
                return ({"PENDING_HISTORY": 2, "HOLD_UNKNOWN": 1}.get(status, 0),
                        c.liquidity_usd if c.liquidity_usd is not None else Decimal(-1))
            if prev is None or priority(candidate) > priority(prev):
                by_mint[candidate.mint] = candidate
        selected = [(c, *discovery_prefilter(c, policy)) for c in by_mint.values()]
        # Stop early when enough preselected candidates have been found.
        if sum(status == "PENDING_HISTORY" for _, status, _ in selected) >= limit:
            break
    evaluated = [(c, *discovery_prefilter(c, policy)) for c in by_mint.values()]
    report["unique_tokens_seen"] = len(evaluated)
    report["discovery_preselected"] = sum(status == "PENDING_HISTORY" for _, status, _ in evaluated)
    report["discovery_ineligible"] = sum(status == "INELIGIBLE_DISCOVERY" for _, status, _ in evaluated)
    report["discovery_unknown"] = sum(status == "HOLD_UNKNOWN" for _, status, _ in evaluated)
    # Input ordering is provider recency ordering; do not claim scored ranking.
    return [(c, status, detail) for c, status, detail in evaluated
            if status == "PENDING_HISTORY"][:limit], report


# Hybrid source coverage: one bounded request to New Pools and one to Trending
# Pools (subject to provider availability). Both feed the SAME strict policy.
def select_hybrid_candidates(transport, policy: dict, *, observed_at: datetime, limit: int) -> tuple[list[tuple[Candidate, str, str]], dict]:
    """Read-only dual-source candidate preselection with first-failure diagnostics.

    A low/zero candidate count is not evidence of an empty market or fraud.
    The API response can include multiple pools for one token. Historical
    confirmation and full security checks remain mandatory and unimplemented.
    """
    from collections import Counter
    if limit < 0:
        raise ValueError("Candidate limit cannot be negative")
    budget = policy["budget"]["geckoterminal_requests_per_run"]
    if isinstance(budget, bool) or not isinstance(budget, int) or not (1 <= budget <= 3):
        raise ValueError("GeckoTerminal request budget must be between 1 and 3")
    jobs = [("new_pools", GECKO_NEW_POOLS_TEMPLATE.format(page=1))]
    if budget >= 2:
        jobs.append(("trending_pools_1h", GECKO_TRENDING_POOLS_TEMPLATE.format(page=1)))
    if budget >= 3:
        # A third request can improve new-token age coverage without changing risk thresholds.
        jobs.append(("new_pools_page_2", GECKO_NEW_POOLS_TEMPLATE.format(page=2)))
    report = {
        "pages_requested": 0, "pages_ok": 0, "unique_tokens_seen": 0,
        "discovery_preselected": 0, "discovery_ineligible": 0,
        "discovery_unknown": 0, "partial_error": None,
        "sources_checked": [], "source_stats": {}, "first_failure_reasons": {},
        "raw_pool_rows": 0, "parsed_pool_rows": 0,
    }
    if limit == 0:
        return [], report
    by_mint: dict[str, Candidate] = {}
    failures=[]
    for source, url in jobs:
        report["pages_requested"] += 1
        try:
            payload = transport.request(url)
            candidates = parse_new_pools(payload, observed_at=observed_at)
        except SourceError as exc:
            failures.append(f"{source}: {exc}")
            report["source_stats"][source] = {"status": "SOURCE_ERROR"}
            continue
        report["pages_ok"] += 1
        report["sources_checked"].append(source)
        raw_rows = len(payload["data"])
        report["raw_pool_rows"] += raw_rows
        report["parsed_pool_rows"] += len(candidates)
        report["source_stats"][source] = {
            "status": "OK", "raw_pool_rows": raw_rows,
            "parsed_pool_rows": len(candidates)
        }
        for candidate in candidates:
            previous = by_mint.get(candidate.mint)
            def priority(c):
                status, _ = discovery_prefilter(c, policy)
                return ({"PENDING_HISTORY": 2, "HOLD_UNKNOWN": 1}.get(status, 0),
                        c.liquidity_usd if c.liquidity_usd is not None else Decimal(-1))
            if previous is None or priority(candidate) > priority(previous):
                by_mint[candidate.mint] = candidate
    if report["pages_ok"] == 0:
        raise SourceError("All GeckoTerminal sources failed: " + "; ".join(failures))
    report["partial_error"] = "; ".join(failures) if failures else None
    evaluated = [(c, *discovery_prefilter(c, policy)) for c in by_mint.values()]
    report["unique_tokens_seen"] = len(evaluated)
    report["discovery_preselected"] = sum(s == "PENDING_HISTORY" for _, s, _ in evaluated)
    report["discovery_ineligible"] = sum(s == "INELIGIBLE_DISCOVERY" for _, s, _ in evaluated)
    report["discovery_unknown"] = sum(s == "HOLD_UNKNOWN" for _, s, _ in evaluated)
    report["first_failure_reasons"] = dict(sorted(Counter(
        detail for _, status, detail in evaluated if status != "PENDING_HISTORY"
    ).items()))
    # Provider order is not a prediction or opportunity score. Do not claim ranking.
    selected = [(c, status, detail) for c, status, detail in evaluated if status == "PENDING_HISTORY"]
    return selected[:limit], report
