# MEMECOIN AI RADAR PRO
## Master Technical Blueprint — Version 1.0

**Document type:** Product Requirements Document (PRD) + Software Architecture Specification + Security Policy + Implementation Plan
**Date:** 23 October 2026
**Language:** English
**Status:** Design baseline approved in conversation; technical integrations and thresholds require implementation testing and empirical calibration
**Delivery stage:** Design only — no repository, hosted resource, API key, trading wallet, or executable bot is created by this document.

---

## Contents

| Sections 0–8 | Sections 9–16 |
|---|---|
| 0. Executive Summary & Decisions | 9. Nonfunctional Requirements & Testing |
| 1. Goals, Users & Boundaries | 10. Proposed Monorepo Layout |
| 2. Functional Architecture | 11. Implementation Roadmap |
| 3. Discovery Engine | 12. Critical Validation Items |
| 4. Strict Security Engine | 13. Example Policy Configuration |
| 5. Opportunity Intelligence | 14. Operational Runbook |
| 6. Telegram Control Center | 15. Source References |
| 7. Deployment, DB & Resilience | 16. Final Baseline & Sign-off |
| 8. Backtesting & Optimization | — |

---

## 0. Executive Summary and Decision Register

MemeCoin AI Radar Pro is a **read-only Solana meme-coin discovery, safety-assessment, ranking, and Telegram notification platform**. It identifies potentially noteworthy market activity through two separate scanners, rejects or quarantines candidates that violate a strict, evidence-based security policy, applies quantitative opportunity scoring to eligible candidates, and tracks what actually happened after each signal. The platform is for research and monitoring, not guaranteed predictions or automatic execution.

### Approved decisions

| Decision | Baseline |
|---|---|
| Discovery strategy | **Hybrid AI Radar**: Scanner A (Early Gems) plus Scanner B (Momentum) |
| Discovery intensity | **Balanced** |
| Security posture | **Strict Security**; hard-stop rules cannot be overruled by an LLM |
| Signal confirmation | **Balanced Confirmation**: two distinct consecutive valid scan observations |
| Initial chain | **Solana mainnet** |
| Execution | **Read-only**; no funded wallet, private key, signing, buying, selling, or copy trading |
| Git hosting | **Public GitHub repository**; standard GitHub-hosted runners |
| Scheduled backend | **GitHub Actions**, nominal five-minute cadence |
| Telegram interface | **Cloudflare Workers webhook** |
| Persistent data | **Neon PostgreSQL** |
| Notifications | Telegram Bot API; owner-only by default |
| Learning governance | **AI Research + Manual Approval**; Champion/Challenger, walk-forward and shadow tests |
| Budget | Target free-tier usage; **not a guarantee of zero cost or uninterrupted service** |
| Scope | Complete design specification **before programming** |

### Non-negotiable product principles

1. **Fail closed on missing critical evidence.** A missing API response cannot be interpreted as safety.
2. **Evidence over prediction.** Every security rule must point to a source, observation time/slot, rule version, and rationale.
3. **Security and opportunity are separate scores.** A 99/100 opportunity does not cancel a single confirmed hard-stop.
4. **No “100% safe”, guaranteed returns, or unsupported accuracy statistics.** PASS means only “eligible under this policy using observed data.”
5. **No auto trading in V1, V2, or this approved design.** Changing that requires a separate explicit design decision and security review.
6. **No look-ahead bias.** Backtests evaluate only data available at signal time, including actual notification delay.
7. **Protect secrets in a public repo.** Never store a token, database URL, signing credential, or raw private user data in source files or Actions logs.
8. **Implement progressively.** Advanced wallet forensics are not represented as completed until their independent evidence pipeline exists and passes tests.

### Design constraints and corrections

- A nominal five-minute GitHub Actions schedule does **not** provide guaranteed five-minute execution or sub-minute security detection. Scheduled jobs may be late or skipped. Webhooks make **Telegram command acknowledgement** faster, not blockchain scanning instantaneous.
- CoinGecko Demo is currently advertised with a **10,000 API-call monthly allowance**. Five-minute polling yields about **8,640 scheduled scans per 30 days** before any extra token requests. Therefore CoinGecko discovery must have a **separate lower-frequency budget**, caching, and adaptive throttling. DEX Screener’s documented endpoint rates are not a promise of unlimited high-volume data.
- Raydium CPMM LP tokens and CLMM position NFTs need **different liquidity-removal checks**. Pump.fun bonding-curve assets require an entirely different lifecycle adapter.
- Token age and pool age are separate; discovery thresholds below refer to **pool age**, unless explicitly stated otherwise.
- Insider-cluster and wash-trading thresholds are **hypothesis-based starting values**, not validated forensic classifiers. They must not produce claims of proven fraud from a single heuristic.

---

## 1. Product Goals, Users, Boundaries and Acceptance Criteria

### 1.1 Primary goals

- Discover newly active Solana trading pools and established tokens exhibiting abnormal market momentum.
- Apply strict token-permission, liquidity, market-exit, holder-distribution, manipulation, and provenance checks before any opportunity alert.
- Deliver intelligible Telegram alerts with mint address, source links, timestamps, risk/coverage scores, evidence, and uncertainty.
- Preserve a full, auditable signal history with follow-ups at 15m, 1h, 6h, 24h, and 7d.
- Evaluate detection and paper-performance quality rather than marketing headline returns.
- Remain operable in free tiers by budgeting API calls, storage, compute, and alert volume.

### 1.2 Out-of-scope functionality

- Real-money transactions, transaction signing, wallet custody, brokerage functions, bot-managed funds.
- Guaranteeing that a coin is not fraudulent, guaranteeing sellability, predicting “10x/100x” outcomes.
- Claiming confirmed common control of wallets from mere shared funding exchange or correlated trade timing.
- Full historical Solana archival/indexer service on free infrastructure.
- High-frequency or real-time market execution; a future continuously running host would be a separate architecture decision.
- Browser-based scraping that violates source terms, bypasses access controls, or evades anti-bot protections.

### 1.3 User stories

- As the owner, I receive an Early Gems alert only after **two fresh valid scans** and Strict Security PASS.
- As the owner, I receive a Momentum alert only if its own scoring rules and market-data coverage pass.
- As the owner, I can send `/analyze <MINT>` and get the newest valid saved report or a clear queued-response notice.
- As the owner, I see exactly **why** a token is rejected, warned, held, or accepted.
- As the owner, I can watch a rejected token for critical changes without overriding security decisions.
- As the owner, I see follow-up performance, including failures and missing execution data.
- As the owner, I can compare candidate scoring versions, then manually approve any replacement.

### 1.4 Global release gates

V1 cannot launch real opportunity alerts until: owner authorization works; contract/critical liquidity/holder/sellability adapters are proven or safely return UNKNOWN; scan snapshots have accurate timestamps; two-scan confirmation is race-safe; evidence records are immutable or append-only; notifications are deduplicated; limits and error handling are measured; no secrets leak in logs; and repeated live dry-runs behave as expected. Strong forensic claims, profit claims, and “verified safe” badges are prohibited.

---

## 2. Functional Architecture and Technology Choices

### 2.1 Logical data flow

```text
New Pools / Market Feeds (budgeted)       On-chain Security / RPC (budgeted)
                 |                                      |
         Discovery Adapters                      Security Adapters
                 |                                      |
         Candidate Normalizer ---------------------------+
                 |
        Early Gems / Momentum Filters
                 |
         Strict Security Gate
         |       |        |
      REJECT    HOLD     PASS
         |       |        |
         +-------+---- Evidence DB
                          |
                 Quantitative Opportunity Engine
                          |
                   Confirmation State Machine
                          |
               Alert Outbox / Performance Tracker
                          |
                      Telegram API

Telegram updates --> Cloudflare Worker --> Owner authorization / Cached reports
                                         --> Pending jobs in Neon
GitHub Actions (scheduled/manual) ---------> Process jobs, scan, evaluate, deliver
GitHub weekly/monthly workflows -----------> Backtest / Champion vs Challenger
```

