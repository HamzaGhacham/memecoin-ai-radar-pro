"""Safe CLI: demo or bounded read-only verification. Never sends trading orders or alerts."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import os
import sys
from .discovery import parse_new_pools, discovery_prefilter, select_hybrid_candidates
from .security import get_account_info_request, evaluate_mint_rpc, TOKEN_CLASSIC
from .holders import largest_accounts_request, inspect_raw_account_concentration
from .owner_diagnostics import owner_accounts_request, inspect_observed_owners
from .pool_program import inspect_pool_program
from .transport import JsonTransport, SourceError
from .validation import is_valid_mint

POLICY = Path(__file__).resolve().parents[2] / "config" / "policy.v1.json"

# Demo only. This is a syntactically valid Solana public key, not a real memecoin.
DEMO_MINT = "11111111111111111111111111111111"

def _demo_payload(now: datetime) -> dict:
    created = (now - timedelta(minutes=20)).isoformat()
    return {"data":[{"attributes":{"address":"demo-pool-address", "pool_created_at":created,
       "reserve_in_usd":"21000", "volume_usd":{"m5":"4800","h1":"19000"},
       "transactions":{"m5":{"buys":19,"sells":9},"h1":{"buys":65,"sells":32}},
       "price_change_percentage":{"h1":"11.0"}},
       "relationships":{"base_token":{"data":{"id":"solana_"+DEMO_MINT}}}}]}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="MemeCoin AI Radar Pro: read-only Stage 1 proof of concept")
    parser.add_argument("--mode", choices=("demo","live"), default="demo")
    parser.add_argument("--rpc-check", action="store_true", help="Perform limited read-only Solana mint RPC lookups in live mode")
    parser.add_argument("--max-candidates", type=int, default=2)
    parser.add_argument("--holder-check", action="store_true", help="Read-only raw top token account diagnostic (not a holder security PASS)")
    parser.add_argument("--owner-check", action="store_true", help="Resolve authorities of top token accounts via one extra read-only batched RPC request")
    parser.add_argument("--pool-check", action="store_true", help="Inspect discovered pool program owner in same owner-account RPC batch; NOT vault/LP verification")
    args = parser.parse_args(argv)
    if args.pool_check and not args.owner_check:
        parser.error("--pool-check requires --owner-check --holder-check --rpc-check --mode live")
    if args.owner_check and not args.holder_check:
        parser.error("--owner-check requires --holder-check --rpc-check --mode live")
    if args.holder_check and (not args.rpc_check or args.mode != "live"):
        parser.error("--holder-check requires --mode live --rpc-check")
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    limit = min(max(args.max_candidates, 0), policy["budget"]["max_candidates_per_run"])
    now = datetime.now(timezone.utc)
    transport = JsonTransport()
    if args.mode == "live":
        try:
            selected, report = select_hybrid_candidates(transport, policy, observed_at=now, limit=limit)
        except SourceError as exc:
            print(json.dumps({"source":"geckoterminal", "status":"SOURCE_UNAVAILABLE", "reason":str(exc)}))
            return 2
    else:
        pools = _demo_payload(now)
        candidates = parse_new_pools(pools, observed_at=now)[:limit]
        selected = [(c, *discovery_prefilter(c, policy)) for c in candidates]
        report = {"pages_requested":0, "pages_ok":0, "unique_tokens_seen":len(candidates),
                  "discovery_preselected":sum(s == "PENDING_HISTORY" for _,s,_ in selected),
                  "discovery_ineligible":sum(s == "INELIGIBLE_DISCOVERY" for _,s,_ in selected),
                  "discovery_unknown":sum(s == "HOLD_UNKNOWN" for _,s,_ in selected),
                  "partial_error":None, "sources_checked":[], "source_stats":{},
                  "first_failure_reasons":{}, "raw_pool_rows":len(candidates),
                  "parsed_pool_rows":len(candidates)}
    print(json.dumps({"stage":"STAGE1_READ_ONLY", "mode":args.mode, "candidates":len(selected),
                      "source_pages":report["pages_ok"], "unique_tokens_seen":report["unique_tokens_seen"],
                      "discovery_preselected":report["discovery_preselected"],
                      "discovery_ineligible":report["discovery_ineligible"],
                      "discovery_unknown":report["discovery_unknown"],
                      "partial_source_error":report["partial_error"],
                      "sources_checked":report.get("sources_checked", []),
                      "source_stats":report.get("source_stats", {}),
                      "first_failure_reasons":report.get("first_failure_reasons", {}),
                      "raw_pool_rows":report.get("raw_pool_rows", 0),
                      "parsed_pool_rows":report.get("parsed_pool_rows", 0),
                      "live_opportunity_alerts_enabled":False, "reason":"Mandatory security checks not yet implemented"}))
    rpc_budget = max(0, int(policy["budget"]["rpc_requests_per_run"]))
    rpc_used = 0
    # Reserve RPC budget for basic mint checks FIRST; then use any remaining
    # budget for optional holder diagnostics. Never starve contract security.
    mint_responses = {}
    for c, _, _ in selected:
        if args.mode == "live" and args.rpc_check and is_valid_mint(c.mint) and rpc_used < rpc_budget:
            rpc_used += 1
            try:
                mint_responses[c.mint] = transport.request(
                    os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
                    payload=get_account_info_request(c.mint))
            except SourceError:
                mint_responses[c.mint] = None
    for c, status, detail in selected:
        rpc = mint_responses.get(c.mint)
        if args.mode == "demo":
            info = {"mintAuthority": None, "freezeAuthority": None}
            rpc = {"result": {"value": {"owner": TOKEN_CLASSIC,
                   "data": {"parsed": {"type": "mint", "info": info}}}}}
        security = evaluate_mint_rpc(c.mint, rpc)
        holder_diagnostics = None
        owner_diagnostics = None
        pool_diagnostics = None
        if args.holder_check:
            if rpc is None:
                holder_diagnostics = {"status": "UNKNOWN", "reason": "Mint RPC unavailable or budget exhausted"}
            elif rpc_used >= rpc_budget:
                holder_diagnostics = {"status": "BUDGET_EXHAUSTED", "reason": "Safety budget reserved for mint checks", "w01_w02_security_status": "UNKNOWN"}
            else:
                try:
                    rpc_used += 1
                    largest = transport.request(
                        os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
                        payload=largest_accounts_request(c.mint))
                except SourceError:
                    largest = None
                holder_diagnostics = inspect_raw_account_concentration(rpc, largest)
                if args.owner_check and holder_diagnostics.get("status") == "RAW_ACCOUNTS_ONLY":
                    if rpc_used >= rpc_budget:
                        owner_diagnostics = {"status":"BUDGET_EXHAUSTED", "w01_w02_security_status":"UNKNOWN"}
                    else:
                        rpc_used += 1
                        include_pool = args.pool_check and is_valid_mint(c.pool)
                        try:
                            owners = transport.request(os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
                                payload=owner_accounts_request(largest, pool_address=c.pool if include_pool else None))
                        except (SourceError, ValueError):
                            owners = None
                        owner_diagnostics = inspect_observed_owners(c.mint, rpc, largest, owners, expect_pool=include_pool)
                        if args.pool_check:
                            pool_diagnostics = inspect_pool_program(c.pool, largest, owners,
                                owner_batch_includes_pool=include_pool, expected_mint=c.mint)
                elif args.owner_check:
                    owner_diagnostics = {"status":"UNKNOWN", "reason":"Raw largest-account data unavailable", "w01_w02_security_status":"UNKNOWN"}
        if args.pool_check and pool_diagnostics is None:
            pool_diagnostics = {"status":"UNKNOWN", "reason":"RPC budget exhausted or prerequisites unavailable",
                                "pool_vaults_classified":False, "l02_l07_l08_security_status":"UNKNOWN"}
        print(json.dumps({"mint":c.mint,"pool":c.pool,"source":c.source,"observed_at":c.observed_at.isoformat(),
                          "age_minutes":round(c.age_minutes,1),"liquidity_usd":str(c.liquidity_usd) if c.liquidity_usd is not None else None,
                          "volume_5m_usd":str(c.volume_5m_usd) if c.volume_5m_usd is not None else None,
                          "volume_1h_usd":str(c.volume_1h_usd) if c.volume_1h_usd is not None else None,
                          "buys_5m":c.buys_5m,"sells_5m":c.sells_5m,"trades_1h":c.trades_1h,
                          "price_change_1h_pct":str(c.price_change_1h_pct) if c.price_change_1h_pct is not None else None,
                          "discovery_status":status, "discovery_reason":detail,
                          "security_decision":security.decision.value,
                          "security_contract_checks":{ck.code:ck.status.value for ck in security.checks if ck.code.startswith("C")},
                          "security_reject_reasons":[{"rule":ck.code, "reason":ck.explanation} for ck in security.checks if ck.status.value=="HARD_REJECT"],
                          "security_unknown_checks":[ck.code for ck in security.checks if ck.status.value=="UNKNOWN"],
                          "holder_account_diagnostics":holder_diagnostics,
                          "owner_authority_diagnostics":owner_diagnostics,
                          "pool_program_diagnostics":pool_diagnostics,
                          "risk_score":None,"ready_for_alert":False}))
    if args.mode == "live":
        print(json.dumps({"rpc_requests_used":rpc_used,"rpc_request_budget":rpc_budget,
                          "holder_diagnostics_enabled":args.holder_check,"owner_diagnostics_enabled":args.owner_check,"pool_diagnostics_enabled":args.pool_check,"alerts_enabled":False}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
