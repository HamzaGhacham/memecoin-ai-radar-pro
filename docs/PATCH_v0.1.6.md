# Stage 2 — Pool Program Identity Diagnostics v0.1.6

## Scope (read-only, fail-closed)

This patch adds optional `--pool-check` diagnostics. It piggybacks the selected GeckoTerminal pool account on the existing `getMultipleAccounts` request, alongside the top 20 token accounts. This does **not** consume a fourth Solana JSON-RPC request. The mainnet program allowlist recognizes PumpSwap AMM and three Raydium AMM families.

**What is verified:** RPC reports that the selected Solana address exists; its owning program address; whether that program ID is in a small, documented list. RPC context slot is checked against the top-account snapshot.

**What is NOT verified:** Whether the address data decodes as a canonical pool of that protocol, pool/token pair binding, vault accounts, liquidity control, LP burn/lock, withdrawal permissions, holder beneficial ownership or tradability. Identifying a program owner is NOT identifying a pool vault or proving pool safety. `L02`, `L07`, `L08`, `W01` and `W02` **remain UNKNOWN**. `ready_for_alert` remains false and neither trading nor Telegram alerts are enabled.

## Changed files

- `src/radar/pool_program.py` (new): safe RPC account-program diagnostic and documented allowlist.
- `src/radar/owner_diagnostics.py`: add optional pool account to same batch; parse only token accounts for holder grouping; strictly check expected batch size.
- `src/radar/cli.py`: add `--pool-check` (requires `--owner-check --holder-check --rpc-check --mode live`), JSON output `pool_program_diagnostics`.
- `tests/test_pool_program.py` (new): read-only integration and fail-closed validation.
- `README.md`: usage and limitations.

## Windows testing

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m radar --mode live --rpc-check --holder-check --owner-check --pool-check --max-candidates 1
```

Expected: `99 tests OK` in the combined v0.1.6 codebase. A live result may be `PROGRAM_RECOGNIZED_NOT_POOL_VERIFIED`, `PROGRAM_UNRECOGNIZED`, `UNKNOWN` or `BUDGET_EXHAUSTED`. NONE is a security PASS.

## Trust boundaries

- Only official RPC and GeckoTerminal are queried; no signer, trading, swap or private keys.
- GeckoTerminal pool address is untrusted until protocol-state decoding binds it to the selected mint.
- Unknown program IDs are **not** labeled scams.
- `getMultipleAccounts` accepts up to 100 addresses; this patch uses <=21 (20 token accounts + 1 pool address).
- Keep configured `rpc_requests_per_run=3`; process `--max-candidates 1` while testing holder+pool checks.
- Public GitHub repositories must never contain your Helius RPC URL/API key.

## Sources reviewed

- Solana `getMultipleAccounts`: https://solana.com/docs/rpc/http/getmultipleaccounts
- Pump.fun published PumpSwap ID: https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_SWAP_README.md
- Raydium program addresses: https://github.com/raydium-io/raydium-docs-v1/blob/main/reference/program-addresses.mdx

## Next stage

Add **protocol-aware pool state decoders** (PumpSwap/Raydium CPMM first), validate pair mints, derive/verify vault pubkeys and parse liquidity control by protocol. Only then assess L02/L07/L08 and normalize W01/W02 — with full coverage requirements still enforced.
