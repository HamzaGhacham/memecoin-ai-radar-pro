-- PostgreSQL / Neon schema. Always keep research results separate from approved opportunity signals.
CREATE TABLE IF NOT EXISTS scan_runs (
 id TEXT PRIMARY KEY,
 started_at TIMESTAMPTZ NOT NULL,
 finished_at TIMESTAMPTZ NOT NULL,
 mode TEXT NOT NULL CHECK (mode IN ('demo','live')),
 scanned INTEGER NOT NULL CHECK (scanned >= 0),
 preselected INTEGER NOT NULL CHECK (preselected >= 0),
 selected INTEGER NOT NULL CHECK (selected >= 0),
 status TEXT NOT NULL,
 source_error TEXT,
 version TEXT NOT NULL DEFAULT 'integration-v0.2.0'
);
CREATE INDEX IF NOT EXISTS scan_runs_finished_idx ON scan_runs(finished_at DESC);
CREATE TABLE IF NOT EXISTS observations (
 id TEXT PRIMARY KEY,
 run_id TEXT NOT NULL REFERENCES scan_runs(id),
 mint TEXT NOT NULL,
 pool TEXT NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL,
 scanner TEXT NOT NULL,
 discovery_status TEXT NOT NULL,
 security_decision TEXT NOT NULL,
 security_unknown_count INTEGER NOT NULL,
 liquidity_usd NUMERIC(28,8),
 raw_top1_pct NUMERIC(9,4),
 raw_top10_pct NUMERIC(9,4),
 pool_status TEXT,
 raw_data JSONB NOT NULL,
 UNIQUE (run_id,mint,pool)
);
CREATE INDEX IF NOT EXISTS observations_mint_time ON observations(mint,observed_at DESC);
CREATE TABLE IF NOT EXISTS watchlist (
 mint TEXT PRIMARY KEY,
 added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pending_jobs (
 id TEXT PRIMARY KEY,
 requested_by TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('scan','analyze')),
 mint TEXT,
 status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','processing','done','failed')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 error_text TEXT
);
CREATE INDEX IF NOT EXISTS pending_jobs_status_time ON pending_jobs(status,created_at);
CREATE TABLE IF NOT EXISTS alerts_outbox (
 id TEXT PRIMARY KEY,
 kind TEXT NOT NULL,
 subject TEXT NOT NULL,
 payload JSONB NOT NULL,
 status TEXT NOT NULL DEFAULT 'queued',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 sent_at TIMESTAMPTZ,
 UNIQUE(kind,subject)
);
