# MemeCoin AI Radar Pro — Integrated Research Release v0.2.0

**Status: deployable research infrastructure / security-gated development release. NOT a production-ready opportunity bot.**

This release consolidates the previously tested v0.1.9 Python scanner and integrates Neon PostgreSQL, GitHub Actions and an owner-only Telegram webhook implemented using Cloudflare Workers. It does **not** place trades, use wallet keys, or mark incomplete security reviews as safe. The last four groups of mandatory security checks (LP controls, verified wallet concentration, sellability) are not yet implemented and **all opportunity signals remain disabled**.

## Architecture

```text
GeckoTerminal New Pools + Trending Pools
            |
    Python Hybrid Discovery
            |
Solana RPC read-only checks (optional)
            |
  STRICT gate: HOLD_UNKNOWN until complete
            |
GitHub scheduled job (every 15 min, opt-in)
            |                 \
     Neon PostgreSQL      Owner-only Telegram research digest (optional)
            |
Cloudflare Worker: /status /top /analyze /watchlist /add /remove /scan
            |
      Private Telegram chat
```

**Approved blueprint:** Hybrid Early+Momentum; Balanced discovery; Strict security; two independent confirmed scans; Solana first; read-only; AI research changes require manual approval; GitHub Public + Cloudflare Workers + Neon + Telegram, free-tier target.

## What works and what does not

| Component | Status |
|---|---|
| GeckoTerminal new + trending pool discovery | Implemented; user reported successful live runs through v0.1.9 |
| Solana mint, freeze and Token-2022 mint extension checks | Implemented; contract-related tests; not a complete contract audit |
| Top-20 raw token-account holders and owner-authority aggregation | Diagnostic only; not a verified distribution |
| PumpSwap pool layout and candidate-side / vault-address decoding | Diagnostic only; vault *state* and LP permissions are **not** verified |
| Strict security fail-closed gate | Implemented; blocks all opportunity alerts while mandatory checks are missing |
| SQLite local storage | Implemented, offline-tested |
| Neon PostgreSQL backend | Implemented, **not live-verified** here |
| GitHub scheduled scanner and CI | Defined; **not deployed or live-verified** here |
| Cloudflare Telegram webhook / commands | Implemented, JavaScript syntax checked, **not deployed or API-verified** here |
| `/scan` queue serviced by next scheduled scan | Implemented (notification requires configured Telegram owner secrets) |
| Performance history | Snapshot storage only; trade-accurate backtesting **not built** |
| AI predictive scoring, two-scan signal confirmation, full LP/holder/sellability clearance | **Not finished; cannot emit eligible opportunities** |
| On-chain fraud guarantee | Not possible. No scam detector can guarantee safety. |

## Security and secret management

**Rotate any API key previously pasted into chat.** Never put API keys, tokens, database credentials or complete RPC URLs in code, issues, CI artifacts or public Git commits. Add rotated credentials only through GitHub `Secrets and variables > Actions > Secrets` and `wrangler secret put`. Never share `.env` files.

No Telegram or account secrets are needed to run offline tests. The original public Solana RPC endpoint may return HTTP 429, so a separate private Solana RPC endpoint is recommended for live tests; this is not a guarantee of unlimited capacity.

## Local setup (Windows PowerShell)

From the extracted project directory:

```powershell
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m radar --mode demo
.\.venv\Scripts\python.exe -m radar.service --mode demo --database-url .\radar-local.sqlite3
```

For an **opt-in read-only live test**, type a **new/rotated complete HTTPS Helius RPC URL** into your own PowerShell session; do not send it into a chat:

```powershell
$env:SOLANA_RPC_URL = (Read-Host 'Enter rotated private Solana HTTPS RPC URL').Trim()
.\.venv\Scripts\python.exe -m radar --mode live --rpc-check --holder-check --owner-check --pool-check --max-candidates 1
.\.venv\Scripts\python.exe -m radar.service --mode live --rpc-check --max-candidates 1 --database-url .\radar-local.sqlite3
```

The last two commands may query live provider endpoints and consume API quota. They never sign or submit transactions. The service prints a concise run summary; the detailed read-only diagnostics can be viewed through the original `radar` CLI.

## Cloud deployment (when you approve moving to GitHub)

Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). **Do not enable the schedule** until Neon is initialized, secrets are set, and the bounded live test succeeds. The cron interval is initially 15 minutes to limit free-tier API consumption. Scheduled GitHub Actions can be delayed or skipped.

## Important policy requirements

- `L02`, `L07`, `L08` (withdrawal rights, pool LP/vault verification), `W01`, `W02` (verified wallet concentration), `T01`, `T04` (sellability and fee constraints) remain `UNKNOWN`.
- `POOL_LAYOUT_VERIFIED_VAULTS_UNCHECKED` is NOT `LIQUIDITY_SAFE`.
- Top-20 token accounts are NOT top-20 independent wallets.
- A valid contract mint is NOT a scam-clearance certificate.
- Historical `PENDING_HISTORY` is NOT confirmed momentum or a buy signal.
- Requested `/scan` runs at a subsequent scheduled interval; the webhook does not run a heavy live scan immediately.

## Sources

- [PumpSwap pool and LP structure](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_SWAP_README.md)
- [Solana getMultipleAccounts](https://solana.com/docs/rpc/http/getmultipleaccounts)
- [GeckoTerminal API](https://www.geckoterminal.com/)
- [Neon from Cloudflare Workers](https://developers.cloudflare.com/workers/databases/third-party-integrations/neon/)
- [GitHub workflow schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
