# v0.1.3 — Token-2022 extension safety diagnostics (read-only)

Updated files: `src/radar/security.py`, `src/radar/cli.py`, plus `tests/test_token2022.py`.

For Token-2022 mint accounts, the analyzer now examines the explicit `info.extensions` list from Solana `getAccountInfo` with `encoding=jsonParsed`. It conservatively blocks permanent delegates, non-transferable tokens, frozen defaults, pausable tokens, unaudited transfer hooks and high/mutable transfer fees. A missing or malformed inventory, unrecognized extension, or incomplete fee schedule stays `UNKNOWN`. This is a policy-based exclusion, not evidence of intentional fraud.

**Limitations:** `jsonParsed` behavior depends on RPC implementation. We have not decoded raw TLV byte layout or audited hook programs. LP control, holder clusters, sell routes and independent consecutive observations are NOT implemented. There is no end-to-end Security PASS or real-money operation, and alerts remain disabled.

Use `python -m unittest discover -s tests -v`, then `python -m radar --mode live --rpc-check --max-candidates 2`. Cross-check unusual results with raw RPC data before relying on them. No `.env` or private credentials are contained in this patch.

See official documentation https://solana.com/docs/tokens/extensions and https://solana.com/docs/tokens/extensions/transfer-hook for behavior and limitations.