### 2.2 Components

| Component | Proposed technology | Responsibilities |
|---|---|---|
| `scanner-engine` | Python 3.12+ | Discovery, filtering, snapshots, scoring, tracking |
| `security-engine` | Python | Token, LP, holder, simulation, evidence, hard-stop decisions |
| `research-engine` | Python | Replays, labels, walk-forward evaluations, score calibration |
| `telegram-gateway` | Cloudflare Worker, TypeScript | Secret validation, authorization, buttons, lightweight reads, enqueue |
| `database` | Neon PostgreSQL | Transactional state, evidence, alerts, snapshots, audit |
| `scheduler` | GitHub Actions | Five-minute workflow with task dispatch, daily/weekly/monthly workflows |
| `third-party-adapters` | HTTP/RPC clients | Rate limiting, normalized payloads, retries, provenance |
| `observability` | Structured logs + DB metrics | Runs, source health, budget, coverage, delivery failures |

The gateway must not perform heavy blockchain analysis synchronously. A manual Telegram scan queues a database job; the next authorized worker processes it, optionally with an authenticated GitHub `workflow_dispatch` later if justified. The fast acknowledgment is not a promise that the final analysis is immediate.

### 2.3 Data providers and source trust

| Source | Function | Trust/limitations |
|---|---|---|
| CoinGecko/GeckoTerminal | New-pool discovery, trending pools, historical pool OHLCV where available | API entitlement, age window, monthly cap, data latency must be verified at integration |
| DEX Screener | Pair prices, pool liquidity, transaction counts, volumes, listings | REST snapshots, limited history; boosted listings are promotional indicators, not an endorsement |
| Solana RPC | Mint owner/program, authorities, extensions, balances, token accounts | Authoritative for queried finalized/confirmed state; shared RPC may throttle and limit history |
| RugCheck | Solana token security report | Secondary corroboration only; availability/schema to be tested |
| GoPlus | Solana token risk and simulation when supported | Secondary corroboration only; verify actual field coverage and plan limits |
| Native DEX protocol adapters | Raydium CPMM/CLMM, launchpad curve status, liquidity rights | Exact version/program ID support required; UNKNOWN for unsupported pools |
| Jupiter-compatible read-only routing source | Sell quote/route feasibility | Quote is indicative, not proof future sell execution; confirm current API entitlement |
| Telegram Bot API | Messaging and interactive commands | Webhook retries, callback authorization, anti-spam and API rate errors |

**Provenance rule:** Record provider, endpoint category, observed_at, ingested_at, Solana slot/commitment where available, schema_version, raw-evidence hash, and provider request result. Two sources repeating the same upstream dataset do not count as independent confirmations.

---

## 3. Discovery Engine — Phase 1

### 3.1 Scanner A — Early Gems Hunter

| Parameter | Default | Interpretation |
|---|---:|---|
| `pool_age_min_minutes` | 5 | Younger pools in a warming/pending state |
| `pool_age_max_hours` | 6 | Above this, eligible for Momentum scanner |
| `min_verified_liquidity_usd` | 15,000 | Discovery floor, not security certification |
| `min_volume_usd_5m` | 3,000 | Latest fully measured five-minute window |
| `min_txns_5m` | 15 | Number of trades, not unique traders |
| `min_buy_sell_count_ratio_5m` | 1.2 | Secondary indicator only; count ratio is not net flow |
| `min_volume_acceleration` | 1.5x | Two comparable non-overlapping windows |
| `min_opportunity_score` | 75/100 | Only after Strict Security PASS |
| `opportunity_coverage_min` | 80% | Mandatory high-priority opportunity features must be valid |
| `confirmation_observations` | 2 | Distinct consecutive valid scans |

**Early Gems lifecycle:** DISCOVERED -> ELIGIBLE -> SECURITY_CHECK -> OPPORTUNITY_PENDING -> CONFIRMED_ALERT, or QUARANTINED / REJECTED / EXPIRED. A newly created pool with insufficient initial history receives `WARMING_UP` rather than a fabricated acceleration value.

### 3.2 Scanner B — Momentum Hunter

| Parameter | Default |
|---|---:|
| `pool_age_min_hours` | 6 |
| `pool_age_max_days` | 30 |
| `min_verified_liquidity_usd` | 50,000 |
| `min_volume_usd_1h` | 50,000 |
| `min_txns_1h` | 100 |
| `min_price_change_1h_pct` | +10% |
| `min_volume_acceleration` | 1.5x |
| `min_opportunity_score` | 80/100 |
| `confirmation_observations` | 2 |

Filter on turnover sustainability and execution friction, not price increase alone. A rapid positive return paired with declining unique participation and worsening sell impact is tagged `OVEREXTENDED` or `WAIT_CONFIRMATION`.

### 3.3 Deduplication and token identity

- Identity key: `(chain_id='solana', mint_address)`; a symbol/name is never trusted as a unique identifier.
- Multiple pools per mint are stored separately with a supported `pool_type`, pool ID, quote asset, DEX name, lifecycle, and selection rationale.
- The market analysis can select a **primary execution pool**, but includes other economically significant pools to avoid cherry-picking liquidity.
- Discovery must not treat DEX Screener boosted profiles as independent organic momentum.
- Coins transitioning from a launchpad bonding curve to a DEX become a new lifecycle stage; do not treat the newly created pool as an unrelated brand-new token.

---

## 4. Strict Security Engine — Phase 2

### 4.1 Outcome vocabulary, evidence and precedence

Individual check status: `PASS | WARNING | HARD_REJECT | UNKNOWN | CONFLICT | NOT_APPLICABLE`. Final decision: `ELIGIBLE_PASS | WATCHLIST | HOLD_UNKNOWN | REJECT_SECURITY | INELIGIBLE_DISCOVERY`.

**Decision precedence**:

1. A confirmed, supported hard-stop -> `REJECT_SECURITY` (with reason/evidence).
2. Missing, stale, contradictory, or unsupported **mandatory** check -> `HOLD_UNKNOWN` (never PASS).
3. Risk score >60 -> `REJECT_SECURITY` **by policy**; label as policy-based high risk, not confirmed scam.
4. Risk score 36–60 -> `WATCHLIST`.
5. Risk score ≤35, weighted data coverage ≥85%, all critical checks complete/fresh, and no hard-stop -> `ELIGIBLE_PASS`.
6. Discovery-only failures (age, volume, liquidity) -> `INELIGIBLE_DISCOVERY`, not an allegation of fraud.

If both HARD_REJECT and UNKNOWN occur, report the **confirmed reject** plus the incomplete checks. On resolution of a conflict, append a new evaluation; do not overwrite the old observation.

**Freshness at decision time:** targeted on-chain critical observations not older than ~2 minutes for Early Gems and ~5 minutes for Momentum, with provider-specific tolerance; require monotonic observation times and record the observed slot. These are designed maxima to test, not guaranteed source latencies.

### 4.2 Contract and permissions rulebook

| ID | Check | HARD REJECT / disqualifier | WARNING / UNKNOWN rules |
|---|---|---|---|
| C01 | Mint authority | Active ability to mint additional supply | UNKNOWN if mint not decoded or authority unresolved |
| C02 | Freeze authority | Active freeze authority under Strict policy | UNKNOWN on failed proof; false alarm avoidance through exact mint state |
| C03 | Permanent delegate | Non-null mint-wide delegate with unrevokable account-owner control | UNKNOWN if Token-2022 extension parsing incomplete |
| C04 | Non-transferable | Mint explicitly non-transferable | UNKNOWN on unsupported transfer behavior |
| C05 | Default account state | New token accounts default to FROZEN | UNKNOWN if unavailable; informational otherwise |
| C06 | Pausable mint | Paused or uncontrolled pause authority exposed under strict policy | UNKNOWN if pause extension not fully decoded |
| C07 | Transfer hook | Demonstrably hostile hook or controllable harmful restrictions | HOLD_UNKNOWN if the hook program is unrecognized or its effect cannot be audited |
| C08 | Transfer fees | Effective fees >5% in reference sell, or configurable dangerous increases | WARNING 1–5%; UNKNOWN if effective fee cannot be computed |
| C09 | Other sensitive Token-2022 extensions | Known disallowed behavior | UNKNOWN + block PASS if unsupported material effect |
| C10 | Token-program and mint validation | Malformed mint or excluded unsupported executable owner | UNKNOWN if owner/RPC query fails |

