
import unittest
import json
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone, timedelta
from radar.cli import POLICY, _demo_payload
from radar.discovery import select_hybrid_candidates
from radar.transport import SourceError

class HybridTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
    def request(self, url):
        self.calls.append(url)
        key = "trending" if "trending_pools" in url else ("new2" if "page=2" in url else "new1")
        result = self.responses.get(key, {"data": []})
        if isinstance(result, Exception):
            raise result
        return deepcopy(result)

class HybridTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,10,23,12,tzinfo=timezone.utc)
        self.policy = json.loads(Path(POLICY).read_text())
        self.early = _demo_payload(self.now)
        self.momentum = deepcopy(self.early)
        row = self.momentum["data"][0]
        row["relationships"]["base_token"]["data"]["id"] = "solana_" + "So11111111111111111111111111111111111111112"
        a = row["attributes"]
        a["pool_created_at"] = (self.now - timedelta(hours=12)).isoformat()
        a["address"] = "trending-pool"
        a["reserve_in_usd"] = "85000"
        a["volume_usd"]["h1"] = "65000"
        a["transactions"]["h1"] = {"buys": 120, "sells": 50}
        a["price_change_percentage"]["h1"] = "15"
    def test_dual_sources_with_shared_budget(self):
        t = HybridTransport({"new1": self.early, "trending": self.momentum})
        chosen, rep = select_hybrid_candidates(t, self.policy, observed_at=self.now,limit=3)
        self.assertEqual(len(chosen),2)
        self.assertEqual(rep["pages_requested"],2)
        self.assertEqual(set(rep["sources_checked"]),{"new_pools","trending_pools_1h"})
        self.assertTrue(all(s == "PENDING_HISTORY" for _,s,_ in chosen))
    def test_first_failure_reasons_are_counted(self):
        bad = deepcopy(self.early)
        bad["data"][0]["attributes"]["pool_created_at"] = (self.now-timedelta(minutes=2)).isoformat()
        bad["data"][0]["attributes"]["reserve_in_usd"] = "100"
        t = HybridTransport({"new1":bad,"trending":{"data":[]}})
        chosen, rep = select_hybrid_candidates(t,self.policy,observed_at=self.now,limit=2)
        self.assertEqual(chosen,[])
        self.assertEqual(rep["first_failure_reasons"], {"EARLY: pool age outside configured range":1})
        self.assertEqual(rep["discovery_ineligible"],1)
    def test_partial_failure_does_not_fake_success(self):
        t = HybridTransport({"new1":self.early,"trending":SourceError("offline")})
        chosen, rep = select_hybrid_candidates(t,self.policy,observed_at=self.now,limit=2)
        self.assertEqual(len(chosen),1)
        self.assertIn("trending_pools_1h", rep["partial_error"])
        self.assertNotIn("trending_pools_1h", rep["sources_checked"])
    def test_total_failure_is_error(self):
        t = HybridTransport({"new1":SourceError("offline"),"trending":SourceError("offline")})
        with self.assertRaises(SourceError):
            select_hybrid_candidates(t,self.policy,observed_at=self.now,limit=2)
    def test_duplicate_mints_not_double_counted(self):
        t = HybridTransport({"new1":self.early,"trending":self.early})
        chosen, rep = select_hybrid_candidates(t,self.policy,observed_at=self.now,limit=2)
        self.assertEqual(len(chosen),1)
        self.assertEqual(rep["unique_tokens_seen"],1)
        self.assertEqual(rep["raw_pool_rows"],2)
    def test_limit_zero_skips_network(self):
        t = HybridTransport({})
        chosen, rep = select_hybrid_candidates(t,self.policy,observed_at=self.now,limit=0)
        self.assertEqual(chosen,[])
        self.assertEqual(t.calls,[])
    def test_one_request_budget_new_only(self):
        self.policy["budget"]["geckoterminal_requests_per_run"]=1
        t = HybridTransport({"new1":self.early})
        chosen, rep = select_hybrid_candidates(t,self.policy,observed_at=self.now,limit=2)
        self.assertEqual(len(t.calls),1)
        self.assertEqual(rep["sources_checked"],["new_pools"])
    def test_second_reason_liquidity_when_age_eligible(self):
        bad = deepcopy(self.early)
        bad["data"][0]["attributes"]["reserve_in_usd"] = "100"
        t = HybridTransport({"new1":bad,"trending":{"data":[]}})
        _, rep = select_hybrid_candidates(t,self.policy,observed_at=self.now,limit=2)
        self.assertEqual(rep["first_failure_reasons"],{"EARLY: liquidity below discovery floor":1})
