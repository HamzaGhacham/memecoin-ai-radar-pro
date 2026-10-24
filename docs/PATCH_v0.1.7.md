# Stage 2 — Owner RPC Diagnostics v0.1.7

## Why this patch exists

Live PumpSwap token scans returned `Owner/mint/program/account amount mismatch or unparsed account` after `getTokenLargestAccounts` and `getMultipleAccounts` were read from adjacent slots. Token balances may move between these separate RPC calls even when the API is working correctly. The prior combined error text did not distinguish normal balance drift from an incorrect mint, unexpected program or data parsing failure.

## Changes

- `owner_diagnostics.inspect_observed_owners`: reports stable `error_code` values, without exposing RPC URL or tokens. Important outcomes include `ACCOUNT_BALANCE_DRIFT`, `TOKEN_PROGRAM_MISMATCH`, `TOKEN_MINT_MISMATCH`, `UNPARSED_TOKEN_ACCOUNT`, `OWNER_RPC_UNAVAILABLE`, `RPC_SLOT_DIVERGENCE` and `OWNER_BATCH_INCOMPLETE`.
- `ACCOUNT_BALANCE_DRIFT` returns `balance_mismatch_count` and `rpc_slots` to support troubleshooting. It does **not** output a concentration percentage or trigger security PASS.
- `owner_accounts_request` sets Solana `minContextSlot` to the largest-account sample slot, when present, so the account batch cannot accidentally be read from an older slot. This **does not create an atomic snapshot**, so drift remains possible.
- Enhanced local unit tests cover missing/incorrect data, slot settings and fail-closed behavior.

## Windows steps (project root)

```powershell
Expand-Archive "$env:USERPROFILE\Downloads\MemeCoin_AI_Radar_Stage2_Owner_Error_Diagnostics_v0.1.7.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m radar --mode live --rpc-check --holder-check --owner-check --pool-check --max-candidates 1
```

## Safety boundaries

- **No change** to discovery/security thresholds, RPC request budget (3), signing, trading or Telegram alerts.
- `W01/W02`, `L02/L07/L08`, `T01/T04` remain UNKNOWN until independently verified. A recognized PumpSwap program is *not* proof that the account matches the expected token pair, nor proof of LP lock or safe withdraw rights.
- In a highly active token, changing balances can be expected even across adjacent slots. A balance-drift warning is **not** scam evidence.
- Never post `SOLANA_RPC_URL` or Helius API keys to a public repository.

## Sources

- https://solana.com/docs/rpc/http/gettokenlargestaccounts
- https://solana.com/docs/rpc/http/getmultipleaccounts
- https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_SWAP_README.md