**Policy nuance:** Under strict meme-coin policy, an active centralized permission can disqualify a token even if the issuer is legitimate. Treat that as a **risk-policy exclusion**, not a finding of intent to defraud. Review whether the extension exists, whether authority is null, whether it can be changed, and how it affects actual transfers.

### 4.3 Liquidity, locks and rug-pull risk

| ID | Check | WARNING | REJECT / HOLD |
|---|---|---|---|
| L01 | Scanner liquidity floor | Below $15k Early / $50k Momentum | INELIGIBLE_DISCOVERY only; not scam |
| L02 | Single-party removable liquidity | 20–50% under one controllable owner | >50% demonstrably removable under an untrusted controlling party => policy reject |
| L03 | Verified removal events | >20% removed within 15m | >50% within 15m => REJECT/REVOKE; compare pool reserves/events, not USD-only TVL |
| L04 | Lock expiration | Large meaningful lock unlocks in <24h | Unlock + confirmed dangerous removal => REJECT; imminent unlock itself WARNING |
| L05 | Pool concentration | >90% of usable liquidity in one withdrawable pool | REJECT only with separately demonstrated control danger |
| L06 | $100 sell impact | >10% | >25% => execution ineligible; not automatically a scam allegation |
| L07 | LP/position ownership | Ownership unclear | UNKNOWN if rights cannot be decoded; REJECT only if >50% verified removable under risky control |
| L08 | Pool mechanism support | Unrecognized LP mode or unsupported launchpad stage | HOLD_UNKNOWN and do not issue PASS |

**Pool-aware adapters:** CPMM/AMM LP fungible tokens; CLMM position NFT/position accounts; launchpad bonding curve virtual/real reserves and migration state. Lock status is never inferred from “burned” language without decoding the actual locking mechanism. A nominal 50% TVL fall can come from price movements and is **not** itself a 50% liquidity withdrawal.

### 4.4 Wallet distribution, insiders and concentration

| ID | Check | WARNING | Hard reject policy / investigation |
|---|---|---|---|
| W01 | Top 1 independent owner | >15% of verified sellable supply | >35% under one freely tradable independent owner => policy reject |
| W02 | Top 10 independent owners | >40% | >60% of tradable supply => policy reject if attribution/denominator verified |
| W03 | Confirmed creator/developer ownership | >10% | >20% controlled and liquid => policy reject |
| W04 | Connected-wallet cluster | >25% with multiple link indicators | >40% with **strong corroborated linkage** => policy reject |
| W05 | Fresh-wallet acquisition | >30% of recent buys from fresh wallets | WARNING only unless separate strong manipulation evidence |
| W06 | Launch snipers | >20% current sellable supply | >50% plus independently corroborated insider connection/dump => policy reject |
| W07 | Insider selling | Verified 2–5% sellable supply over 15m | ≥5% from proven insiders over 15m => critical policy reject |
| W08 | Developer harmful history | Prior risky project behavior | Corroborated repeat rug pattern + reliable identity link => policy reject |

**Denominator and attribution rules:** Report `% of total mint supply` and `% of verified circulating/sellable supply` separately. Merge multiple token accounts per same owner. Identify and explain known DEX pool vaults, burn accounts, locks, escrow, vesting, treasury, and unidentified program-owned accounts. Never silently exclude unknown accounts. The RPC `getTokenLargestAccounts` returns the largest **20 token accounts**, not the top 20 individual people or wallet owners. If wallet clustering/denominator is insufficient, show UNKNOWN and confidence limits, not an invented exact percentage.

**Wallet-link evidence hierarchy:** direct program authority or explicit ownership proof > repeated direct transfers + linked control > shared funding together with coordinated patterns > mere same centralized exchange funding or simultaneous buys. Exchange-origin coincidence alone is never proof of common ownership.

### 4.5 Sellability and execution friction

| ID | Test | Warning / Unknown | Reject / execution ineligible |
|---|---|---|---|
| T01 | Read-only sell route | No route: UNKNOWN, investigate stage/coverage | Proven protocol-level sale prevention => REJECT |
| T02 | $100 estimated sell impact | >10% | >25% => execution-ineligible policy exclusion |
| T03 | $500 estimated sell impact | >15% | >35% => execution-ineligible policy exclusion |
| T04 | Effective transfer fee | 1–5% | >5% => policy exclusion |
| T05 | Unsigned simulation | Unexplained revert/failure => UNKNOWN | Reproducible token-logic prevention => REJECT |
| T06 | Route instability | Route disappears across snapshots | Suspend eligibility pending fresh checks; no unproven scam finding |

All quotes are conditional estimates. Never expose an execution button or create a funded account. Reference sizes of $100 and $500 are policy probes, not recommended purchases. Distinguish DEX routing failures, missing support, depleted liquidity, and hostile token restrictions.

### 4.6 Market manipulation and forensic heuristics

| ID | Detector | Investigation trigger | Escalation |
|---|---|---|---|
| M01 | Wash trading | ≥30% suspicious circular/repeated volume | ≥60% **verified linked circular flow** => policy reject |
| M02 | Coordinated buying | Strong synchrony across wallets | Never hard reject on timing alone; require control/concentration proof |
| M03 | Artificial holders | Many similarly funded low-balance accounts | HOLD if holder distribution cannot be reliably determined |
| M04 | Slow rug | Persistent coordinated insider sales over 1–24h | REJECT only with confirmed insider provenance and harmful flow |
| M05 | Bundle / sniper clustering | Highly concentrated opening-block purchases | WARNING alone; never conclude scam from a bundle alone |
| M06 | Fake volume | Volume spike without independent unique participation | HOLD/REJECT only when multiple strong manipulation indicators exist |
| M07 | Creator repeat launches | Many short-lived or abandoned launches | WARNING; escalate with independently confirmed prior harmful behavior |

These are forensic hypotheses. A machine must distinguish `SUSPECTED_MANIPULATION` from `CONFIRMED_ABUSE`; human review is required before issuing public allegations or using confirmed scam labels in training.

### 4.7 Identity and community

| ID | Check | Policy |
|---|---|---|
| I01 | Phishing website | Confirmed phishing domain => security reject |
| I02 | Impersonation / copycat | WARNING; reject when independently verified damaging impersonation |
| I03 | False partnership claim | WARNING unless strong confirmed deception |
| I04 | No website / no socials | Missing context, not scam proof |
| I05 | Fake social engagement | WARNING with evidence, not a standalone hard-stop |
| I06 | DEX paid boosts / paid ads | Marketing field only; never a trust feature |
| I07 | Launchpad lifecycle | Enforce lifecycle-specific security logic; UNKNOWN if stage cannot be determined |

### 4.8 Risk score computation and evidence coverage

Initial weights (subject to backtest): Contract & Permissions 30%, Liquidity & Rug Risk 25%, Holders & Insiders 20%, Sellability & Market 15%, Developer & Identity 10%. Each dimension is normalized to 0–100 using documented capped penalties. Total risk = weighted sum of dimension penalties; **UNKNOWN contributes neither a clean zero nor fabricated high risk**. Instead, coverage and mandatory gates separately restrict eligibility. For correlated signals (e.g., Top-10 and wallet-cluster concentration), take a capped combined contribution and identify shared root evidence.

Data Coverage = validated weight of applicable checks / total applicable check weight; include a mandatory-complete gate independent of coverage percentage. `NOT_APPLICABLE` requires recorded rationale and is removed from denominator; `UNKNOWN`, `CONFLICT`, and stale evidence are incomplete. Minimum security coverage **85%** for PASS; minimum opportunity coverage **80%** before alert.

