import unittest
from unittest.mock import Mock, patch

from providers.ues import UESProvider


class UESProviderTests(unittest.TestCase):
    @patch("providers.tep.requests.post")
    def test_collects_both_unisource_divisions_and_excludes_tep(self, post):
        response = Mock()
        response.json.return_value = {
            "mapLastRefreshed": "Jul 2, 2:42 PM",
            "outages": [
                {
                    "division": "USE",
                    "customersOut": "10",
                    "coordLat": "32.218",
                    "coordLng": "-110.970",
                },
                {
                    "division": "UEE",
                    "customersOut": "20",
                    "coordLat": "32.219",
                    "coordLng": "-110.971",
                },
                {
                    "division": "TEP",
                    "customersOut": "30",
                    "coordLat": "32.220",
                    "coordLng": "-110.972",
                },
            ],
        }
        post.return_value = response

        provider = UESProvider()
        result = provider.fetch_data()
        provider.validate_snapshot(result)

        self.assertEqual(result["metadata"]["provider"], "UES")
        self.assertEqual(result["summary"]["outage_count"], 2)
        self.assertEqual(result["summary"]["customers_affected"], 30)
        self.assertEqual(
            [outage["division"] for outage in result["outages"]],
            ["USE", "UEE"],
        )
        post.assert_called_once_with(
            UESProvider.API_URL,
            headers=UESProvider.HEADERS,
            timeout=30,
        )

    def test_malformed_customer_count_is_rejected(self):
        payload = {
            "outages": [{
                "division": "USE",
                "customersOut": "unknown",
            }]
        }
        with self.assertRaisesRegex(ValueError, "valid customer count"):
            UESProvider().parse_data(payload)


if __name__ == "__main__":
    unittest.main()
