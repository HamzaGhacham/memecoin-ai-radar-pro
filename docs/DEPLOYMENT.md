# Deployment checklist: Public GitHub + Neon + Cloudflare + Telegram

**All opportunity alerts are intentionally disabled, regardless of deployment success.**

## 0. Rotate exposed credentials before doing anything else

Revoke the Solana RPC API key previously shared in chat. Generate a fresh one. Do not include it in the repository or `.env` file that you push. The `SOLANA_RPC_URL` secret is the entire HTTPS URL containing the new key, not just the key.

## 1. GitHub (public)

Create an **empty public repository**. Extract and commit this release (make sure `.env` and `.venv` are excluded). Then run **Actions > CI - safe offline checks**. The release bundle includes no live credentials. Do not upload the zip inside the repository; commit the extracted text files.

## 2. Neon PostgreSQL

Create one Neon project. In Neon SQL Editor, run `db/schema.sql` (paste its SQL). Confirm `scan_runs`, `observations`, `watchlist`, `pending_jobs` and `alerts_outbox` exist. The Cloudflare Worker and Python runner require compatible tables.

Add these GitHub Actions **repository secrets**:

| Secret | Example shape (never paste real values into documents) |
|---|---|
| `DATABASE_URL` | `postgresql://...` from Neon, use SSL |
| `SOLANA_RPC_URL` | `https://.../?api-key=...` full rotated HTTPS RPC URL |

Do not set `RADAR_SCHEDULE_ENABLED` yet.

## 3. Verify GitHub runner manually

In Actions select `Radar research scan (strict, informational only)` and `Run workflow` only after setting repository **variable** `RADAR_SCHEDULE_ENABLED=true`. This same toggle will allow the 15-minute schedule. To test first without a timer, set it true briefly, launch one workflow, examine concise logs, then set the variable false until comfortable. Failure is expected to stop without a safety PASS. If an API quota or connection error occurs, leave the variable false and investigate.

## 4. Telegram bot

Use BotFather to create a bot and obtain `TELEGRAM_BOT_TOKEN`. Obtain your numeric user ID (`TELEGRAM_OWNER_ID`). Send `/start` to your bot so it can message you later.

## 5. Cloudflare Worker

```bash
cd cloudflare
npm install
npx wrangler login
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_OWNER_ID
npx wrangler secret put DATABASE_URL
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npm run deploy
```

The `TELEGRAM_WEBHOOK_SECRET` should be an unguessable string you generate locally and enter privately. Keep each secret out of shell history and logs. After deployment, use Telegram `setWebhook` with your Worker URL ending in `/webhook` and the *same* `secret_token`. Do this on your PC using a secure Telegram Bot API client; do not publish the bot token in a link, repository or issue. Webhook and long polling are mutually exclusive.

Check Telegram `/status`, `/top`, `/watchlist`, `/add SOLANA_MINT`, `/remove SOLANA_MINT` and `/scan`. When the next scheduled runner completes, it should attempt an owner-only result message for `/scan`, if the Telegram bot and owner secrets are also set on GitHub.

For queued-scan completion messages, set these extra GitHub **secrets**:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OWNER_ID`

The scheduled workflow already reads the RPC and DB secrets; add the Telegram secrets in its job environment **after you have reviewed the workflow** if you want queued job notifications. Ordinary scheduled scan logs continue to work without these secrets. Optionally set `SEND_RESEARCH_REPORTS=true` as a workflow env var for a brief informational Telegram digest on each run (no buy signals).

## 6. Operational controls

- To stop scans: set `RADAR_SCHEDULE_ENABLED=false` or disable workflow.
- To stop Telegram commands: remove webhook / disable Cloudflare Worker.
- Treat `HOLD_UNKNOWN` as *not cleared*.
- Watch GitHub usage, Neon storage, RPC credits and GeckoTerminal quotas.
- Public repository code is visible to everyone; only put non-secret config in version control.
- No production promise: LP ownership, verified whale clustering, sellability tests, AI scoring and execution-aware backtesting remain future work.