### 4.9 Continuous security state and revocation

- Verified >20% removable liquidity exit within 15m -> WARNING / urgent recheck.
- Verified >50% removal within 15m -> revoke PASS, CRITICAL alert to watched/signaled coins.
- Verified ≥5% sellable-supply insider dump within 15m -> revoke PASS, CRITICAL.
- Risk score jump ≥25 points -> full re-evaluation; urgency depends on source evidence.
- New active critical mint permission -> revoke PASS.
- Unsupported contract change, missing sell route, or stale critical state -> suspend PASS pending recheck.
- Backtest may calibrate statistical warnings; **critical hard-stop policy changes require explicit human approval**, security review, and version increment.

Each state transition records `previous_state`, `next_state`, reason IDs, version, evidence references, and UTC timestamp. Alerts are generated only for watched tokens or active tracked signals by default; blanket rejection broadcasts are a user-configurable option, not the default.

---

## 5. Opportunity Intelligence — Phase 3

### 5.1 Philosophy

A quantitative engine generates reproducible numeric scores; an optional LLM explains already-computed evidence. The LLM does not invent missing on-chain statistics, set trading orders, change rule outcomes, or override safety gates. Advanced wallet metrics are explicitly `NOT_IMPLEMENTED` until data access and validation exist.

### 5.2 Scorecards

| Early Gems dimension | Weight | Momentum dimension | Weight |
|---|---:|---|---:|
| Volume acceleration | 25% | Volume acceleration | 25% |
| Buying pressure (counts plus value where available) | 20% | Price structure | 20% |
| Liquidity quality | 20% | Organic demand | 20% |
| Price structure | 15% | Liquidity/execution | 15% |
| Organic buyers | 10% | Wallet activity | 10% |
| Launch quality | 10% | Momentum persistence | 10% |

**Feature definitions:** `volume_acceleration` compares two complete, non-overlapping windows and winsorizes extreme denominators; `organic_buyers` counts unique verified owners when chain data exists and reports data coverage otherwise; `buy_pressure` combines count and notional to avoid “small buys, one large sell” distortion; `execution_quality` includes price impact, route stability, and effective fees; `momentum_persistence` measures confirmation across independent time windows; `overextension` compares recent move, participation, and declining liquidity/volume rather than using an arbitrary high price gain alone.

### 5.3 Decision policy

| Decision | Preconditions |
|---|---|
| `EARLY_CONFIRMED` | Scanner A eligible, Security PASS, score ≥75, coverage ≥80%, two distinct valid observations, Entry Quality not blocked |
| `MOMENTUM_CONFIRMED` | Scanner B eligible, Security PASS, score ≥80, coverage ≥80%, two distinct valid observations, Entry Quality not blocked |
| `WATCHLIST` | Score 60–74 Early / 60–79 Momentum, or `WAIT_CONFIRMATION`/overextended setup |
| `HOLD_UNKNOWN` | Mandatory critical security/market evidence missing |
| `REJECT_SECURITY` | Strict security denial; no opportunity alert |
| `EXPIRED` | Confirmation expires, pool age out of range, data stale, or signal conditions disappear |

Two consecutive observations must have different acquisition timestamps and independently refreshed market state. Duplicate provider snapshots do not count. Significant changes in pool identity, liquidity, security, or token state reset confirmation. Since a scan may not run exactly every five minutes, define a configurable maximum confirmation gap (initial candidate: 15 minutes); if exceeded, reset confirmation rather than implying continuity.

### 5.4 Entry-quality states

`FAVORABLE_SETUP | WAIT_FOR_CONFIRMATION | OVEREXTENDED | INSUFFICIENT_DATA`. These classify the quality of observation timing, **not** financial advice or an executable buy recommendation. A high Opportunity Score with `WAIT_FOR_CONFIRMATION` may be sent as watchlist context, not a confirmed actionable alert. Only deterministic quantitative evidence decides status.

### 5.5 Smart Money (advanced; not implicitly in initial MVP)

Per-wallet features include realized PnL when complete trade history is available, win rate with sample count and downside skew, holding time, repeated launch timing, fee-adjusted performance, insider-linked risk, and data coverage. Three wallets buying simultaneously do not prove separate informed investors. Proprietary wallet scoring must not treat partial history as exact PnL.

---

## 6. Telegram Control Center — Phase 4

### 6.1 Interaction design

Telegram bot runs **webhook-only** through a Cloudflare Worker. Do not also run `getUpdates` concurrently. Validate Telegram's `X-Telegram-Bot-Api-Secret-Token`, owner/user allowlist and per-command permission. Always answer callback queries and provide bounded, non-blocking responses. Heavy analysis uses queued jobs, not synchronous Worker processing.

### 6.2 Command registry

| Command | Inputs | Behavior |
|---|---|---|
| `/start` | — | Welcome, dashboard buttons, status |
| `/help` | — | Command registry and examples |
| `/scan` | `[early|momentum|both]` | Queue a new scan; show job ID and status; rate-limit |
| `/top` | `[N]` | Rank up to 10 eligible recent opportunities; do not include rejected tokens |
| `/early` | — | Early Gems confirmed/observed candidates |
| `/momentum` | — | Momentum candidates |
| `/trending` | — | Highest verified market acceleration |
| `/analyze` | `<MINT>` | Cached full report or queue fresh security/opportunity analysis |
| `/compare` | `<MINT1> <MINT2>` | Side-by-side comparison on aligned timestamps and coverage |
| `/risk` | `<MINT>` | Complete security outcome, IDs, sources, uncertainties |
| `/holders` | `<MINT>` | Token-account/owner concentration and denominator definition |
| `/liquidity` | `<MINT>` | Pool types, LP control, recent verified changes, exit impact |
| `/wallets` | `<MINT>` | Cluster analysis if implemented, else honest `NOT_AVAILABLE` |
| `/rejected` | `[N]` | Rejections, exclusions and reasons with distinct labels |
| `/why` | `<MINT>` | Explain one decision with rule IDs/evidence |
| `/watchlist` | — | Saved tokens, state and last check |
| `/add` | `<MINT>` | Monitor any valid mint, without overriding security |
| `/remove` | `<MINT>` | Remove personal watch entry |
| `/track` | `<MINT>` | Latest snapshot, follow-up state |
| `/history` | `<MINT>` | Chronological security/scoring history |
| `/performance` | `[period]` | Returns, execution coverage, signal follow-ups |
| `/stats` | `[period]` | Discovery/security/alert/coverage summary |
| `/report` | `[daily|weekly]` | Latest generated report or queue generation |
| `/status` | — | Last scan, job backlog, last successful alert, sources |
| `/health` | — | API/database health and error metrics |
| `/settings` | — | Show owner-editable, validated preferences |
| `/pause` | — | Pause opportunity alerts; **do not disable critical watchlist security alerts** |
| `/resume` | — | Resume opportunities |
| `/mute` | `[duration]` | Mute noncritical messages only |

All command inputs must validate Solana base58 public keys by decoding to expected 32 bytes; never trust token symbol as user lookup identifier. Buttons use short opaque lookup IDs, not privileged raw payloads or credentials. Parse and escape Telegram formatting safely.

### 6.3 Alert taxonomy and delivery

| Event | Default | Dedup / urgency |
|---|---|---|
| Early Gem confirmed | Enabled | Once per signal state; 30m opportunity cooldown |
| Momentum confirmed | Enabled | Same |
| Critical new safety risk | Enabled for watchlist or signaled tokens | **Bypass opportunity cooldown** |
| Suspended/revoked PASS | Enabled | Immediate after next successful detection |
| Risk score increase ≥25 | Enabled for tracked tokens | Alert on material state transition |
| Watchlist score improvement | Optional | Throttled |
| Signal expired/invalidated | Enabled for active signals | State transition |
| 15m/1h/6h/24h/7d follow-up | Stored by default | Summary notifications configurable |
| Daily report | Enabled | Once per local report date |
| Weekly report | Enabled | Once per report week |
| Source outage | Enabled after repeated failures | Aggregate incidents; avoid spam |

