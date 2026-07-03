import unittest
from unittest.mock import Mock, patch

from providers.aps import APSProvider


class APSProviderTests(unittest.TestCase):
    @patch("providers.aps.requests.get")
    def test_malformed_feature_is_not_archived_as_zero(self, get):
        response = Mock()
        response.json.return_value = {
            "features": [{"attributes": {}, "geometry": {"x": -112, "y": 33}}]
        }
        get.return_value = response

        with self.assertRaisesRegex(RuntimeError, "valid customer count"):
            APSProvider().fetch_data()


if __name__ == "__main__":
    unittest.main()
