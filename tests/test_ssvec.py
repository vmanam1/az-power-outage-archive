import unittest
from unittest.mock import Mock, patch

from providers.ssvec import SSVECProvider
from scripts.config import REQUEST_TIMEOUT, SSVEC_PARAMS, SSVEC_URL


SAMPLE_PAYLOAD = {
    "features": [
        {
            "attributes": {
                "INCIDENT_ID": 17681,
                "REGION": "Sierra Vista",
                "STATUS": "Power Out",
                "TIME_OUTAGE": 1783033203000,
                "TIME_RESTORED_EST": 1783044003000,
                "TIME_RESTORED": None,
                "CAUSE": "Investigating",
                "CUSTOMER_COUNT": 94,
            },
            "geometry": {
                "x": -110.24842509502584,
                "y": 31.54727947857296,
            },
        },
        {
            "attributes": {
                "INCIDENT_ID": 17591,
                "CUSTOMER_COUNT": 1,
            },
            "geometry": None,
        },
    ]
}


class SSVECProviderTests(unittest.TestCase):
    @patch("providers.ssvec.requests.get")
    def test_fetches_and_formats_outages(self, get):
        response = Mock()
        response.json.return_value = SAMPLE_PAYLOAD
        get.return_value = response

        result = SSVECProvider().fetch_data()

        get.assert_called_once_with(
            SSVEC_URL,
            params=SSVEC_PARAMS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result["metadata"]["provider"], "SSVEC")
        self.assertEqual(result["summary"]["outage_count"], 2)
        self.assertEqual(result["summary"]["customers_affected"], 95)
        self.assertEqual(result["outages"][0]["city"], "Sierra Vista")
        self.assertEqual(result["outages"][0]["start_time"], "2026-07-02 16:00:03 MST")
        self.assertEqual(result["outages"][0]["etr"], "2026-07-02 19:00:03 MST")
        self.assertIsNone(result["outages"][1]["latitude"])

    def test_empty_feed_has_zero_summary(self):
        result = SSVECProvider().parse_data({"features": []})
        self.assertEqual(result["summary"]["outage_count"], 0)
        self.assertEqual(result["summary"]["customers_affected"], 0)

    @patch("providers.ssvec.requests.get")
    def test_arcgis_error_is_reported(self, get):
        response = Mock()
        response.json.return_value = {"error": {"message": "Invalid query"}}
        get.return_value = response

        with self.assertRaisesRegex(RuntimeError, "SSVEC API returned an error"):
            SSVECProvider().fetch_data()


if __name__ == "__main__":
    unittest.main()
