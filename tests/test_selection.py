import unittest
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from radar.cli import _demo_payload, POLICY
from radar.discovery import select_live_candidates
from radar.transport import SourceError

class FakeTransport:
    def __init__(self, pages):
        self.pages = pages
        self.urls = []
    def request(self, url):
        self.urls.append(url)
        page = int(url.split("page=")[-1])
        response = self.pages.get(page)
        if isinstance(response, Exception):
            raise response
        return deepcopy(response)

class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,10,23,12,0,tzinfo=timezone.utc)
        self.policy = json.loads(Path(POLICY).read_text())
        self.good = _demo_payload(self.now)
    def test_filter_before_limit_and_fetch_next_page(self):
        early = deepcopy(self.good)
        early["data"][0]["attributes"]["pool_created_at"] = (self.now-timedelta(minutes=2)).isoformat()
        t = FakeTransport({1:early, 2:self.good})
        selected, report = select_live_candidates(t,self.policy,observed_at=self.now,limit=1)
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0][1],"PENDING_HISTORY")
        self.assertEqual(report["pages_ok"],2)
        self.assertEqual(len(t.urls),2)
    def test_avoid_extra_page_if_enough_candidates(self):
        t = FakeTransport({1:self.good})
        selected, report = select_live_candidates(t,self.policy,observed_at=self.now,limit=1)
        self.assertEqual(len(selected),1)
        self.assertEqual(report["pages_ok"],1)
        self.assertEqual(len(t.urls),1)
    def test_empty_selection_is_honest(self):
        low = deepcopy(self.good)
        low["data"][0]["attributes"]["reserve_in_usd"]="0"
        t=FakeTransport({1:low,2:low})
        selected, report = select_live_candidates(t,self.policy,observed_at=self.now,limit=2)
        self.assertEqual(selected,[])
        self.assertEqual(report["discovery_ineligible"],1)
        self.assertEqual(report["unique_tokens_seen"],1)
    def test_second_page_failure_retains_partial_data_and_reports_error(self):
        low=deepcopy(self.good)
        low["data"][0]["attributes"]["reserve_in_usd"]="0"
        t=FakeTransport({1:low,2:SourceError("rate limit")})
        selected, report=select_live_candidates(t,self.policy,observed_at=self.now,limit=2)
        self.assertEqual(selected,[])
        self.assertEqual(report["partial_error"],"rate limit")
        self.assertEqual(report["pages_ok"],1)
    def test_first_page_failure_raises(self):
        with self.assertRaises(SourceError):
            select_live_candidates(FakeTransport({1:SourceError("unavailable")}),self.policy,observed_at=self.now,limit=1)
    def test_budget_is_bounded(self):
        self.policy["budget"]["geckoterminal_requests_per_run"] = 20
        with self.assertRaises(ValueError):
            select_live_candidates(FakeTransport({}),self.policy,observed_at=self.now,limit=1)
    def test_zero_limit_makes_no_api_call(self):
        t=FakeTransport({})
        result, report = select_live_candidates(t,self.policy,observed_at=self.now,limit=0)
        self.assertEqual(result,[])
        self.assertEqual(t.urls,[])
