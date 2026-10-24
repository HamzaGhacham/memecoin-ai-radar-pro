"""Tests for safe read-only owner aggregation of observed token accounts."""
import unittest
from radar.owner_diagnostics import owner_accounts_request, inspect_observed_owners
from radar.security import TOKEN_CLASSIC

MINT = '11111111111111111111111111111111'
OTHER = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
AUTH = 'SysvarRent111111111111111111111111111111111'

def mint(slot=1000,supply='1000'):
    info = {'supply': supply}
    value = {'owner':TOKEN_CLASSIC,'data':{'parsed':{'type':'mint','info':info}}}
    return {'result':{'context':{'slot':slot},'value':value}}

def largest(slot=1001, amounts=('200','100')):
    rows = [{'address':a,'amount':n} for a,n in zip([MINT,OTHER],amounts)]
    return {'result':{'context':{'slot':slot},'value':rows}}

def owners(slot=1002, authority1=AUTH, authority2=AUTH):
    rows=[]
    for authority,amount in zip([authority1,authority2],['200','100']):
        info={'mint':MINT,'owner':authority,'tokenAmount':{'amount':amount}}
        rows.append({'owner':TOKEN_CLASSIC,'data':{'parsed':{'type':'account','info':info}}})
    return {'result':{'context':{'slot':slot},'value':rows}}

class OwnerDiagnosticsTests(unittest.TestCase):
    def test_batch_request_one_call_for_multiple_accounts(self):
        r = owner_accounts_request(largest())
        self.assertEqual(r['method'],'getMultipleAccounts')
        self.assertEqual(r['params'][0],[MINT,OTHER])
        self.assertEqual(r['params'][1]['encoding'],'jsonParsed')
    def test_group_two_accounts_but_no_wallet_security_pass(self):
        r=inspect_observed_owners(MINT,mint(),largest(),owners())
        self.assertEqual(r['status'],'OBSERVED_ACCOUNT_AUTHORITIES_ONLY')
        self.assertEqual(r['top_1_observed_authority_pct'],'30.00')
        self.assertEqual(r['top_10_observed_authorities_pct'],'30.00')
        self.assertEqual(r['unique_authorities_in_top_accounts'],1)
        self.assertEqual(r['authorities_with_multiple_top_accounts'],1)
        self.assertFalse(r['wallet_concentration_verified'])
        self.assertEqual(r['w01_w02_security_status'],'UNKNOWN')
        self.assertFalse(r['pool_vaults_classified'])
    def test_two_different_authorities(self):
        r=inspect_observed_owners(MINT,mint(),largest(),owners(authority2=OTHER))
        self.assertEqual(r['top_1_observed_authority_pct'],'20.00')
        self.assertEqual(r['unique_authorities_in_top_accounts'],2)
    def test_wrong_mint_unknown(self):
        d=owners();d['result']['value'][0]['data']['parsed']['info']['mint']=OTHER
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),d)['status'],'UNKNOWN')
    def test_wrong_token_program_unknown(self):
        d=owners();d['result']['value'][0]['owner']=MINT
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),d)['status'],'UNKNOWN')
    def test_wrong_token_account_balance_unknown(self):
        d=owners();d['result']['value'][0]['data']['parsed']['info']['tokenAmount']['amount']='199'
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),d)['status'],'UNKNOWN')
    def test_missing_account_unknown(self):
        d=owners();d['result']['value'][0]=None
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),d)['status'],'UNKNOWN')
    def test_missing_response_unknown(self):
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),None)['status'],'UNKNOWN')
    def test_rpc_error_unknown(self):
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),{'error':{'code':429}})['status'],'UNKNOWN')
    def test_slot_gap_unknown(self):
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),owners(slot=1900))['status'],'UNKNOWN')
    def test_bad_list_unknown(self):
        d=owners();d['result']['value']=[]
        self.assertEqual(inspect_observed_owners(MINT,mint(),largest(),d)['status'],'UNKNOWN')
    def test_rpc_owner_request_minimum_slot_prevents_older_data(self):
        request=owner_accounts_request(largest(slot=2040))
        self.assertEqual(request['params'][1]['minContextSlot'],2040)
    def test_balance_drift_has_specific_code_and_slots_without_pass(self):
        payload=owners(slot=1002)
        payload['result']['value'][0]['data']['parsed']['info']['tokenAmount']['amount']='199'
        result=inspect_observed_owners(MINT,mint(),largest(),payload)
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(result['error_code'],'ACCOUNT_BALANCE_DRIFT')
        self.assertEqual(result['balance_mismatch_count'],1)
        self.assertEqual(result['rpc_slots'],[1000,1001,1002])
        self.assertFalse(result['wallet_concentration_verified'])
        self.assertEqual(result['w01_w02_security_status'],'UNKNOWN')
        self.assertNotIn('top_1_observed_authority_pct',result)
    def test_wrong_program_has_specific_code(self):
        payload=owners(); payload['result']['value'][0]['owner']=MINT
        result=inspect_observed_owners(MINT,mint(),largest(),payload)
        self.assertEqual(result['error_code'],'TOKEN_PROGRAM_MISMATCH')
    def test_wrong_mint_has_specific_code(self):
        payload=owners();payload['result']['value'][0]['data']['parsed']['info']['mint']=OTHER
        result=inspect_observed_owners(MINT,mint(),largest(),payload)
        self.assertEqual(result['error_code'],'TOKEN_MINT_MISMATCH')
    def test_unparsed_account_has_specific_code(self):
        payload=owners();payload['result']['value'][0]['data']={'raw':'not-parsed'}
        result=inspect_observed_owners(MINT,mint(),largest(),payload)
        self.assertEqual(result['error_code'],'UNPARSED_TOKEN_ACCOUNT')
    def test_owner_rpc_error_keeps_unknown(self):
        result=inspect_observed_owners(MINT,mint(),largest(),{'error':{'code':429}})
        self.assertEqual(result['error_code'],'OWNER_RPC_UNAVAILABLE')
        self.assertEqual(result['w01_w02_security_status'],'UNKNOWN')
    def test_no_write_rpc_request(self):
        self.assertNotIn(owner_accounts_request(largest())['method'],{'sendTransaction','simulateTransaction','signMessage'})

if __name__=='__main__': unittest.main()
