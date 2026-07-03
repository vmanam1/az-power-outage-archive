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
            "metadata": {
                "provider": "EXAMPLE",
                "source": "Test",
                "scraped_at": "2026-07-02 21:00:00 MST",
            },
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

    def test_rejects_wrong_provider_metadata(self):
        self.snapshot["metadata"]["provider"] = "SOMEONE_ELSE"
        with self.assertRaisesRegex(ValueError, "provider does not match"):
            self.provider.validate_snapshot(self.snapshot)

    def test_rejects_incomplete_coordinates(self):
        self.snapshot["outages"][0]["longitude"] = None
        with self.assertRaisesRegex(ValueError, "incomplete coordinates"):
            self.provider.validate_snapshot(self.snapshot)

    def test_rejects_boolean_customer_count(self):
        self.snapshot["outages"][0]["customers"] = True
        with self.assertRaisesRegex(ValueError, "invalid customers"):
            self.provider.validate_snapshot(self.snapshot)

    def test_customer_parser_does_not_coerce_malformed_values(self):
        with self.assertRaisesRegex(ValueError, "valid customer count"):
            self.provider.parse_customer_count("unknown", "customers")


if __name__ == "__main__":
    unittest.main()
