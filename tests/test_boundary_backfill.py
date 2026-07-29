import unittest

import dashboard.geo as geo
from dashboard.geo import derived_boundary
from dashboard.normalizer import normalize_outage


def _square_region(name, lat, lng, half_size_m=5000):
    """A square Web Mercator region centered on a WGS84 coordinate."""
    cx, cy = geo._to_web_mercator(lat, lng)
    ring = [
        [cx - half_size_m, cy - half_size_m],
        [cx + half_size_m, cy - half_size_m],
        [cx + half_size_m, cy + half_size_m],
        [cx - half_size_m, cy + half_size_m],
    ]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return {
        "name": name,
        "rings": [ring],
        "bbox": (min(xs), min(ys), max(xs), max(ys)),
    }


SHOW_LOW = (34.2542, -110.0298)


class DerivedBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._original = geo._regions
        geo._regions = {
            "navopache": [_square_region("6 - LINDEN", *SHOW_LOW)],
        }
        self.addCleanup(setattr, geo, "_regions", self._original)

    def test_point_inside_region_gets_marked_name(self):
        self.assertEqual(
            derived_boundary("navopache", *SHOW_LOW), "≈ 6 - LINDEN"
        )

    def test_point_outside_all_regions_gets_none(self):
        self.assertIsNone(derived_boundary("navopache", 33.45, -112.07))

    def test_unknown_provider_gets_none(self):
        self.assertIsNone(derived_boundary("aps", *SHOW_LOW))


class NormalizerBoundaryFallbackTests(unittest.TestCase):
    def setUp(self):
        self._original = geo._regions
        geo._regions = {
            "navopache": [_square_region("6 - LINDEN", *SHOW_LOW)],
        }
        self.addCleanup(setattr, geo, "_regions", self._original)

    def test_published_boundary_is_kept_verbatim(self):
        out = normalize_outage(
            {"latitude": SHOW_LOW[0], "longitude": SHOW_LOW[1],
             "customers": 1, "boundary": "3 - RESERVATION"},
            "navopache",
        )
        self.assertEqual(out["boundary"], "3 - RESERVATION")

    def test_missing_boundary_backfilled_from_region_polygons(self):
        out = normalize_outage(
            {"latitude": SHOW_LOW[0], "longitude": SHOW_LOW[1], "customers": 1},
            "navopache",
        )
        self.assertEqual(out["boundary"], "≈ 6 - LINDEN")

    def test_dict_boundary_is_discarded_and_backfilled(self):
        # TEP publishes coordinate dictionaries instead of names.
        out = normalize_outage(
            {"latitude": 32.2226, "longitude": -110.9747, "customers": 1,
             "boundary": {"coordLatSW": "32.2", "coordLngSW": "-110.9"}},
            "tep",
        )
        self.assertIsInstance(out["boundary"], str)
        self.assertTrue(out["boundary"].startswith("≈ "))
        self.assertTrue(out["boundary"].endswith(" area"))

    def test_no_coordinates_leaves_boundary_none(self):
        out = normalize_outage(
            {"latitude": None, "longitude": None, "customers": 1,
             "incident_id": "x"},
            "tep",
        )
        self.assertIsNone(out["boundary"])


if __name__ == "__main__":
    unittest.main()
