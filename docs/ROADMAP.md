# Implementation roadmap with gates

0. **Feasibility (IN PROGRESS)**: bounded provider tests, schema fingerprints, updated free-tier budgets. Gate: source matrix documented with live evidence.
1. **Foundation (STARTED)**: typed models, read-only discovery, base Solana authority probe, config, unit tests, CI, no alerts. Gate: green offline tests and bounded live smoke run.
2. **Persistence**: Neon migrations for tokens/pools/observations/security evidence/jobs; idempotency and retention; transactional claims. Gate: concurrent writes and restart safety tested.
3. **Strict Security**: complete Token-2022 parsing, pool-specific liquidity ownership/removal, holder ownership, sellability, external corroboration, durable evidence. Gate: no eligible PASS from incomplete checks; differential tests.
4. **Opportunity + confirmation**: valid acceleration windows, scoring with explicit missingness, two independent observations across separate scans. Gate: no look-ahead and no duplicate alerts.
5. **Telegram gateway**: Cloudflare webhook, owner auth, secret token, rate controls, queued commands, safe replies. Gate: spoofed/non-owner request rejected.
6. **Alert outbox & follow-ups**: cooldown and critical bypass, bounded deliveries, actual scheduled follow-up tracking. Gate: idempotency, crash recovery and missed-window flags.
7. **Free-tier production scheduling**: five-minute GitHub scan, independent discovery budget, storage/resource observability. Gate: live dry-run and budget alarms pass.
8. **Research / learning**: cohort-based security labels, execution-aware performance, walk-forward Champion/Challenger, shadow mode, manual approval. Gate: reproducible experiment results and no auto-modified hard stops.

Every stage must be independently testable and cannot silently weaken Strict Security rules.
