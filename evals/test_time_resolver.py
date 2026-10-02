import unittest
from datetime import datetime, timezone
import zoneinfo
from backend.time_resolver import resolve_time

class TestTimeResolver(unittest.TestCase):
    def setUp(self):
        # Anchor ref_dt: 2026-10-02 10:00:00 UTC (Friday)
        # In Asia/Kolkata (UTC+5:30): 2026-10-02 15:30:00 (Friday)
        # In Pacific/Auckland (UTC+13:00 / Daylight Saving in Oct): 2026-10-03 23:00:00 (Saturday)
        self.ref_dt = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)

    def test_noon_today_in_auckland(self):
        # Anchor at 22:00 UTC on 2026-10-01, which is 11:00 AM on 2026-10-02 in Auckland (before noon)
        morning_ref = datetime(2026, 10, 1, 22, 0, 0, tzinfo=timezone.utc)
        res = resolve_time("noon today in Auckland", tz_name="Pacific/Auckland", ref_dt=morning_ref)
        self.assertEqual(res.kind, "hour")
        self.assertEqual(res.target_hour, "12:00")
        self.assertEqual(res.target_date, "2026-10-02")
        self.assertTrue(res.iso.endswith("T12:00"))

        # When local time is after noon in Auckland (e.g. 23:00), noon today is recognized as past
        past_ref = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
        res_past = resolve_time("noon today in Auckland", tz_name="Pacific/Auckland", ref_dt=past_ref)
        self.assertEqual(res_past.kind, "past")
        self.assertEqual(res_past.target_hour, "12:00")
        self.assertIn("already passed", res_past.assumed)

    def test_next_friday(self):
        # 2026-10-02 is a Friday, so next Friday should be 2026-10-09
        res = resolve_time("next Friday", tz_name="Asia/Kolkata", ref_dt=self.ref_dt)
        self.assertEqual(res.kind, "day")
        self.assertEqual(res.target_date, "2026-10-09")
        self.assertEqual(res.target_hour, "12:00")
        self.assertIn("Assuming", res.assumed)

    def test_1pm(self):
        res = resolve_time("1pm", tz_name="Asia/Kolkata", ref_dt=self.ref_dt)
        self.assertEqual(res.kind, "hour")
        self.assertEqual(res.target_hour, "13:00")
        self.assertTrue(res.iso.endswith("T13:00"))

    def test_three_months(self):
        res = resolve_time("three months from now", tz_name="Asia/Kolkata", ref_dt=self.ref_dt)
        self.assertEqual(res.kind, "beyond_horizon")
        self.assertIsNone(res.iso)

    def test_this_evening(self):
        res = resolve_time("this evening", tz_name="Asia/Kolkata", ref_dt=self.ref_dt)
        self.assertEqual(res.kind, "hour")
        self.assertEqual(res.target_hour, "18:00")
        self.assertEqual(res.target_date, "2026-10-02")

    def test_this_weekend(self):
        res = resolve_time("this weekend", tz_name="Asia/Kolkata", ref_dt=self.ref_dt)
        self.assertEqual(res.kind, "day")
        # 2026-10-02 is Friday, so this weekend is Saturday 2026-10-03
        self.assertEqual(res.target_date, "2026-10-03")
        self.assertEqual(res.target_hour, "12:00")

    def test_past_time_refusal(self):
        res = resolve_time("yesterday afternoon", tz_name="Asia/Kolkata", ref_dt=self.ref_dt)
        self.assertEqual(res.kind, "past")
        self.assertIn("already passed", res.assumed)

    def test_followup_carry_over(self):
        prior = {
            "kind": "hour",
            "iso": "2026-10-03T18:00",
            "assumed": "Assuming tomorrow 18:00",
            "target_hour": "18:00",
            "target_date": "2026-10-03"
        }
        res = resolve_time("what about Indore?", is_followup=True, prior_target=prior, tz_name="Asia/Kolkata", ref_dt=self.ref_dt)
        self.assertEqual(res.target_hour, "18:00")
        self.assertEqual(res.target_date, "2026-10-03")

if __name__ == "__main__":
    unittest.main()
