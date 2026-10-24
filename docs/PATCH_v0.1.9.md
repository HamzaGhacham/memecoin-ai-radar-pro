# Stage 2 — PumpSwap Pair Orientation & Recorded Vault Address Diagnostics (v0.1.9)

## Problem reproduced from 2026-10-23 live output

The user-selected mint is PumpSwap **quote_mint**, while Wrapped SOL is **base_mint**. v0.1.8 treated any mint other than pool base mint as a token-pair mismatch. That is too restrictive: the pool's stored pair contains the candidate as quote. Such an orientation is **non-canonical** for many meme-token/SOL pools; it warrants a warning and further checks, **not** an automatic fraud classification.

Large raw token-account concentration (e.g. 85.46% observed in a top account) may include a pool reserve vault. Raw account concentration is NOT a verified ownership distribution, and an address match to a recorded vault is NOT proof that it is a valid reserve account.

## Changes

- PumpSwap pool decoder accepts candidate token on **either** the on-chain base or quote side as pool membership.
- Explicit `candidate_token_side`, `pair_orientation`, `unusual_pair_orientation`, and `candidate_vault_address` fields.
- A true non-member mint still returns `MINT_MISMATCH` / `POOL_TOKEN_PAIR_MISMATCH`.
- `POOL_LAYOUT_VERIFIED_QUOTE_TOKEN_VAULTS_UNCHECKED` distinguishes a quote-side candidate from a canonical base-side candidate.
- `vault_address_diagnostics` compares the pool's recorded candidate-vault address to the already-fetched 20 largest token account addresses; no additional RPC calls.
- Preserves `L02`, `L07`, `L08`, `W01`, `W02`, `T01`, `T04` as UNKNOWN. No Security PASS, scoring, alerts, trades, or credentials.

## Critical limits and interpretation

A matching vault address is only a cross-source address coincidence at nearby RPC slots. An independent read of the token-account mint, authority and balance, protocol PDA derivation where applicable, reserve correctness, LP mint, LP token control and withdrawal authority are still required. PumpSwap liquidity security is **NOT VERIFIED**.

`ACCOUNT_BALANCE_DRIFT` is an explicitly handled RPC snapshot inconsistency; this patch does not hide it or turn it into a PASS. On an active pool, rescan at a later slot if desired. The `minContextSlot` parameter does not create an atomic snapshot.

## Installation (from existing v0.1.8)

Download the v0.1.9 ZIP, place it in Downloads, open PowerShell inside the project folder, and run:

```powershell
Copy-Item .\src\radar\pumpswap_layout.py .\src\radar\pumpswap_layout.py.v018.bak
Copy-Item .\src\radar\pool_program.py .\src\radar\pool_program.py.v018.bak
Expand-Archive "$env:USERPROFILE\Downloads\MemeCoin_AI_Radar_Stage2_Pool_Pair_Orientation_v0.1.9.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m radar --mode live --rpc-check --holder-check --owner-check --pool-check --max-candidates 1
```

Tests are fixture-backed and offline. The live candidate can change between scans; a different pool may produce a different result. Keep all credentials in environment variables, never post the Helius RPC URL or commit `.env`.

## Source

https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_SWAP_README.md
https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json
