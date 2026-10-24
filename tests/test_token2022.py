import unittest
from radar.security import evaluate_mint_rpc, TOKEN_2022
from radar.models import CheckStatus, SecurityDecision

MINT = '11111111111111111111111111111111'


def payload(extensions):
    info = {'mintAuthority': None, 'freezeAuthority': None}
    if extensions is not ...:
        info['extensions'] = extensions
    return {'result': {'value': {'owner': TOKEN_2022,
        'data': {'parsed': {'type':'mint','info': info}}}}}


def state(report, code):
    return next(x.status for x in report.checks if x.code == code)


class Token2022ExtensionsTests(unittest.TestCase):
    def test_empty_explicit_inventory_not_missing(self):
        report = evaluate_mint_rpc(MINT, payload([]))
        for code in ('C03','C04','C05','C06','C07','C08','C09'):
            self.assertEqual(state(report,code),CheckStatus.NOT_APPLICABLE)
        self.assertEqual(report.decision, SecurityDecision.HOLD_UNKNOWN)

    def test_missing_inventory_fails_closed(self):
        report=evaluate_mint_rpc(MINT,payload(...))
        self.assertEqual(state(report,'C03'),CheckStatus.UNKNOWN)

    def test_nonlist_inventory_fails_closed(self):
        self.assertEqual(state(evaluate_mint_rpc(MINT,payload({})),'C09'),CheckStatus.UNKNOWN)

    def test_permanent_delegate_hard_reject(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'permanentDelegate','state':{'delegate':MINT}}]))
        self.assertEqual(state(r,'C03'),CheckStatus.HARD_REJECT)
        self.assertEqual(r.decision,SecurityDecision.REJECT_SECURITY)

    def test_non_transferable_hard_reject(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'nonTransferable'}]))
        self.assertEqual(state(r,'C04'),CheckStatus.HARD_REJECT)

    def test_frozen_default_hard_reject(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'defaultAccountState','state':{'accountState':'frozen'}}]))
        self.assertEqual(state(r,'C05'),CheckStatus.HARD_REJECT)

    def test_default_state_incomplete_unknown(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'defaultAccountState'}]))
        self.assertEqual(state(r,'C05'),CheckStatus.UNKNOWN)

    def test_pausable_and_hook_hard_reject(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'pausable'},{'extension':'transferHook','state':{'programId':MINT}}]))
        self.assertEqual(state(r,'C06'),CheckStatus.HARD_REJECT)
        self.assertEqual(state(r,'C07'),CheckStatus.HARD_REJECT)

    def test_high_fixed_fee_hard_reject(self):
        fee={'extension':'transferFeeConfig','state':{'transferFeeConfigAuthority':None,
             'olderTransferFee':{'transferFeeBasisPoints': 600},
             'newerTransferFee':{'transferFeeBasisPoints': 50}}}
        r=evaluate_mint_rpc(MINT,payload([fee]))
        self.assertEqual(state(r,'C08'),CheckStatus.HARD_REJECT)

    def test_mutable_fee_hard_reject(self):
        fee={'extension':'transferFeeConfig','state':{'transferFeeConfigAuthority':MINT,
             'olderTransferFee':{'transferFeeBasisPoints': 0},
             'newerTransferFee':{'transferFeeBasisPoints': 0}}}
        r=evaluate_mint_rpc(MINT,payload([fee]))
        self.assertEqual(state(r,'C08'),CheckStatus.HARD_REJECT)

    def test_medium_fee_warning(self):
        fee={'extension':'transferFeeConfig','state':{'transferFeeConfigAuthority':None,
             'olderTransferFee':{'transferFeeBasisPoints': 150},
             'newerTransferFee':{'transferFeeBasisPoints': 150}}}
        r=evaluate_mint_rpc(MINT,payload([fee]))
        self.assertEqual(state(r,'C08'),CheckStatus.WARNING)

    def test_incomplete_fee_unknown(self):
        fee={'extension':'transferFeeConfig','state':{'newerTransferFee':{'transferFeeBasisPoints': 250}}}
        self.assertEqual(state(evaluate_mint_rpc(MINT,payload([fee])),'C08'),CheckStatus.UNKNOWN)

    def test_unrecognized_extension_unknown(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'confidentialTransferMint'}]))
        self.assertEqual(state(r,'C09'),CheckStatus.UNKNOWN)

    def test_malformed_extension_unknown(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'metadataPointer'},42]))
        self.assertEqual(state(r,'C09'),CheckStatus.UNKNOWN)

    def test_duplicate_extension_unknown(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'tokenMetadata'},{'extension':'tokenMetadata'}]))
        self.assertEqual(state(r,'C09'),CheckStatus.UNKNOWN)

    def test_metadata_alone_never_yields_global_pass(self):
        r=evaluate_mint_rpc(MINT,payload([{'extension':'metadataPointer'}]))
        self.assertEqual(state(r,'C09'),CheckStatus.NOT_APPLICABLE)
        self.assertEqual(r.decision,SecurityDecision.HOLD_UNKNOWN)
        self.assertFalse(r.mandatory_complete)