Use idempotency keys built from `(chat_id, event_type, token_id, signal_version, transition_id)` to suppress duplicates. `alert_outbox` stores attempts, last error, Telegram message ID, send timestamps and next_retry_at. Telegram has no cross-system atomic transaction with PostgreSQL; use at-least-once delivery with dedup best-effort and potential rare duplicates explicitly acknowledged.

### 6.4 Required notification payload

```
MemeCoin AI Radar Pro — EARLY GEM (confirmed)
Token: $SYMBOL  |  Network: Solana
Mint: <full validated mint address>
Pool: <DEX + pool address>
Scanner: Early Gems | Observations: 2/2
Opportunity: 84/100 (coverage 91%)
Security risk: 18/100 (coverage 94%)
Security status: POLICY_PASS (not guaranteed safe)
Price / liquidity / measured volume: <with units and timestamps>
Top verified warnings: <rule IDs + text>
Entry quality: WAIT_FOR_CONFIRMATION / FAVORABLE_SETUP
Reasons: <3 evidence-backed sentences>
Sources: DEX URL + explorer link + check report
Observed at: <UTC time> | Sent at: <UTC time>
No automated transaction was placed.
```

Daily and weekly reports include scanned count, eligible/rejected/held counts, opportunity cohorts, age, signal latency, data gaps, verified event labels, and **median** observed returns with sample sizes. “Top gainers” must not substitute for full cohort performance.

---

## 7. Deployment, Scheduling, Database and Resilience — Phase 5

### 7.1 Target topology

- **GitHub Public Repository**: Python worker package, TypeScript Cloudflare Worker, documentation, policies, tests, Actions YAML and schema migrations.
- **GitHub Actions**: Scheduled scan runner, manual dispatch, daily reports, weekly evaluation, monthly research. Use standard hosted runners; pin or review action versions and grant least privilege to `GITHUB_TOKEN`.
- **Cloudflare Worker**: Telegram POST webhook, secret verification, owner allowlist, simple reads, queue insertion, rate limit and health endpoint. Keep CPU work tiny.
- **Neon PostgreSQL**: Persistent shared system of record with one transactionally claimed job queue and append-only security/signal evidence tables.
- **Telegram**: Owner-only control, inline keyboards, notification delivery.

### 7.2 Workflow schedule proposal

| Workflow / module | Schedule and trigger | Boundaries |
|---|---|---|
| `radar-scan` | Nominal `*/5` minutes, plus manual trigger | Run Early/Momentum, process eligible pending jobs, security and due follow-ups; enforce time and API budget |
| `security-priority` | Invoked within main scan; standalone only if budget allows | Focus tracked and previously signaled coins; no promise of live protection |
| `daily-report` | Once daily using Africa/Casablanca local-day logic | Dedup by report date; GitHub cron and local offset may differ across seasons |
| `weekly-evaluation` | Once per week | Backtests and full cohort QA |
| `monthly-research` | Monthly/manual | Challenger proposal, never auto-merge |
| `workflow-health` | Hourly or as part of scan | Staleness and source outage watch |
| `ci-checks` | Pull requests and pushes | Unit, integration mocks, static checks, secret scan |

**Scheduling constraint:** GitHub may delay or drop scheduled runs (especially on busy minute boundaries). It can disable inactive public scheduled workflows. Instrument last-success time and send an independent health warning where feasible. A purely GitHub-based detector cannot alert about its own total scheduler outage unless another monitor is available.

### 7.3 Free-tier API call plan — REQUIRED

- CoinGecko Demo: advertised **10,000 calls/month**, i.e. ~333/day in a 30-day month; use a monthly hard budget with a reserve for historical queries, verification and errors.
- **Proposed starting schedule:** CoinGecko discovery **once per 15 minutes** (~2,880 discovery calls / 30 days if one call each time), not every 5 minutes. Other scans can use DEX Screener plus stored candidate lists. If two CoinGecko discovery endpoints run every 15 minutes, budget ~5,760/month before lookups.
- DEX Screener pair/token endpoints: published 300 requests/minute and profile/boost endpoints 60 requests/minute; nevertheless set far lower internal caps and cache pool data.
- Use batch token-pair endpoint where appropriate; queue bounded candidate batches; apply exponential backoff with jitter on 429/5xx; respect `Retry-After`.
- Set per-source day/month quotas and real-time remaining-budget gauges. Budget-exhausted state must degrade coverage and delay new opportunities, **not silently substitute stale data**.
- Sources with undocumented effective limits remain configurable and must pass live smoke tests.

### 7.4 Indicative free-tier infrastructure constraints (verify immediately before provisioning)

| Provider | Published relevant free-tier baseline | Architectural response |
|---|---|---|
| GitHub Actions | Standard hosted runners in public repos are free; extra runner/storage restrictions apply | Public repo, standard runners, concise artifact retention |
| Cloudflare Workers | 100,000 requests/day; ~10ms CPU per request | Simple webhook, quick DB access, no in-request scanning |
| Neon | 1GB database storage/project; 100 CU-hours/project/month (2 Oct 2026 update) | Aggregation, retention and compute monitor |
| CoinGecko Demo | 10,000 calls/month | Independent discovery budget and caching |
| Telegram Bot API | Standard messaging available subject to platform rate/error limits | Outbox, throttling, 429 retry handling |

**Budget promise:** “Designed to operate within currently published free quotas under a measured low-volume workload” — not “guaranteed permanently 0 DH.” Security data enrichment can be unavailable on free tiers.

### 7.5 Database logical schema

All times in `TIMESTAMPTZ` (UTC storage); all money/amount fields use appropriate high-precision numeric/decimal representations, not floating-point money. Use normalized chain + mint keys and immutable source observations.

| Table | Essential fields / keys | Indexes/constraints |
|---|---|---|
| `tokens` | `id, chain_id, mint_address, token_program, symbol, decimals, first_seen_at, metadata_status` | unique `(chain_id,mint_address)` |
| `pools` | `id, token_id, pool_address, dex_id, pool_type, quote_mint, created_at, lifecycle, is_supported` | unique `(chain_id,pool_address)` |
| `market_snapshots` | `id,pool_id,observed_at,ingested_at,price_usd,liquidity_usd,vol_5m,vol_1h,tx_5m,tx_1h,source_id` | `(pool_id,observed_at)`; retention partitions optional |
| `security_checks` | `id,token_id,check_code,status,rule_version,details_json,evidence_id,observed_at,slot,expires_at` | `(token_id,check_code,observed_at DESC)` |
| `security_evaluations` | `id,token_id,state,risk_score,coverage,mandatory_complete,rule_version,reason_codes,at` | `(token_id,at DESC)` |
| `evidence_sources` | `id,provider,source_ref,observed_at,ingested_at,slot,commitment,payload_hash,payload_ref,validation_state` | source/time |
| `wallet_ownerships` | `id,token_id,token_account,owner_address,owner_type,amount,observed_at,verification_state` | token, owner |
| `wallet_clusters` | `id,token_id,cluster_key,ownership_share,confidence,evidence_refs,at` | token, time |
| `candidates` | `id,token_id,scanner,first_seen_at,last_seen_at,filter_state,reason_codes` | token, scanner |
| `opportunity_evaluations` | `id,token_id,scanner,score,coverage,entry_quality,feature_json,score_version,at` | token, scanner, at |
| `confirmations` | `id,token_id,scanner,first_observation_id,second_observation_id,state,expires_at` | unique active token/scanner state |
| `signals` | `id,token_id,scanner,decision,confirmed_at,sent_at,reference_price,security_eval_id,opportunity_eval_id,rule_version` | unique logical signal/transition |
| `tracking_results` | `id,signal_id,horizon,scheduled_at,measured_at,price_return,net_estimate,mfe,mae,exit_quality,data_quality` | unique `(signal_id,horizon,version)` |
| `watchlist` | `id,owner_chat_id,token_id,created_at,alerts_enabled` | unique `(owner_chat_id,token_id)` |
| `pending_jobs` | `id,owner_id,job_type,payload_json,state,priority,attempts,lease_until,created_at,completed_at` | `(state,priority,created_at)` |
| `alert_outbox` | `id,idempotency_key,chat_id,event_type,payload_json,status,attempts,next_retry_at,telegram_message_id` | unique `idempotency_key` |
| `scan_runs` | `id,workflow_id,run_id,started_at,finished_at,result,counts_json,error_json,commit_sha` | workflow/time |
| `api_usage` | `id,provider,endpoint_group,usage_date,requests,cost_estimate,errors` | unique provider/group/date |
| `bot_settings` | `owner_id,settings_json,settings_version,updated_at` | unique owner |
| `strategy_versions` | `id,version,config_hash,commit_sha,effective_at,approval_record` | unique version |
| `backtest_runs` | `id,strategy_version,dataset_version,window_start,window_end,metrics_json,sample_counts,approved_by,at` | strategy/date |
| `incident_logs` | `id,severity,component,root_cause,status,opened_at,resolved_at` | status/time |
| `audit_events` | `id,actor,action,old_value_hash,new_value_hash,at,request_id` | actor/time |

