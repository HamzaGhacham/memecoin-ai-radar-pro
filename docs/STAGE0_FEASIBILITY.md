# Stage 0 — Technical Feasibility Matrix

**Date:** 2026-10-23. **Evidence:** official API documentation reviewed; **live provider calls were NOT executed in the offline build environment**. Any live integration must pass actual user-account/quota tests before production.

| Source | Documentary evidence | Implemented in starter | Live verified | Eligibility impact |
|---|---|---|---|---|
| GeckoTerminal new pools | Public Beta API, 30 req/min | JSON adapter, bounded one request | NO | Discovery only, may have missing fields |
| DEX Screener token pairs | Official pair/token endpoints, documented rates | Planned | NO | Market enrichment missing |
| Solana JSON-RPC `getAccountInfo` | Official token mint/authority state docs | Optional read-only request + conservative parser | NO | C01/C02/C10 only |
| Token-2022 extensions | Solana official docs | UNKNOWN until vetted decoding | NO | Fail closed; no PASS |
| RugCheck | Security report API; coverage needs field tests | Not implemented | NO | Secondary corroboration missing |
| GoPlus | Token security/transaction API; plan varies | Not implemented | NO | Secondary corroboration missing |
| Raydium CPMM / CLMM LP rights | Different representations; pool-specific adapters needed | Not implemented | NO | Mandatory unknown |
| Jupiter sellability quote | Read-only indicative quotes; availability/keys change | Not implemented | NO | Mandatory unknown |
| Neon PostgreSQL | Free tier documented, new storage announcement Oct 2026 | Schema planned | NO | No persistent scans/alerts yet |
| Cloudflare Telegram webhook | Workers free limitations official | Planned | NO | No chat control yet |
| GitHub Actions | Public standard runners + manual trigger | CI and opt-in manual test | NO remote runner executed | Scheduler purposefully inactive |

## Stage 0 acceptance gates

- [x] Baseline rules/config written; read-only boundary enforced.
- [x] Offline schema fixtures and negative tests.
- [x] Bounded manual API smoke-test command.
- [ ] Manual network smoke test of GeckoTerminal / Solana RPC from runner.
- [ ] Check actual response schema and source rate behavior.
- [ ] Verify pool lifecycle coverage (CPMM / CLMM / curve) and feasible free providers.
- [ ] Confirm actual Neon and Cloudflare account entitlements and set budget ceilings.
- [ ] Document coverage loss: if no LP or sellability proof, prevent opportunity alert.

No source should ever be marked "live verified" based only on documentation.
