# Patch v0.1.4 — Raw Token Account Concentration (Read-only)

## Scope

- Optional bounded Solana `getTokenLargestAccounts` RPC call after all selected tokens receive the baseline `getAccountInfo` checks (budget permits).
- Read supply from prior mint RPC `jsonParsed` payload; no third request necessary.
- Report top 1 and top 10 **token account** share of current supply as a diagnostic only.
- Validate raw integer amounts, account uniqueness, descending order, supply totals, both response slots (max delta 300), RPC error envelopes, and strictly preserve unknown on malformed/stale results.
- Do not mark W01/W02 `PASS` or `HARD_REJECT` based on this raw diagnostic. Pool vaults, burn/escrow, multiple token accounts owned by the same wallet and connected wallet clusters are NOT resolved.
- Only opt-in through `--holder-check` combined with `--mode live --rpc-check`. Default budget remains 3 Solana RPC calls *per run*; `getAccountInfo` for all candidates is prioritized before holder diagnostics.
- No alerts, execution, auto trading, persistent database, Wallet Clustering, or LP/sellability security assertions.

## Windows PowerShell

Run tests after applying patch:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Optional live test (one candidate preserves free-tier RPC budget):

```powershell
.\.venv\Scripts\python.exe -m radar --mode live --rpc-check --holder-check --max-candidates 1
```

On rate limiting, missing supply, stale slots or absent qualifying candidates, `holder_account_diagnostics.status` may be `UNKNOWN` or there may be zero candidates. This is not a system failure and must NOT be treated as Security PASS.

Official API contract: https://solana.com/docs/rpc/http/gettokenlargestaccounts
