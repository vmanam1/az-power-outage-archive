import unittest
from datetime import datetime
from unittest.mock import patch

from selenium.common.exceptions import WebDriverException

from providers.mohave import MohaveProvider
from providers.navopache import NavopacheProvider
from providers.trico import TricoProvider
from scripts.utils import ARIZONA_TZ


SAMPLE_RECORDS = [{
    "x": -12374629.961348616,
    "y": 3819166.5106796823,
    "text": """×
Outage Details
Planned
Cause: 19 OTHER SCHEDULED (SEE REMARKS)
Outage Reported At: 06/25 08:22 AM
Number Out: 1
Estimated Time Of Restoration: 06/25 11:30 AM
""",
}]


class NISCProviderTests(unittest.TestCase):
    @patch.object(TricoProvider, "scrape_records", return_value=SAMPLE_RECORDS)
    def test_formats_public_outage_card(self, scrape_records):
        result = TricoProvider().fetch_data()

        scrape_records.assert_called_once_with()
        self.assertEqual(result["metadata"]["provider"], "TRICO")
        self.assertEqual(result["summary"]["outage_count"], 1)
        self.assertEqual(result["summary"]["customers_affected"], 1)
        outage = result["outages"][0]
        self.assertAlmostEqual(outage["latitude"], 32.4245, places=3)
        self.assertAlmostEqual(outage["longitude"], -111.1632, places=3)
        self.assertEqual(outage["comments"], "Planned")
        self.assertEqual(outage["cause"], "19 OTHER SCHEDULED (SEE REMARKS)")
        self.assertEqual(outage["start_time"][:10], f"{datetime.now(ARIZONA_TZ).year}-06-25")

    def test_empty_map_has_zero_summary(self):
        result = MohaveProvider().parse_records([])
        self.assertEqual(result["summary"]["outage_count"], 0)
        self.assertEqual(result["summary"]["customers_affected"], 0)

    def test_outage_card_without_customer_count_is_rejected(self):
        records = [{
            "x": SAMPLE_RECORDS[0]["x"],
            "y": SAMPLE_RECORDS[0]["y"],
            "text": "Outage Details\nInvestigating\nCause: Unknown",
        }]
        with self.assertRaisesRegex(ValueError, "missing a customer count"):
            TricoProvider().parse_records(records)

    @patch("providers.nisc.time.sleep")
    @patch.object(TricoProvider, "scrape_records")
    def test_retries_browser_failure(self, scrape_records, sleep):
        scrape_records.side_effect = [
            WebDriverException("temporary"),
            SAMPLE_RECORDS,
        ]

        result = TricoProvider().fetch_data()

        self.assertEqual(result["summary"]["outage_count"], 1)
        self.assertEqual(scrape_records.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_utility_urls_are_distinct(self):
        self.assertIn("trico.org", TricoProvider.MAP_URL)
        self.assertIn("mohaveelectric.com", MohaveProvider.MAP_URL)
        self.assertIn("navopache.org", NavopacheProvider.MAP_URL)


if __name__ == "__main__":
    unittest.main()