**Transactions and concurrency:** Queue workers acquire due jobs via a lease or `FOR UPDATE SKIP LOCKED`; use conditional transitions, optimistic version fields where useful, deterministic signal dedup keys and bounded retries. Neon autosuspend/connect churn requires connection pooling/driver choice suited to Worker execution.

### 7.6 Retention, backup and resilience

- Raw 5-minute snapshots: target 30 days, aggregate to 15m/1h for ~90 days, long-term daily summaries; adapt limits to storage.
- Preserve decisions, evidence hashes, version IDs, and signal lifecycle for reproducibility; minimize large raw transactions.
- Keep database size monitoring, optional export of essential state, restore instructions, and migration rollback procedures. Neon free restore capabilities are limited; avoid treating provider retention as an indefinite backup.
- Source 429/5xx: backoff, circuit breaker, freshness downgrade, `UNKNOWN` if mandatory.
- Database unavailable: pause new alerts and commands requiring state, send health incident if a working independent delivery path exists.
- Telegram unavailable: retain outbox and retry according to error code; acknowledge inability to guarantee exactly-once delivery.
- Scheduled scan missing: explicit stale-scan metric with local alert on next run or separate monitor where possible.
- Sensitive credential compromise: documented rotation for Telegram token, Neon credentials, Cloudflare secrets and GitHub tokens.

### 7.7 Public repository security standards

- `.env.example` contains only dummy names, never values; use GitHub Environment/Actions secrets and Cloudflare encrypted secrets.
- GitHub Actions `permissions: contents: read` by default; grant specific write permissions only when required.
- Do not run untrusted pull request code with deployment secrets (`pull_request_target` hazards); protect deployment branches and workflows.
- Pin/review third-party Action versions and dependencies; run secret scanning, dependency audit, static type checking and unit tests.
- The Telegram webhook verifies both source header and authorized `from.id`/chat. Validate callback ownership, age, and stale idempotency state.
- Never request, display or store seed phrases, trading private keys, or wallet signing sessions.
- API keys and DB roles follow least privilege, rotateable and auditable access; data exposed through Telegram must not include operational credentials.

---

## 8. Backtesting, Learning and Optimization — Phase 6

### 8.1 Objective and data validity

Backtesting must evaluate **historical decisions** using only features and evidence whose `available_at` timestamp was no later than the actual decision. Price-only data cannot reproduce a historical security assessment. Distinguish token-level OHLCV history, historical mint-authority transitions, distribution/LP rights, and actual command delivery time. If historical security state is unavailable, mark the replay as **market-only research**, not an end-to-end strategy verification.

### 8.2 Label taxonomy

| Label | Standard |
|---|---|
| `CONFIRMED_SCAM` | Multiple independently recorded verified malicious or deceptive events, human review; retain evidence |
| `HIGHLY_SUSPICIOUS` | Strong indicators without definitive proof |
| `SEVERE_COLLAPSE` | Large price drawdown; explicitly **not** proof of scam |
| `NO_VERIFIED_SCAM_WITHIN_WINDOW` | No corroborated scam found within observation window, not “safe” |
| `UNKNOWN_LABEL` | Insufficient observation or unresolved facts |

Avoid using mere 90% price drops as automatically positive scam labels. Avoid treating censored/unobserved tokens as clean negatives. Respect label-time latency and preserve reviewer notes.

### 8.3 Evaluation metrics

**Security**: scam recall and precision on an independently labeled set; false-positive rate; false-negative count; detection delay measured from first observable confirmed risk; UNKNOWN/COVERAGE rates; calibration and sample sizes. Report missing-label coverage, not just a vanity percentage.

**Opportunity**: alerts per eligible universe; signal latency; `return_15m, return_1h, return_6h, return_24h, return_7d`, median return, distributions, MFE, MAE, max drawdown, estimated fee/slippage impact, tradable-exit rate, survivorship and missing-data proportion. Returns assume no actual trade; show observed-price and execution-aware estimates separately.

**Operational**: scan completion, source error/429 rate, median data freshness, DB storage/CU-hours, CoinGecko quota usage, Telegram delivery rates and queue lag.

### 8.4 Data splitting and governance

- Time-ordered training, validation and untouched out-of-sample testing.
- Walk-forward evaluation with embargo where outcome windows overlap.
- Compare Early Gems and Momentum separately before pooled metrics.
- Champion = deployed threshold/configuration version; Challenger = proposed alternative.
- Monthly research may recommend changes but **must not merge or deploy without owner approval**.
- Shadow mode: suggested baseline >=30 days **and** minimum statistically meaningful sample count; 30 days alone is not enough.
- Manual approval record must include PR/reference, dataset time spans, out-of-sample report, risk/coverage changes, rollback plan and authorizing user.
- Never automatically weaken security hard stops. Changing a hard-stop demands explicit policy amendment + documented security review.

### 8.5 Research workflow

1. Freeze the current strategy version and available-at data snapshot.
2. Generate candidate parameter changes on **training** data only.
3. Select on validation window with predefined objectives and guardrails.
4. Evaluate one time on untouched test window.
5. Run Challenger in shadow alongside Champion for fresh incoming tokens.
6. Present comparative precision/recall, false-positive costs, opportunity quality, confidence intervals and compute/API budget.
7. Obtain manual approval; tag configuration and commit; monitor rollout; revert if guardrails degrade.

No LLM-generated numerical fact is accepted without backing input features. ML is optional and postponed until there is sufficient labeled history to outperform a simple transparent rule baseline.

---

## 9. Nonfunctional Requirements and Test Strategy

### 9.1 Requirements

| Category | Requirement |
|---|---|
| Safety | Unknown critical state prevents opportunity PASS; risk overrides opportunity |
| Observability | Each user-visible alert has traceable source/slot/timestamps/version |
| Privacy/security | No wallet credentials or personal financial information; owner-only controls |
| Reliability | Idempotent scan jobs and alerts, bounded retries, source circuit breakers |
| Cost | Hard monthly API quotas, DB usage budgets, free-tier-aware degradation |
| Scalability | Modular chain/DEX adapters; V1 limited to Solana |
| Determinism | Same snapshot + same policy = same numeric scores and decisions |
| Explainability | Human-readable rule IDs and evidence fields |
| Data precision | UTC timestamps; decimal token amounts; explicit USD notionals and confidence |
| Maintainability | Typed adapter contracts, tests, migration versioning, code reviews |

### 9.2 Required test suite

