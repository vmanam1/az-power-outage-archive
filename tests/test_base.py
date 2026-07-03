import unittest

from providers.base import BaseProvider


class ExampleProvider(BaseProvider):
    def __init__(self):
        super().__init__("example")

    def fetch_data(self):
        return None


class SnapshotValidationTests(unittest.TestCase):
    def setUp(self):
        self.provider = ExampleProvider()
        self.snapshot = {
            "metadata": {"provider": "EXAMPLE", "source": "Test"},
            "summary": {"outage_count": 1, "customers_affected": 2},
            "outages": [{
                "latitude": 33.0,
                "longitude": -112.0,
                "customers": 2,
            }],
        }

    def test_accepts_valid_snapshot(self):
        self.assertIs(
            self.provider.validate_snapshot(self.snapshot),
            self.snapshot,
        )

    def test_rejects_mismatched_summary(self):
        self.snapshot["summary"]["customers_affected"] = 3
        with self.assertRaisesRegex(ValueError, "does not match outages"):
            self.provider.validate_snapshot(self.snapshot)

    def test_rejects_invalid_coordinates(self):
        self.snapshot["outages"][0]["latitude"] = 120
        with self.assertRaisesRegex(ValueError, "invalid latitude"):
            self.provider.validate_snapshot(self.snapshot)


if __name__ == "__main__":
    unittest.main()
