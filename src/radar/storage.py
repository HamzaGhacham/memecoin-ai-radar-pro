"""Persistent storage adapter. SQLite for offline tests, Neon PostgreSQL for deployment.

Never write API secrets or authentication URLs to stored JSON.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sqlite3
import uuid

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS scan_runs (
 id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
 mode TEXT NOT NULL, scanned INTEGER NOT NULL, preselected INTEGER NOT NULL,
 selected INTEGER NOT NULL, status TEXT NOT NULL, source_error TEXT, version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL, mint TEXT NOT NULL,
 pool TEXT NOT NULL, observed_at TEXT NOT NULL, scanner TEXT NOT NULL,
 discovery_status TEXT NOT NULL, security_decision TEXT NOT NULL,
 security_unknown_count INTEGER NOT NULL, liquidity_usd TEXT,
 raw_top1_pct TEXT, raw_top10_pct TEXT, pool_status TEXT,
 raw_data TEXT NOT NULL, UNIQUE (run_id,mint,pool)
);
CREATE INDEX IF NOT EXISTS observations_mint_time ON observations(mint,observed_at DESC);
CREATE TABLE IF NOT EXISTS watchlist (mint TEXT PRIMARY KEY,added_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pending_jobs (
 id TEXT PRIMARY KEY, requested_by TEXT NOT NULL, kind TEXT NOT NULL,
 mint TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error_text TEXT
);
CREATE TABLE IF NOT EXISTS alerts_outbox (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT NOT NULL,
 payload TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
 sent_at TEXT, UNIQUE(kind,subject)
);
"""

