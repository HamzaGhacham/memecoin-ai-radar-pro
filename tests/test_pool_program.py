"""v0.1.6 pool account program identity is *diagnostic*, not LP verification."""
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from unittest.mock import patch
from radar.owner_diagnostics import owner_accounts_request, inspect_observed_owners
from radar.pool_program import inspect_pool_program, KNOWN_PROGRAMS
from radar.cli import main
from radar.security import TOKEN_CLASSIC
from test_owner_cli import StubTransport, candidate, report, MINT, OTHER, AUTH

POOL = 'SysvarC1ock11111111111111111111111111111111'
PUMPSWAP = 'pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA'


def largest():
    return {'result': {'context': {'slot': 1001}, 'value': [
        {'address': MINT, 'amount': '200'}, {'address': OTHER, 'amount': '100'}
    ]}}


def owners(pool_owner=PUMPSWAP, *, include_pool=True, slot=1002, executable=False):
    rows = []
    for amount in ('200', '100'):
        rows.append({'owner': TOKEN_CLASSIC, 'data': {'parsed': {'type': 'account',
            'info': {'mint': MINT, 'owner': AUTH, 'tokenAmount': {'amount': amount}}}}})
    if include_pool:
        rows.append({'owner': pool_owner, 'executable': executable, 'data': ['AA==', 'base64']})
    return {'result': {'context': {'slot': slot}, 'value': rows}}


class PoolProgramTests(unittest.TestCase):
    def test_add_pool_to_existing_batch_no_extra_request(self):
        req = owner_accounts_request(largest(), pool_address=POOL)
        self.assertEqual(req['method'], 'getMultipleAccounts')
        self.assertEqual(req['params'][0], [MINT, OTHER, POOL])
        self.assertEqual(req['params'][1]['encoding'], 'jsonParsed')

    def test_pool_and_owner_inspection_can_use_same_batch(self):
        from test_owner_diagnostics import mint
        batch = owners()
        r = inspect_observed_owners(MINT, mint(), largest(), batch, expect_pool=True)
        p = inspect_pool_program(POOL, largest(), batch, owner_batch_includes_pool=True)
        self.assertEqual(r['status'], 'OBSERVED_ACCOUNT_AUTHORITIES_ONLY')
        self.assertEqual(r['unique_authorities_in_top_accounts'], 1)
        self.assertEqual(p['status'], 'PROGRAM_RECOGNIZED_NOT_POOL_VERIFIED')
        self.assertEqual(p['program_family'], 'PUMPSWAP_AMM')
        self.assertTrue(p['pool_account_verified'])
        self.assertFalse(p['pool_vaults_classified'])
        self.assertEqual(p['l02_l07_l08_security_status'], 'UNKNOWN')
        self.assertEqual(p['w01_w02_security_status'], 'UNKNOWN')

    def test_unexpected_pool_row_not_accepted_in_legacy_owner_mode(self):
        from test_owner_diagnostics import mint
        r = inspect_observed_owners(MINT, mint(), largest(), owners(), expect_pool=False)
        self.assertEqual(r['status'], 'UNKNOWN')

    def test_missing_rpc_unknown(self):
        self.assertEqual(inspect_pool_program(POOL, largest(), None, owner_batch_includes_pool=True)['status'], 'UNKNOWN')

    def test_missing_pool_account_unknown(self):
        batch = owners(); batch['result']['value'][-1] = None
        self.assertEqual(inspect_pool_program(POOL, largest(), batch, owner_batch_includes_pool=True)['status'], 'UNKNOWN')

    def test_unknown_program_not_automatically_scam(self):
        x = inspect_pool_program(POOL, largest(), owners(pool_owner=MINT), owner_batch_includes_pool=True)
        self.assertEqual(x['status'], 'PROGRAM_UNRECOGNIZED')
        self.assertEqual(x['l02_l07_l08_security_status'], 'UNKNOWN')

    def test_pool_address_invalid_or_not_in_batch(self):
        self.assertEqual(inspect_pool_program('not-a-key', largest(), owners(), owner_batch_includes_pool=True)['status'], 'UNKNOWN')
        self.assertEqual(inspect_pool_program(POOL, largest(), owners(include_pool=False), owner_batch_includes_pool=False)['status'], 'UNKNOWN')
        with self.assertRaises(ValueError):
            owner_accounts_request(largest(), pool_address=MINT)

    def test_executable_pool_never_verifies(self):
        p = inspect_pool_program(POOL, largest(), owners(executable=True), owner_batch_includes_pool=True)
        self.assertEqual(p['status'], 'UNKNOWN')
        self.assertFalse(p['pool_account_verified'])

    def test_stale_rpc_slot_unknown(self):
        p = inspect_pool_program(POOL, largest(), owners(slot=1400), owner_batch_includes_pool=True)
        self.assertEqual(p['status'], 'UNKNOWN')

    def test_broken_batch_length_unknown(self):
        self.assertEqual(inspect_pool_program(POOL, largest(), owners(include_pool=False), owner_batch_includes_pool=True)['status'], 'UNKNOWN')

    def test_trusted_protocol_ids_exist(self):
        self.assertEqual(KNOWN_PROGRAMS[PUMPSWAP], 'PUMPSWAP_AMM')
        self.assertEqual(len(KNOWN_PROGRAMS), 4)

    def test_never_signs_or_trades(self):
        self.assertNotIn(owner_accounts_request(largest(), pool_address=POOL)['method'], {'sendTransaction', 'simulateTransaction'})


class PoolCliTests(unittest.TestCase):
    def test_pool_check_requires_owner(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['--pool-check'])

    def test_pool_check_readonly_shared_third_rpc(self):
        class PoolStubTransport(StubTransport):
            def request(self, url, *, payload=None):
                if payload['method'] == 'getMultipleAccounts':
                    self.calls.append(payload['method'])
                    self.batch_addresses = payload['params'][0]
                    return owners()
                return super().request(url, payload=payload)
        instance = {}
        def stub_factory():
            x = PoolStubTransport()
            instance['client'] = x
            return x
        c = replace(candidate(MINT), pool=POOL)
        out = io.StringIO()
        with patch('radar.cli.JsonTransport', stub_factory), patch('radar.cli.select_hybrid_candidates',
                return_value=([(c, 'PENDING_HISTORY', 'test')], report(1))), redirect_stdout(out):
            result = main(['--mode', 'live', '--rpc-check', '--holder-check', '--owner-check', '--pool-check', '--max-candidates', '1'])
        lines = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(result, 0)
        self.assertEqual(instance['client'].calls, ['getAccountInfo','getTokenLargestAccounts','getMultipleAccounts'])
        self.assertEqual(len(instance['client'].batch_addresses), 3)
        self.assertEqual(lines[1]['pool_program_diagnostics']['status'], 'PROGRAM_RECOGNIZED_NOT_POOL_VERIFIED')
        self.assertEqual(lines[1]['security_decision'], 'HOLD_UNKNOWN')
        self.assertFalse(lines[1]['ready_for_alert'])
        self.assertEqual(lines[-1]['rpc_requests_used'], 3)
        self.assertTrue(lines[-1]['pool_diagnostics_enabled'])

if __name__ == '__main__':
    unittest.main()
