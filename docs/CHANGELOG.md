# Changelog

## v0.1.1 — Candidate-selection fix
- Evaluate prefilters **before** applying `--max-candidates`.
- Fetch page 2 only if page 1 lacks enough preselected candidates; at most 2 GeckoTerminal requests/run.
- Deduplicate by token mint, preferring a pool that meets prefilters, then higher listed USD liquidity.
- Print screening counts, fetched page count, and explicit partial-source errors.
- Print C01/C02/C10 status rather than implying they PASS because they disappeared from UNKNOWN.
- Always keep Opportunity Alerts and auto-trading disabled; security remains HOLD until fully implemented.
- Dedicated Momentum trending-pools adapter, persistence, and two-scan confirmation are future work.

## v0.1.2 - Hybrid discovery diagnostics
- Adds independent new-pools and trending-pools (1h) source polling within the existing two-request budget.
- Reports first-failure reason counts and source coverage, without relaxing the Balanced/Strict thresholds.
- If one provider endpoint fails, shows partial-source error; if both fail, exits safely.
- No confirmation persistence, full security checks, Telegram alerts, or trading.

## v0.1.9 — PumpSwap pair orientation and recorded-vault diagnostics
- Candidate mint in either Pool `base_mint` or `quote_mint` is recorded as pair membership; quote-side membership flagged non-canonical when applicable.
- An actual mint absent from both sides remains `POOL_TOKEN_PAIR_MISMATCH`.
- Compare the corresponding recorded vault address with existing top-20 Token Accounts, without consuming extra RPC budget.
- No vault state verification, no LP security inference, no holder PASS, no alerts or trading.