- **Unit**: every rule boundary at -epsilon, exact threshold and +epsilon; authority null/non-null; unknown/NA/conflict; coverage computation; no double count; late price/snapshot; signal expiration.
- **Property-based**: no combination of opportunity scores produces PASS after a confirmed hard stop; no unknown critical check produces PASS; repeated identical events do not create a new logical signal.
- **Contract/schema**: fixtures for Dex Screener, CoinGecko, Solana RPC, Telegram, RugCheck/GoPlus; reject schema drift safely.
- **On-chain fixtures**: legacy SPL versus Token-2022; CPMM versus CLMM; bonding curve migration; pool vault mistaken as holder; owner with multiple token accounts; simulated unsupported extensions.
- **Integration mocks**: DB failures, Telegram 429, CoinGecko monthly quota reached, webhook retry, overlapping Actions runs, stale/missing snapshots, Neon autosuspend connection.
- **Live smoke tests**: read-only calls to well-known valid Solana mints and a curated test token set; no purchases or signature prompts.
- **Security**: unauthorized Telegram user, forged webhook header, replayed callback, malicious symbol/Markdown injection, leaked secret regex scans, compromised third-party Actions prevention.
- **Backtest**: explicit no-look-ahead checks, same signal delivery timing, OHLCV-only market replay flagged incomplete, missing trades cannot be assumed at best price.

### 9.3 Release acceptance matrix

| Milestone | Acceptance proof |
|---|---|
| M0 Source feasibility | Endpoint live checks, field coverage table, call budgets, limits, supported pool types |
| M1 Normalized ingestion | At least two providers normalized; dedup; slot/time evidence |
| M2 Security baseline | Mandatory check state matrix tested; no false PASS on outages/unsupported program |
| M3 Discovery + quantitative opportunity | Two distinct scanners; reproducible scores and features; missing data gated |
| M4 Telegram gateway | Webhook secret and owner auth, commands, queue, inline buttons, alert dedup |
| M5 GitHub + Neon | Measured five-minute runs, idempotent jobs, stable migrations, quota monitoring |
| M6 Tracking | All required horizons, missing data/exit impact represented honestly |
| M7 Research | Valid historical replay, Champion/Challenger, approval/rollback record |
| M8 Pilot | Owner-only read-only dry-run, daily reports, incident logs, no secret exposure |

---

## 10. Proposed Monorepo Layout (documentation-level, not generated code)

```text
memecoin-ai-radar-pro/
  README.md
  LICENSE
  SECURITY.md
  CONTRIBUTING.md
  docs/
    MASTER_BLUEPRINT.md
    security-rulebook.md
    api-source-matrix.md
    architecture-decisions/
    operations-runbook.md
    telegram-command-reference.md
    backtesting-methodology.md
  config/
    profiles/
      balanced-discovery.yaml
      strict-security.yaml
    scoring/
      early-gems.yaml
      momentum.yaml
    budgets.yaml
  apps/
    scanner/               # Python scheduled core
    telegram-worker/       # TypeScript Cloudflare webhook
  packages/
    schemas/               # normalized contracts, model versions
    adapters/              # market, RPC, security, routes
    security/              # rule engine
    opportunity/           # scoring and confirmation
    tracking/              # performance measurement
    research/              # evaluation / optimization
  db/
    migrations/
    seed-fixtures/
  tests/
    unit/
    contracts/
    integration/
    fixtures/
    security/
  .github/
    workflows/
      ci.yml
      radar-scan.yml
      daily-report.yml
      weekly-evaluation.yml
      monthly-research.yml
      workflow-health.yml
```

Suggested style: Python typing + pytest + ruff for core; TypeScript strict mode + test runner for Worker; SQL migrations under version control; centralized feature schemas and API-budget adapters. Do not add Redis, paid queues, Docker orchestration, auto trading, or GPU requirements unless future evidence makes them necessary.

---

## 11. Implementation Roadmap (AFTER blueprint approval)

### Stage 0 — Validate vendors and freeze specifications
- Create a source capability matrix mapping each required check to exact accessible provider fields.
- Confirm CoinGecko Demo entitlement, historical endpoint limits, GoPlus/RugCheck availability and Raydium/Pump.fun supported states.
- Finalize threshold policy YAML, score normalization formulas and mandatory-check list.
- Produce sample Telegram messages and expected result schema.
- Exit criterion: no feature is promised as fully implemented without a data path.

### Stage 1 — Repository, CI and operational secrets
- Create **public** GitHub repo with protected default branch and scoped Actions permissions.
- Establish Python/TypeScript package structure, docs, lint/types/tests, template settings.
- Create Cloudflare Worker/Neon projects privately, configure encrypted credentials and cost dashboards.
- Exit criterion: green CI, no secrets committed, documented rotation.

### Stage 2 — Database + ingestion MVP
- Implement schema migrations and normalized source contracts.
- Integrate CoinGecko new pools at budgeted cadence and DEX Screener pair lookups, plus Solana RPC for token identity.
- Persist snapshots, source timestamps, dedup and rate-limit counters.
- Exit criterion: repeatable market candidate lists and provider error transparency.

### Stage 3 — Baseline strict security
- Implement mandatory mint/Token-2022, recognized pool liquidity/control, top-owner concentration and route feasibility checks.
- Add optional RugCheck/GoPlus corroboration where available.
- Hard-stop/UNKNOWN/WARNING rules, evidence trace, policy version and contradictory-data handling.
- Exit criterion: cannot produce PASS with simulated critical missing data or hard reject.

### Stage 4 — Both scanners and scoring
- Implement Early Gems and Momentum filters, volume-window sanity, scorecards and opportunity coverage.
- Implement two-observation confirmation with distinct snapshots and a configurable maximum time gap.
- Add Entry Quality and signal lifecycle transitions.
- Exit criterion: deterministic fixtures exercise all decision states.

### Stage 5 — Telegram interface and production-style dry runs
- Add Worker webhook, owner access controls, commands, callbacks, persisted jobs and alert outbox.
- Integrate GitHub scheduling/manual triggers with Neon, budgets, retries and alerts.
- Exit criterion: valid token analysis queued and delivered, no duplicates on retry, owner-only authorization.

### Stage 6 — Tracking and daily/weekly reports
- Add observed-price and execution-aware simulation, 15m/1h/6h/24h/7d follow-ups, missing-data markers.
- Build per-scanner reports and health/budget monitoring.
- Exit criterion: complete history for tracked signals with no cherry-picked successes.

### Stage 7 — Advanced forensics and research
- Add stronger wallet provenance, cluster hypotheses, insider behavior, monitored creator history and manipulation detectors **only after reliable indexer/history access**.
- Build labels/evidence QA, walk-forward research, Champion/Challenger, 30-day-plus shadow mode and manual promotion workflow.
- Exit criterion: independent evaluation with sample sizes, confidence limitations and rollback ability.

### Stage 8 — Stabilization and optional future infrastructure
- Evaluate actual missing scans, provider coverage, quota exhaustion and notification delay.
- If near-real-time threat detection becomes a hard requirement, propose an explicitly costed continuously running service/stream architecture. **Do not represent GitHub Actions as real-time protection.**

---

## 12. Critical Decisions and Open Validation Items

The following are **not** reasons to halt planning, but must be resolved through vendor smoke tests before implementation:

| Item | Resolution criterion |
|---|---|
| Pool discovery completeness | Measure which launchpad/bonding-curve tokens are not visible in public new-pool feeds |
| Token-2022 extension coverage | Demonstrate decoder handles all security-relevant extensions or returns HOLD_UNKNOWN |
| Owner/cluster data completeness | Verify top-owner mapping, circulating denominator, and exchange funding ambiguity |
| CLMM liquidity control | Confirm exact position rights and lock adapters by protocol/version |
| Sell-route/simulation | Verify read-only API coverage and provenance; distinguish no quote vs blocked sale |
| RugCheck/GoPlus tiers | Confirm usable API rate limits, fields, failure mode and source independence |
| Scoring normalization | Set explicit min/max transfer functions per metric and document rationale |
| CoinGecko budget | Test ≤10k/month under worst-case retries, historical queries and dual scan feeds |
| Token classification | Maintain independent scam-label evidence with human review |
| Data storage | Load-test 1GB retention policy and 100 CU-hour budget |
| Telegram webhook auth | Validate header secret, owner ID and callback idempotency |
| GitHub scheduler reliability | Observe missing/delayed executions; never promise event-time detection |

