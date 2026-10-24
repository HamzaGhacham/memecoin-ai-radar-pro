"""One-off scheduled scan entrypoint. Never emits opportunity alerts without verified security."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
import argparse
import json
import os
import sys
from .cli import main as legacy_scan
from .storage import Store


def capture_scan(*,mode='demo', max_candidates=1, rpc=False):
    args=['--mode',mode,'--max-candidates',str(max_candidates)]
    if rpc and mode=='live':
        args += ['--rpc-check','--holder-check','--owner-check','--pool-check']
    out=StringIO()
    with redirect_stdout(out):
        code=legacy_scan(args)
    messages=[]
    for line in out.getvalue().splitlines():
        if line.strip():
            messages.append(json.loads(line))
    if code!=0 or not messages or messages[0].get('stage')!='STAGE1_READ_ONLY':
        raise RuntimeError('Market data scan unavailable or malformed')
    header=messages[0]
    rows=[v for v in messages[1:] if 'mint' in v]
    # The source may be partially unavailable; keep visible errors, never imply PASS.
    for r in rows:
        r['ready_for_alert']=False
        r['security_decision']=r.get('security_decision','HOLD_UNKNOWN')
        r['candidate_scanner']='EARLY' if r['age_minutes']<360 else 'MOMENTUM'
        r['data_confirmation']='PENDING_SECOND_VALID_SNAPSHOT'
    return header,rows


def perform_once(*,mode='demo',max_candidates=1,rpc=False,dsn=None,require_database=False):
    started=datetime.now(timezone.utc).isoformat()
    if require_database and not dsn:
        raise ValueError('Persistent DATABASE_URL required for scheduled operation')
    header,rows=capture_scan(mode=mode,max_candidates=max_candidates,rpc=rpc)
    now=datetime.now(timezone.utc).isoformat()
    result={'run_started_at':started,'run_finished_at':now,'mode':mode,
            'scanned':header.get('unique_tokens_seen',0),
            'preselected':header.get('discovery_preselected',0),
            'selected':len(rows),'source_error':header.get('partial_source_error'),
            'security_release_enabled':False,'opportunity_alert_count':0,
            'candidates':rows}
    if dsn:
        with Store(dsn) as store:
            store.initialize()
            result['run_id']=store.save_scan(header,rows,started_at=started,finished_at=now,mode=mode)
            result['market_history_evidence']={row['mint']:store.research_history(row['mint']) for row in rows}
            # Owner-authenticated /scan requests are satisfied by this scheduled
            # scan. Do not leave them queued forever or pretend it ran instantly.
            jobs=store.queued_scan_jobs()
            result['queued_scan_jobs_seen']=len(jobs)
            from .telegram_ops import notify_owner,format_research_report
            for job in jobs:
                if str(job['requested_by']) != str(os.getenv('TELEGRAM_OWNER_ID','')):
                    # Untrusted/misconfigured owner: never message arbitrary users.
                    store.mark_scan_job(job['id'],'failed')
                elif notify_owner(format_research_report(result)):
                    store.mark_scan_job(job['id'],'done')
                # If delivery failed, leave queued for next run, do not lose request.
    return result


def mode_reports_enabled():
    return os.getenv('SEND_RESEARCH_REPORTS','false').lower() == 'true'


def main(argv=None):
    p=argparse.ArgumentParser(description='Safe scheduled radar integration runner')
    p.add_argument('--mode',choices=['demo','live'],default='demo')
    p.add_argument('--rpc-check',action='store_true')
    p.add_argument('--max-candidates',type=int,default=1)
    p.add_argument('--database-url',default=os.getenv('DATABASE_URL',''))
    p.add_argument('--require-database',action='store_true')
    p.add_argument('--init-db',action='store_true')
    args=p.parse_args(argv)
    try:
        if args.init_db:
            with Store(args.database_url) as store: store.initialize()
            print(json.dumps({'database':'initialized','secrets_exposed':False}))
            return 0
        if args.mode=='live' and args.rpc_check and not os.getenv('SOLANA_RPC_URL'):
            # Do not fall back to rate-limited public RPC for automated jobs.
            raise ValueError('SOLANA_RPC_URL required for scheduled RPC scans')
        result=perform_once(mode=args.mode,max_candidates=args.max_candidates,
                    rpc=args.rpc_check,dsn=args.database_url,require_database=args.require_database)
        if mode_reports_enabled() and result.get('queued_scan_jobs_seen',0)==0:
            from .telegram_ops import notify_owner,format_research_report
            result['research_report_delivered']=notify_owner(format_research_report(result))
        # Only print safe concise stats on GitHub, no mint addresses or full URLs.
        print(json.dumps({k:v for k,v in result.items() if k not in ('candidates','market_history_evidence')},ensure_ascii=False))
        return 0
    except Exception as exc:
        # Do not print exception string, which may contain credential-bearing DSNs.
        print(json.dumps({'status':'FAIL_CLOSED','error_class':type(exc).__name__,
            'opportunity_alert_count':0,'secret_redacted':True}))
        return 2

if __name__=='__main__': sys.exit(main())
