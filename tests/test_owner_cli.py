"""Integration checks preserve contract-first and the RPC ceiling."""
import io
import json
import unittest
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from radar.models import Candidate
from radar.cli import main
from radar.security import TOKEN_CLASSIC

MINT = '11111111111111111111111111111111'
OTHER = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
AUTH = 'SysvarRent111111111111111111111111111111111'

class StubTransport:
    last = None
    def __init__(self,*a,**k):
        self.calls=[];StubTransport.last=self
    def request(self,url,*,payload=None):
        self.calls.append(payload['method'])
        if payload['method']=='getAccountInfo':
            return {'result':{'context':{'slot':1000},'value':{'owner':TOKEN_CLASSIC,'data':{'parsed':{
                'type':'mint','info':{'mintAuthority':None,'freezeAuthority':None,'supply':'1000'}}}}}}
        if payload['method']=='getTokenLargestAccounts':
            return {'result':{'context':{'slot':1001},'value':[
                {'address':MINT,'amount':'200'},{'address':OTHER,'amount':'100'}]}}
        if payload['method']=='getMultipleAccounts':
            rows=[]
            for n in ['200','100']:
                info={'mint':MINT,'owner':AUTH,'tokenAmount':{'amount':n}}
                rows.append({'owner':TOKEN_CLASSIC,'data':{'parsed':{'type':'account','info':info}}})
            return {'result':{'context':{'slot':1002},'value':rows}}
        raise AssertionError('Unexpected RPC method')

def candidate(mint):
    now=datetime.now(timezone.utc)
    return Candidate(mint=mint,pool='sample-pool',dex='example',created_at=now-timedelta(minutes=30),observed_at=now,
                     liquidity_usd=Decimal('20000'),volume_5m_usd=Decimal('4000'),volume_1h_usd=Decimal('50000'),
                     buys_5m=20,sells_5m=7,trades_1h=120,price_change_1h_pct=Decimal('11'))
def report(n):
    return {'pages_ok':2, 'unique_tokens_seen':n, 'discovery_preselected':n,
            'discovery_ineligible':0,'discovery_unknown':0, 'partial_error':None,
            'sources_checked':[],'source_stats':{},'first_failure_reasons':{},'raw_pool_rows':n,'parsed_pool_rows':n}

class OwnerCliTests(unittest.TestCase):
    def run_cli(self,mints):
        selected=[(candidate(m),'PENDING_HISTORY','test') for m in mints]
        stdout=io.StringIO()
        with patch('radar.cli.JsonTransport',StubTransport),patch('radar.cli.select_hybrid_candidates',return_value=(selected,report(len(mints)))),redirect_stdout(stdout):
            result=main(['--mode','live','--rpc-check','--holder-check','--owner-check','--max-candidates',str(len(mints))])
        return result,[json.loads(l) for l in stdout.getvalue().splitlines()],StubTransport.last.calls
    def test_one_candidate_uses_three_readonly_rpc_requests(self):
        status,lines,calls=self.run_cli([MINT])
        self.assertEqual(status,0)
        self.assertEqual(calls,['getAccountInfo','getTokenLargestAccounts','getMultipleAccounts'])
        self.assertEqual(lines[-1]['rpc_requests_used'],3)
        self.assertEqual(lines[1]['owner_authority_diagnostics']['status'],'OBSERVED_ACCOUNT_AUTHORITIES_ONLY')
        self.assertEqual(lines[1]['security_decision'],'HOLD_UNKNOWN')
        self.assertFalse(lines[1]['ready_for_alert'])
    def test_two_candidates_contract_checks_come_first_and_budget_prevents_extra(self):
        _,lines,calls=self.run_cli([MINT,OTHER])
        self.assertEqual(calls,['getAccountInfo','getAccountInfo','getTokenLargestAccounts'])
        self.assertEqual(lines[-1]['rpc_requests_used'],3)
        self.assertEqual(lines[1]['owner_authority_diagnostics']['status'],'BUDGET_EXHAUSTED')
        self.assertFalse(lines[2]['ready_for_alert'])
    def test_owner_check_requires_holder(self):
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            main(['--mode','live','--rpc-check','--owner-check'])

if __name__=='__main__': unittest.main()
