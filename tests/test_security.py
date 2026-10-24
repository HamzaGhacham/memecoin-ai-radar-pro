import unittest
from radar.security import evaluate_mint_rpc, TOKEN_CLASSIC, TOKEN_2022, MANDATORY_CHECKS, get_account_info_request
from radar.models import CheckStatus, SecurityDecision

MINT='11111111111111111111111111111111'
def response(owner=TOKEN_CLASSIC, mint_authority=None,freeze_authority=None):
    info = {'mintAuthority': mint_authority, 'freezeAuthority': freeze_authority}
    return {'result': {'value': {'owner': owner, 'data': {'parsed': {'type': 'mint', 'info': info}}}}}
class SecurityTests(unittest.TestCase):
    def statuses(self,r):
        return {ck.code:ck.status for ck in r.checks}
    def test_clean_classic_still_hold(self):
        r=evaluate_mint_rpc(MINT,response())
        self.assertEqual(r.decision,SecurityDecision.HOLD_UNKNOWN)
        self.assertEqual(self.statuses(r)['C01'],CheckStatus.PASS)
        self.assertEqual(self.statuses(r)['C03'],CheckStatus.NOT_APPLICABLE)
        self.assertEqual(self.statuses(r)['L07'],CheckStatus.UNKNOWN)
        self.assertIsNone(r.risk_score)
        self.assertFalse(r.mandatory_complete)
    def test_mint_authority_reject(self):
        r=evaluate_mint_rpc(MINT,response(mint_authority=MINT))
        self.assertEqual(r.decision,SecurityDecision.REJECT_SECURITY)
        self.assertEqual(self.statuses(r)['C01'],CheckStatus.HARD_REJECT)
    def test_freeze_authority_reject(self):
        r=evaluate_mint_rpc(MINT,response(freeze_authority=MINT))
        self.assertEqual(r.decision,SecurityDecision.REJECT_SECURITY)
        self.assertEqual(self.statuses(r)['C02'],CheckStatus.HARD_REJECT)
    def test_token_program_ids(self):
        self.assertEqual(TOKEN_CLASSIC, 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
        self.assertEqual(TOKEN_2022, 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')
    def test_2022_never_passes_without_extension_parser(self):
        r=evaluate_mint_rpc(MINT,response(owner=TOKEN_2022))
        self.assertEqual(self.statuses(r)['C03'],CheckStatus.UNKNOWN)
        self.assertEqual(r.decision,SecurityDecision.HOLD_UNKNOWN)
    def test_unrecognized_program_rejected(self):
        r=evaluate_mint_rpc(MINT,response(owner='NotATokenProgram'))
        self.assertEqual(self.statuses(r)['C10'],CheckStatus.HARD_REJECT)
    def test_rpc_none_unknown(self):
        r=evaluate_mint_rpc(MINT,None)
        self.assertEqual(r.decision,SecurityDecision.HOLD_UNKNOWN)
        self.assertTrue(all(ck.status==CheckStatus.UNKNOWN for ck in r.checks))
    def test_missing_authority_not_assumed_null(self):
        v=response()
        del v['result']['value']['data']['parsed']['info']['mintAuthority']
        self.assertEqual(self.statuses(evaluate_mint_rpc(MINT,v))['C01'],CheckStatus.UNKNOWN)
    def test_invalid_mint_rejected_as_input(self):
        with self.assertRaises(ValueError):
            evaluate_mint_rpc('INVALID',response())
    def test_malformed_rpc_result_is_unknown(self):
        r=evaluate_mint_rpc(MINT, {'result':None})
        self.assertEqual(r.decision,SecurityDecision.HOLD_UNKNOWN)
    def test_no_rpc_write(self):
        self.assertEqual(get_account_info_request(MINT)['method'],'getAccountInfo')
        self.assertEqual(len(MANDATORY_CHECKS),len(set(MANDATORY_CHECKS)))
