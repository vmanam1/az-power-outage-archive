import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from providers.tep import TEPProvider
from scripts.utils import ARIZONA_TZ


SAMPLE_PAYLOAD = {
    "mapLastRefreshed": "Jul 2, 2:30 PM",
    "outages": [{
        "coordLat": "32.218236",
        "coordLng": "-110.970550",
        "bounds": {"coordLatCenter": "32.218235"},
        "formattedStartTime": "Jul 2, 12:18 AM",
        "customersOut": "1,234",
        "customersRestored": "40",
        "status": "Crews are working to restore power",
        "formattedEstimatedRestoration": "Jul 2, 4:18 AM",
        "updatedCause": "Equipment failure",
        "event": "Unplanned",
        "division": "TEP",
        "lastUpdate": "07/02/2026 04:43:35 AM",
    }],
}


class TEPProviderTests(unittest.TestCase):
    @patch("providers.tep.requests.post")
    def test_fetches_and_formats_feed(self, post):
        response = Mock()
        response.json.return_value = SAMPLE_PAYLOAD
        post.return_value = response

        result = TEPProvider().fetch_data()

        post.assert_called_once_with(
            TEPProvider.API_URL,
            headers=TEPProvider.HEADERS,
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result["summary"]["outage_count"], 1)
        self.assertEqual(result["summary"]["customers_affected"], 1234)
        self.assertEqual(result["outages"][0]["latitude"], 32.218236)
        self.assertEqual(result["outages"][0]["cause"], "Equipment failure")
        self.assertEqual(result["outages"][0]["customers_restored"], 40)
        self.assertEqual(result["outages"][0]["last_update"], "2026-07-02 04:43 MST")

    def test_formats_yearless_time_using_reference_year(self):
        reference = datetime(2026, 7, 2, 12, tzinfo=ARIZONA_TZ)
        value = TEPProvider.format_time("Jul 2, 4:18 AM", reference=reference)
        self.assertEqual(value, "2026-07-02 04:18 MST")

    def test_empty_feed_has_zero_summary(self):
        result = TEPProvider().parse_data({"outages": []})
        self.assertEqual(result["summary"]["outage_count"], 0)
        self.assertEqual(result["summary"]["customers_affected"], 0)


if __name__ == "__main__":
    unittest.main()
