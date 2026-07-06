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
                {"division": "USE", "customersOut": "10"},
                {"division": "UEE", "customersOut": "20"},
                {"division": "TEP", "customersOut": "30"},
            ],
        }
        post.return_value = response

        result = UESProvider().fetch_data()

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


if __name__ == "__main__":
    unittest.main()
