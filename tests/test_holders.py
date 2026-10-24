import unittest
from radar.holders import largest_accounts_request, inspect_raw_account_concentration

KEY = '11111111111111111111111111111111'
OTHER = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'

def mint(supply='1000',slot=1000):
    return {'result':{'context':{'slot':slot}, 'value': {'data':{'parsed':{'type':'mint','info':{'supply':supply}}}}}}

def largest(amounts=('300','200'),slot=1001):
    addresses=[KEY,OTHER]
    if len(amounts)>2:
        addresses += [KEY]*len(amounts)
    return {'result':{'context':{'slot':slot},'value':[{'address':addresses[i], 'amount':a} for i,a in enumerate(amounts)]}}

class HolderTests(unittest.TestCase):
    def test_request_read_only(self):
        self.assertEqual(largest_accounts_request(KEY)['method'],'getTokenLargestAccounts')
        with self.assertRaises(ValueError): largest_accounts_request('wrong')
    def test_raw_account_percentages_never_pass_w01_w02(self):
        r=inspect_raw_account_concentration(mint(),largest())
        self.assertEqual(r['status'],'RAW_ACCOUNTS_ONLY')
        self.assertEqual(r['top_1_token_account_pct'],'30.00')
        self.assertEqual(r['top_10_token_accounts_pct'],'50.00')
        self.assertEqual(r['w01_w02_security_status'],'UNKNOWN')
        self.assertFalse(r['wallet_concentration_verified'])
        self.assertEqual(len(r['raw_flags']),2)
    def test_missing_supply_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint(None),largest())['status'],'UNKNOWN')
    def test_zero_supply_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint('0'),largest())['status'],'UNKNOWN')
    def test_rpc_error_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint(),{'error':{'code':429}})['status'],'UNKNOWN')
    def test_empty_top_list_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint(),largest(()) )['status'],'UNKNOWN')
    def test_sum_larger_than_supply_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint('400'),largest())['status'],'UNKNOWN')
    def test_invalid_amount_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint(),largest(('-1','10')))['status'],'UNKNOWN')
        self.assertEqual(inspect_raw_account_concentration(mint(),largest(('NaN','10')))['status'],'UNKNOWN')
    def test_out_of_order_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint(),largest(('100','300')))['status'],'UNKNOWN')
    def test_duplicate_token_account_unknown(self):
        d=largest();d['result']['value'][1]['address']=KEY
        self.assertEqual(inspect_raw_account_concentration(mint(),d)['status'],'UNKNOWN')
    def test_stale_slot_unknown(self):
        self.assertEqual(inspect_raw_account_concentration(mint(slot=100),largest(slot=600))['status'],'UNKNOWN')
    def test_missing_slot_unknown(self):
        d=largest();del d['result']['context']['slot']
        self.assertEqual(inspect_raw_account_concentration(mint(),d)['status'],'UNKNOWN')
