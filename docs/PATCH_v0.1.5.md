# Stage 2 — Owner Authority Diagnostics v0.1.5

## Objective

Extend the read-only holder diagnostics from token-account concentration to
**observed token-account authority aggregation**, using one batched
`getMultipleAccounts` request for the up-to-20 addresses from
`getTokenLargestAccounts`. This is an **inspection aid, not wallet security
verification**.

## Changed files

- `src/radar/owner_diagnostics.py`: new safe owner fetch and aggregation with
  validation of parsed account owner, mint, program, amounts and RPC slots.
- `src/radar/cli.py`: new optional `--owner-check` switch, bounded RPC calls and
  JSON `owner_authority_diagnostics` output.
- `tests/test_owner_diagnostics.py`: coverage of parsing, grouping and failures.
- `tests/test_owner_cli.py`: contract-first RPC budget integration tests.
- `README.md`: usage instructions.

## Run

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m radar --mode live --rpc-check --holder-check --owner-check --max-candidates 1
```

## Strong limitations

- The command does not establish beneficial wallet ownership, insider links,
  vault classification, burn accounts or escrow accounts.
- A given owner/authority can be a program-derived address or a custodian.
- Only accounts among the **top 20** from the source RPC are considered.
- If a token account balance changes between RPC calls, the owner aggregation
  is `UNKNOWN` instead of giving a misleading concentration figure.
- **W01 and W02 always remain UNKNOWN**. No opportunity alerts or trades.
- The default RPC ceiling of **3** is respected for a one-candidate run:
  (1) getAccountInfo, (2) getTokenLargestAccounts, (3) getMultipleAccounts.
- A run with multiple candidates may exhaust the budget before owner analysis;
  in that case the report declares `BUDGET_EXHAUSTED`.
- RPC provider-specific credit pricing can differ from RPC request count.

## Next stage

Identify pools and their vault accounts using protocol-specific, independently
verified on-chain DEX parsing (CPMM, CLMM and bonding-curve cases).
Only then can owner-normalized W01/W02 and LP L02/L07/L08 be meaningfully
considered, subject to broader coverage checks.
