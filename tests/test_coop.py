import unittest
from unittest.mock import patch

from providers.mohave import MohaveProvider
from providers.navopache import NavopacheProvider
from providers.trico import TricoProvider

# Real captured values from mohaveelectric's hosted map. The x/y offsets and
# boundaryExtent must decode to the exact coordinates the utility's own map
# renders (verified against live markers).
CONFIG = {
    "mapSettings": {
        "boundaryExtent": [-12762208.0, 4084789.0, -12586187.0, 4255993.0]
    }
}

SUMMARY = {
    "totalServed": 47046,
    "outages": [
        {
            "id": "349870",
            "nbrOut": 1,
            "timeOff": 1784899201388,
            "planned": False,
            "x": 85852,
            "y": 138987,
        },
        {
            "id": "349902",
            "nbrOut": 92,
            "timeOff": 1785126999953,
            "estimateTime": 1785134400000,
            "cause": "WEATHER                 ",
            "comment": "Crews are responding.",
            "planned": True,
            "x": 3535,
            "y": 95257,
        },
    ],
    "lastUpdate": 1785131228367,
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def fake_fetch(payloads):
    def _request(method, url, **kwargs):
        for name, payload in payloads.items():
            if url.endswith(name):
                return FakeResponse(payload)
        raise AssertionError(f"unexpected url {url}")
    return _request


class CoopOutageMapProviderTests(unittest.TestCase):
    @patch("providers.coop.request_with_retries")
    def test_fetches_and_formats_outages(self, mock_request):
        mock_request.side_effect = fake_fetch(
            {"config.json": CONFIG, "summary.json": SUMMARY}
        )
        data = MohaveProvider().fetch_data()

        self.assertEqual(data["summary"]["outage_count"], 2)
        self.assertEqual(data["summary"]["customers_affected"], 93)
        self.assertEqual(data["summary"]["total_customers"], 47046)

        first, second = data["outages"]
        # Decoded coordinates must match the utility's own map markers.
        self.assertAlmostEqual(first["latitude"], 35.43955, places=4)
        self.assertAlmostEqual(first["longitude"], -113.87364, places=4)
        self.assertEqual(first["customers"], 1)
        self.assertEqual(first["incident_id"], "349870")
        self.assertIsNone(first["cause"])
        self.assertIsNone(first["etr"])
        self.assertTrue(first["start_time"].endswith("MST"))

        self.assertAlmostEqual(second["latitude"], 35.11886, places=4)
        self.assertAlmostEqual(second["longitude"], -114.61311, places=4)
        self.assertEqual(second["cause"], "WEATHER")
        self.assertEqual(second["comments"], "Planned outage. Crews are responding.")
        self.assertTrue(second["etr"].endswith("MST"))

    @patch("providers.coop.request_with_retries")
    def test_empty_feed_has_zero_summary(self, mock_request):
        mock_request.side_effect = fake_fetch(
            {"config.json": CONFIG, "summary.json": {"outages": []}}
        )
        data = TricoProvider().fetch_data()
        self.assertEqual(data["summary"]["outage_count"], 0)
        self.assertEqual(data["summary"]["customers_affected"], 0)

    @patch("providers.coop.request_with_retries")
    def test_missing_extent_is_reported(self, mock_request):
        mock_request.side_effect = fake_fetch(
            {"config.json": {"mapSettings": {}}, "summary.json": SUMMARY}
        )
        with self.assertRaisesRegex(RuntimeError, "boundaryExtent"):
            NavopacheProvider().fetch_data()

    @patch("providers.coop.request_with_retries")
    def test_malformed_customer_count_is_rejected(self, mock_request):
        bad = {"outages": [{"id": "1", "nbrOut": "many", "x": 1, "y": 1}]}
        mock_request.side_effect = fake_fetch(
            {"config.json": CONFIG, "summary.json": bad}
        )
        with self.assertRaises(RuntimeError):
            MohaveProvider().fetch_data()

    @patch("providers.coop.request_with_retries")
    def test_slugs_target_the_right_utilities(self, mock_request):
        seen = []

        def record(method, url, **kwargs):
            seen.append(url)
            if url.endswith("config.json"):
                return FakeResponse(CONFIG)
            return FakeResponse({"outages": []})

        mock_request.side_effect = record
        for provider, slug in (
            (MohaveProvider(), "mohaveelectric"),
            (TricoProvider(), "trico"),
            (NavopacheProvider(), "navopache"),
        ):
            provider.fetch_data()
        self.assertTrue(all("outagemap-data.cloud.coop" in u for u in seen))
        for slug in ("mohaveelectric", "trico", "navopache"):
            self.assertTrue(any(f"/{slug}/" in u for u in seen))


if __name__ == "__main__":
    unittest.main()
