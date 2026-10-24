"""Integration tests verify RPC budget and contract-first sequencing."""
import io
import json
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from radar.cli import main
from radar.models import Candidate
from radar.security import TOKEN_CLASSIC

MINT1='11111111111111111111111111111111'
MINT2='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'

class DummyTransport:
    instance = None
    def __init__(self,*args,**kwargs):
        self.calls = []
        DummyTransport.instance=self
    def request(self,url,*,payload=None):
        self.calls.append(payload)
        method=payload['method']
        if method == 'getAccountInfo':
            return {'result':{'context':{'slot':1000}, 'value':{'owner':TOKEN_CLASSIC,'data':{'parsed':{'type':'mint','info':{
                    'mintAuthority':None,'freezeAuthority':None,'supply':'1000'}}}}}}
        if method == 'getTokenLargestAccounts':
            return {'result':{'context':{'slot':1001},'value':[
                {'address':MINT1,'amount':'200'}, {'address':MINT2,'amount':'100'}]}}
        raise AssertionError('Unexpected RPC method '+method)


def sample(mint):
    now=datetime.now(timezone.utc)
    return Candidate(mint=mint,pool='test-pool',dex='test',created_at=now-timedelta(minutes=30),observed_at=now,
                     liquidity_usd=Decimal('30000'),volume_5m_usd=Decimal('5000'),volume_1h_usd=Decimal('10000'),
                     buys_5m=20,sells_5m=10,trades_1h=120,price_change_1h_pct=Decimal('12'))


def report(count):
    return {'pages_ok':2, 'unique_tokens_seen':count, 'discovery_preselected':count,
            'discovery_ineligible':0,'discovery_unknown':0, 'partial_error':None,
            'sources_checked':['new_pools','trending_pools_1h'],'source_stats':{},
            'first_failure_reasons':{},'raw_pool_rows':count, 'parsed_pool_rows':count}

class HolderCliTests(unittest.TestCase):
    def _run(self, count):
        selected=[(sample(m),'PENDING_HISTORY','prefilter') for m in [MINT1,MINT2][:count]]
        out=io.StringIO()
        with patch('radar.cli.JsonTransport', DummyTransport), patch('radar.cli.select_hybrid_candidates', return_value=(selected,report(count))), redirect_stdout(out):
            status=main(['--mode','live','--rpc-check','--holder-check','--max-candidates',str(count)])
        return status,[json.loads(line) for line in out.getvalue().strip().splitlines()], DummyTransport.instance

    def test_contract_first_and_budget_three_for_two_candidates(self):
        status,lines,t=self._run(2)
        self.assertEqual(status,0)
        self.assertEqual([c['method'] for c in t.calls], ['getAccountInfo','getAccountInfo','getTokenLargestAccounts'])
        self.assertEqual(lines[-1]['rpc_requests_used'],3)
        self.assertEqual(lines[1]['holder_account_diagnostics']['status'],'RAW_ACCOUNTS_ONLY')
        self.assertEqual(lines[2]['holder_account_diagnostics']['status'],'BUDGET_EXHAUSTED')
        self.assertEqual(lines[2]['security_contract_checks']['C10'],'PASS')
        self.assertFalse(lines[1]['ready_for_alert'])
        self.assertIn('W01',lines[1]['security_unknown_checks'])

    def test_one_candidate_uses_two_calls(self):
        _,lines,t=self._run(1)
        self.assertEqual(len(t.calls),2)
        self.assertEqual(lines[-1]['rpc_requests_used'],2)

    def test_holder_check_requires_rpc(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as err:
            main(['--mode','live','--holder-check'])
        self.assertEqual(err.exception.code,2)
