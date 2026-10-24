import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from radar.discovery import parse_new_pools, discovery_prefilter
from radar.transport import SourceError
from radar.cli import _demo_payload, DEMO_MINT, POLICY
from pathlib import Path
import json

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,10,23,12,0,tzinfo=timezone.utc)
        self.policy = json.loads(Path(POLICY).read_text())
        self.payload = _demo_payload(self.now)
    def test_demo_candidate(self):
        parsed = parse_new_pools(self.payload, observed_at=self.now)
        self.assertEqual(len(parsed),1)
        self.assertEqual(parsed[0].mint,DEMO_MINT)
        self.assertEqual(parsed[0].age_minutes,20.0)
        self.assertEqual(parsed[0].liquidity_usd,Decimal(21000))
    def test_early_prefilter_never_confirmed(self):
        c = parse_new_pools(self.payload, observed_at=self.now)[0]
        self.assertEqual(discovery_prefilter(c,self.policy)[0],'PENDING_HISTORY')
    def test_missing_market_values_are_unknown(self):
        self.payload['data'][0]['attributes']['reserve_in_usd']=None
        c = parse_new_pools(self.payload, observed_at=self.now)[0]
        self.assertEqual(discovery_prefilter(c,self.policy)[0],'HOLD_UNKNOWN')
    def test_below_liquidity_ineligible_not_scam(self):
        self.payload['data'][0]['attributes']['reserve_in_usd']='12000'
        c = parse_new_pools(self.payload, observed_at=self.now)[0]
        self.assertEqual(discovery_prefilter(c,self.policy)[0],'INELIGIBLE_DISCOVERY')
    def test_invalid_mint_skipped(self):
        self.payload['data'][0]['relationships']['base_token']['data']['id']='solana_fake-0'
        self.assertEqual(parse_new_pools(self.payload, observed_at=self.now),[])
    def test_unexpected_schema_fails_explicitly(self):
        with self.assertRaises(SourceError):
            parse_new_pools({'error':'invalid'}, observed_at=self.now)
    def test_future_pool_held(self):
        self.payload['data'][0]['attributes']['pool_created_at'] = (self.now+timedelta(minutes=3)).isoformat()
        c = parse_new_pools(self.payload, observed_at=self.now)[0]
        self.assertEqual(discovery_prefilter(c,self.policy)[0],'HOLD_UNKNOWN')
    def test_missing_timestamp_skipped(self):
        del self.payload['data'][0]['attributes']['pool_created_at']
        self.assertEqual(parse_new_pools(self.payload, observed_at=self.now),[])
    def test_momentum_requires_volume_and_price(self):
        row=self.payload['data'][0]['attributes']
        row['pool_created_at']=(self.now-timedelta(hours=8)).isoformat()
        row['reserve_in_usd']='60000'
        row['volume_usd']['h1']='70000'
        row['transactions']['h1']={'buys':90,'sells':40}
        row['price_change_percentage']={'h1':'14'}
        c=parse_new_pools(self.payload,observed_at=self.now)[0]
        self.assertEqual(discovery_prefilter(c,self.policy)[0],'PENDING_HISTORY')
    def test_nan_volume_unknown(self):
        self.payload['data'][0]['attributes']['volume_usd']['m5']='NaN'
        c=parse_new_pools(self.payload,observed_at=self.now)[0]
        self.assertEqual(discovery_prefilter(c,self.policy)[0],'HOLD_UNKNOWN')
