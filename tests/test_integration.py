import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from radar.service import perform_once, capture_scan, main
from radar.storage import Store

class IntegrationTests(unittest.TestCase):
    def test_demo_capture_no_alert(self):
        header,rows=capture_scan()
        self.assertEqual(header['stage'],'STAGE1_READ_ONLY')
        self.assertFalse(rows[0]['ready_for_alert'])
        self.assertEqual(rows[0]['data_confirmation'],'PENDING_SECOND_VALID_SNAPSHOT')
    def test_sqlite_persists_safe_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            dsn=str(Path(folder)/'radar.sqlite3')
            result=perform_once(dsn=dsn)
            self.assertEqual(result['opportunity_alert_count'],0)
            with Store(dsn) as store:
                last=store.latest_summary()
                self.assertEqual(last['selected'],1)
                rows=store.recent_observations(result['candidates'][0]['mint'])
                self.assertEqual(len(rows),1)
                self.assertFalse(rows[0]['data']['ready_for_alert'])
    def test_requires_database(self):
        with self.assertRaises(ValueError):
            perform_once(require_database=True)
    def test_invalid_db_url(self):
        with self.assertRaises(ValueError):
            Store('https://invalid.example')
    def test_init_db_no_secret_exposure(self):
        with patch.dict(os.environ,{'DATABASE_URL':'postgresql://SENSITIVE','SOLANA_RPC_URL':'SENSITIVE'},clear=True):
            stream=io.StringIO()
            with patch('sys.stdout',stream):
                rc=main(['--mode','live','--max-candidates','1','--require-database'])
            self.assertEqual(rc,2)
            self.assertNotIn('SENSITIVE',stream.getvalue())
            self.assertIn('FAIL_CLOSED',stream.getvalue())
    def test_bad_mint_cannot_query(self):
        with Store(':memory:') as store:
            with self.assertRaises(ValueError):
                store.recent_observations('INVALID')

if __name__=='__main__':unittest.main()

class ReportTests(unittest.TestCase):
    def test_research_not_a_buy_alert(self):
        from radar.telegram_ops import format_research_report
        msg=format_research_report({'mode':'live','scanned':38,'preselected':2,'selected':1})
        self.assertIn('Opportunity signals: 0',msg)
        self.assertIn('not a buy recommendation',msg)

    def test_jobs_can_be_marked_done(self):
        from datetime import datetime, timezone
        now=datetime.now(timezone.utc).isoformat()
        with Store(':memory:') as store:
            store._exec('INSERT INTO pending_jobs(id,requested_by,kind,mint,status,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)',('job-1','123','scan',None,'queued',now,now))
            store.db.commit()
            self.assertEqual(store.queued_scan_jobs()[0]['id'],'job-1')
            store.mark_scan_job('job-1','done')
            self.assertEqual(store.queued_scan_jobs(),[])

class ConfirmationEvidenceTests(unittest.TestCase):
    def test_one_snapshot_never_confirms_opportunity(self):
        with Store(':memory:') as store:
            report=store.research_history('11111111111111111111111111111111')
            self.assertEqual(report['state'],'INSUFFICIENT_HISTORY')
            self.assertFalse(report['opportunity_confirmed'])

    def test_two_demo_runs_still_never_opportunity(self):
        with tempfile.TemporaryDirectory() as temp:
            path=str(Path(temp)/'samples.db')
            first=perform_once(dsn=path)
            second=perform_once(dsn=path)
            with Store(path) as store:
                evidence=store.research_history(first['candidates'][0]['mint'])
                self.assertNotEqual(evidence['state'],'TWO_MARKET_OBSERVATIONS_ONLY')
                self.assertFalse(evidence['opportunity_confirmed'])