class Store:
    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError('Database URL/path required for persisted scans')
        self.pg = dsn.startswith(('postgresql://', 'postgres://'))
        if self.pg:
            try:
                import psycopg
            except ImportError as exc:
                raise RuntimeError('Install deployment extra: pip install -e ".[neon]"') from exc
            self.db = psycopg.connect(dsn, connect_timeout=12)
        else:
            if dsn.startswith(('http://','https://')):
                raise ValueError('Invalid database DSN')
            self.db = sqlite3.connect(dsn)
            self.db.row_factory = sqlite3.Row
            self.db.executescript(SQLITE_DDL)
            self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.db.rollback()
        self.close()

    def initialize(self):
        if self.pg:
            schema = Path(__file__).resolve().parents[2] / 'db/schema.sql'
            # Execute separate commands for connector compatibility.
            with self.db.cursor() as cur:
                for stmt in schema.read_text(encoding='utf8').split(';'):
                    if stmt.strip():
                        cur.execute(stmt)
            self.db.commit()

    def _exec(self, sql, args=()):
        cur = self.db.cursor()
        try:
            cur.execute(sql if self.pg else sql.replace('%s','?'), args)
            return cur.fetchall() if cur.description else []
        finally:
            cur.close()

    def save_scan(self, header, rows, *, started_at, finished_at, mode, status='OK'):
        run_id = str(uuid.uuid4())
        try:
            self._exec('INSERT INTO scan_runs (id,started_at,finished_at,mode,scanned,preselected,selected,status,source_error,version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(
                run_id,started_at,finished_at,mode,int(header.get('unique_tokens_seen',0)),
                int(header.get('discovery_preselected',0)),len(rows),status,
                str(header.get('partial_source_error') or '')[:240], 'integration-v0.2.0'))
            for row in rows:
                # Prevent accidental credential leakage: explicitly select validated, public fields only.
                clean = {k:row.get(k) for k in (
                    'mint','pool','observed_at','age_minutes','liquidity_usd',
                    'volume_5m_usd','volume_1h_usd','buys_5m','sells_5m','trades_1h',
                    'price_change_1h_pct','discovery_status','discovery_reason','security_decision',
                    'security_contract_checks','security_unknown_checks','security_reject_reasons',
                    'holder_account_diagnostics','owner_authority_diagnostics','pool_program_diagnostics',
                    'risk_score','ready_for_alert')}
                holders = row.get('holder_account_diagnostics') or {}
                scanner = ('EARLY' if (row.get('age_minutes') or 0)<360 else 'MOMENTUM')
                payload = json.dumps(clean,ensure_ascii=False)
                stored_json = json.dumps(clean, ensure_ascii=False)
                if self.pg:
                    from psycopg.types.json import Jsonb
                    stored_json = Jsonb(clean)
                self._exec('INSERT INTO observations (id,run_id,mint,pool,observed_at,scanner,discovery_status,security_decision,security_unknown_count,liquidity_usd,raw_top1_pct,raw_top10_pct,pool_status,raw_data) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(
                    str(uuid.uuid4()),run_id,row['mint'],row['pool'],row['observed_at'],scanner,
                    row.get('discovery_status','HOLD_UNKNOWN'),row.get('security_decision','HOLD_UNKNOWN'),
                    len(row.get('security_unknown_checks') or []),row.get('liquidity_usd'),
                    holders.get('top_1_token_account_pct'),holders.get('top_10_token_accounts_pct'),
                    (row.get('pool_program_diagnostics') or {}).get('status'),
                    stored_json))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return run_id

    def research_history(self, mint, at_time=None):
        """Only establishes repeated *observations*, never validates opportunity signals."""
        from datetime import datetime
        obs=self.recent_observations(mint,limit=5)
        if len(obs)<2:
            return {'distinct_observations':len(obs),'state':'INSUFFICIENT_HISTORY','opportunity_confirmed':False}
        current=datetime.fromisoformat(obs[0]['observed_at'])
        for prior in obs[1:]:
            before=datetime.fromisoformat(prior['observed_at'])
            gap=(current-before).total_seconds()/60
            if 4 <= gap <= 60 and obs[0]['discovery_status']=='PENDING_HISTORY' and prior['discovery_status']=='PENDING_HISTORY':
                return {'distinct_observations':2,'state':'TWO_MARKET_OBSERVATIONS_ONLY',
                        'minutes_between':round(gap,2),'opportunity_confirmed':False,
                        'note':'Volume acceleration, full security and final opportunity score remain unverified'}
        return {'distinct_observations':len(obs),'state':'STALE_OR_INSUFFICIENT_SEPARATION',
                'opportunity_confirmed':False}

    def recent_observations(self,mint,limit=5):
        from .validation import is_valid_mint
        if not is_valid_mint(mint):
            raise ValueError('Invalid mint')
        rows = self._exec('SELECT observed_at,discovery_status,security_decision,raw_data FROM observations WHERE mint=%s ORDER BY observed_at DESC LIMIT %s',(mint,min(limit,30)))
        return [dict(observed_at=str(r[0]),discovery_status=r[1],security_decision=r[2],data=json.loads(r[3]) if isinstance(r[3],str) else r[3]) for r in rows]

    def queued_scan_jobs(self, limit=5):
        rows=self._exec("SELECT id,requested_by FROM pending_jobs WHERE kind='scan' AND status='queued' ORDER BY created_at LIMIT %s",(min(limit,5),))
        return [{'id':r[0], 'requested_by':str(r[1])} for r in rows]

    def mark_scan_job(self,job_id,status):
        if status not in ('done','failed'):
            raise ValueError('Invalid job status')
        if self.pg:
            self._exec('UPDATE pending_jobs SET status=%s,updated_at=now() WHERE id=%s AND status=%s',(status,job_id,'queued'))
        else:
            self._exec('UPDATE pending_jobs SET status=%s,updated_at=%s WHERE id=%s AND status=%s',(
                status,datetime.now(timezone.utc).isoformat(),job_id,'queued'))
        self.db.commit()

    def latest_summary(self):
        r=self._exec('SELECT id,finished_at,scanned,preselected,selected,status FROM scan_runs ORDER BY finished_at DESC LIMIT 1')
        if not r: return None
        return dict(zip(('id','finished_at','scanned','preselected','selected','status'),r[0]))
