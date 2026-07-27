import unittest

from dashboard.geo import DERIVED_PREFIX, derived_city, nearest_place
from dashboard.normalizer import normalize_outage


class NearestPlaceTests(unittest.TestCase):
    def test_phoenix_centroid_resolves_to_phoenix(self):
        self.assertEqual(nearest_place(33.57215, -112.09013), "Phoenix")

    def test_missing_coordinates_return_none(self):
        self.assertIsNone(nearest_place(None, None))

    def test_far_away_point_returns_none(self):
        # Hundreds of km outside Arizona: nothing within MAX_DISTANCE_KM.
        self.assertIsNone(nearest_place(45.0, -100.0))

    def test_derived_city_is_marked(self):
        label = derived_city(33.57215, -112.09013)
        self.assertTrue(label.startswith(DERIVED_PREFIX))


class NormalizerCityDerivationTests(unittest.TestCase):
    def test_published_city_is_kept_verbatim(self):
        out = normalize_outage(
            {"latitude": 33.57215, "longitude": -112.09013, "customers": 1, "city": "Surprise"},
            "aps",
        )
        self.assertEqual(out["city"], "Surprise")

    def test_missing_city_is_derived_from_coordinates(self):
        out = normalize_outage(
            {"latitude": 33.57215, "longitude": -112.09013, "customers": 1},
            "srp",
        )
        self.assertEqual(out["city"], f"{DERIVED_PREFIX}Phoenix")

    def test_no_coordinates_means_no_derived_city(self):
        out = normalize_outage({"customers": 1}, "srp")
        self.assertIsNone(out["city"])


if __name__ == "__main__":
    unittest.main()