---

## 13. Example Policy Configuration — Human-Readable Specification

*Illustrative configuration contract, **not executable bot code**. Numeric thresholds are calibration candidates, not guaranteed optimal settings.*

```yaml
strategy:
  name: hybrid-ai-radar
  version: hybrid-v1.0
  chain: solana
  auto_trading: false
  discovery_profile: balanced
  security_profile: strict
  confirmation:
    consecutive_distinct_observations: 2
    max_gap_minutes: 15

scanners:
  early_gems:
    pool_age_minutes: [5, 360]
    min_liquidity_usd: 15000
    min_volume_usd_5m: 3000
    min_transactions_5m: 15
    min_buy_sell_count_ratio_5m: 1.2
    min_volume_acceleration: 1.5
    min_opportunity_score: 75
  momentum:
    pool_age_hours: [6, 720]
    min_liquidity_usd: 50000
    min_volume_usd_1h: 50000
    min_transactions_1h: 100
    min_price_change_pct_1h: 10
    min_volume_acceleration: 1.5
    min_opportunity_score: 80

security:
  min_weighted_coverage_pct: 85
  all_mandatory_checks_required: true
  max_pass_risk_score: 35
  watchlist_risk_score_max: 60
  reject_above_risk_score: 60
  disallow_active_mint_authority: true
  disallow_active_freeze_authority: true
  disallow_permanent_delegate: true
  effective_transfer_fee_reject_pct: 5
  top1_owner_warn_pct: 15
  top1_owner_reject_pct: 35
  top10_owner_warn_pct: 40
  top10_owner_reject_pct: 60
  verified_cluster_warn_pct: 25
  verified_cluster_reject_pct: 40
  liquidity_removal_warn_15m_pct: 20
  liquidity_removal_reject_15m_pct: 50

opportunity:
  min_feature_coverage_pct: 80
  entry_quality_blocked_states: [OVEREXTENDED, INSUFFICIENT_DATA]

operations:
  github_scan_nominal_minutes: 5
  coingecko_discovery_nominal_minutes: 15
  coingecko_monthly_call_budget_ceiling: 10000
  opportunity_dedup_cooldown_minutes: 30
  performance_horizons: [15m, 1h, 6h, 24h, 7d]
  report_timezone: Africa/Casablanca
  manual_approval_required_for_rule_changes: true
```

The `max_pass_risk_score` gate is evaluated **after** hard-stop rules and mandatory completeness checks. A discovered token below the scanner liquidity floor is `INELIGIBLE_DISCOVERY`, not necessarily `REJECT_SECURITY`. The config loader must validate impossible intervals, unsafe score direction, inconsistent thresholds and conflicting version IDs.

---

## 14. Operational Runbook and Incident Policies

### API outage
1. Capture provider error classification, elapsed time, last successful fetch and affected checks.
2. Retry only within budget with exponential backoff, jitter and bounded attempts.
3. Mark mandatory dependent checks UNKNOWN after data expires; suspend new opportunities if required.
4. Send a consolidated source-outage message after configurable repeated failures.
5. On recovery, refresh and reevaluate; do not replay stale signals as new opportunities.

### Token safety incident
1. Acquire fresh on-chain evidence and correlate with existing record.
2. Confirm whether the trigger is a verified event or a market-data artifact.
3. Revoke PASS where required; write immutable transition and priority outbox item.
4. Notify only watched/signaled contexts by default; include source time and detection time.
5. Continue follow-up measurements; do not rewrite historical earlier PASS as if risk was known then.

### Quota exhaustion
1. Stop nonessential enrichment and historical imports first.
2. Retain essential on-chain checks for watched/signaled coins where possible.
3. Downgrade new candidate coverage and withhold opportunity alerts if mandatory data cannot be refreshed.
4. Report next reset estimate and measured quota usage without inventing a guaranteed availability time.

### DB storage/computation pressure
1. Pause bulky raw-data ingestion and enforce retention / aggregation.
2. Preserve security and signal provenance.
3. Export backups before destructive pruning when possible; record deleted ranges.
4. Restore normal tasks only after quota and consistency checks.

### Bad software release
1. Freeze new signals; continue only safe monitoring if possible.
2. Identify affected commits, configuration versions and decision IDs.
3. Roll back to last approved Champion/configuration through GitHub PR/release process.
4. Reprocess affected tokens with visible corrected reports, not silently changed history.

---

## 15. Source References and Verification Log

**Documentation review date: 23 October 2026.** Links below point to official documentation unless explicitly stated. Providers may change plans and endpoints, and each integration must be verified during Stage 0.

1. [GitHub Actions billing — public standard runners](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
2. [GitHub Actions scheduled workflow troubleshooting](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows)
3. [GitHub REST workflow dispatch endpoint](https://docs.github.com/en/rest/actions/workflows)
4. [Cloudflare Workers platform limits](https://developers.cloudflare.com/workers/platform/limits/)
5. [Neon free plan 1GB update, 2 October 2026](https://neon.com/blog/neon-free-plan-1-gb-per-project)
6. [CoinGecko API plans and Demo allowance](https://www.coingecko.com/en/api)
7. [CoinGecko new-pools guide, 14 October 2026](https://www.coingecko.com/learn/how-to-track-new-tokens-onchain)
8. [CoinGecko API historical on-chain OHLCV limitations](https://www.coingecko.com/learn/coingecko-api-troubleshooting-guide-and-solutions)
9. [DEX Screener API reference](https://docs.dexscreener.com/api/reference)
10. [Solana RPC methods](https://solana.com/docs/rpc/http)
11. [Solana getTokenLargestAccounts](https://solana.com/docs/rpc/http/gettokenlargestaccounts)
12. [Solana Token-2022 Permanent Delegate](https://solana.com/docs/tokens/extensions/permanent-delegate)
13. [Solana Token-2022 Transfer Hook](https://solana.com/docs/tokens/extensions/transfer-hook)
14. [Solana Token-2022 Transfer Fees](https://solana.com/docs/tokens/extensions/transfer-fees)
15. [Solana Token-2022 Default Account State](https://solana.com/docs/tokens/extensions/default-state)
16. [Solana Token-2022 Pausable Mint](https://solana.com/docs/tokens/extensions/pausable)
17. [Raydium LP and position types](https://docs.raydium.io/user-flows/choosing-a-pool-type)
18. [Raydium Burn & Earn lock behavior](https://docs.raydium.io/user-flows/burn-and-earn)
19. [Telegram Bot API](https://core.telegram.org/bots/api)
20. [GoPlus API overview](https://docs.gopluslabs.io/reference/api-overview)

---

## 16. Final Baseline and Sign-off Checklist

**Approved design directions:** Hybrid scanners; Balanced Discovery; Strict Security; two-observation Balanced Confirmation; Solana; GitHub public repo + Actions; Cloudflare Worker Telegram gateway; Neon DB; Free-tier budgets; Telegram command center; evidence-rich alerts; persistent performance tracking; AI Research with Manual Approval.

**Still requiring technical confirmation rather than new product choices:** provider API entitlement, historical data completeness, exact Solana program adapters, fee/route simulation coverage, feature normalization curves, secured database/Worker connectivity, and observed schedule reliability.

**Authorization boundary:** This blueprint is **not an instruction to deploy, trade, register paid accounts, or spend money**. Actual coding, GitHub repository creation, Cloudflare/Neon provisioning and credential setup begin only in a separately authorized implementation step.

**Final statement:** The bot is a research assistant for high-risk assets. Its main safety achievement is **better evidence and disciplined abstention**, not a promise to eliminate scams. Results, costs, operational cadence, and detection accuracy remain subject to validation.
