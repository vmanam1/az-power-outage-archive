import json
import os
import tempfile
import unittest

from dashboard.archive_reader import scan_archive
from scripts.utils import filter_snapshot_to_arizona, is_in_arizona


def _snapshot(outages):
    return {
        "metadata": {
            "provider": "NAVOPACHE",
            "scraped_at": "2026-07-29 15:00:00 MST",
            "source": "Mock",
            "scraper_version": "1.0.0",
        },
        "summary": {
            "outage_count": len(outages),
            "customers_affected": sum(o.get("customers", 0) for o in outages),
        },
        "outages": outages,
    }


PHOENIX = {"latitude": 33.4484, "longitude": -112.0740, "customers": 10}
SHOW_LOW = {"latitude": 34.2542, "longitude": -110.0298, "customers": 5}
RESERVE_NM = {"latitude": 33.7180, "longitude": -108.7552, "customers": 156}
NO_COORDS = {"latitude": None, "longitude": None, "customers": 3, "incident_id": "x1"}


class IsInArizonaTests(unittest.TestCase):
    def test_arizona_points_are_inside(self):
        self.assertTrue(is_in_arizona(PHOENIX["latitude"], PHOENIX["longitude"]))
        self.assertTrue(is_in_arizona(SHOW_LOW["latitude"], SHOW_LOW["longitude"]))

    def test_neighboring_states_are_outside(self):
        # Reserve, NM (Navopache's New Mexico territory)
        self.assertFalse(is_in_arizona(33.7180, -108.7552))
        # Agua Prieta, Sonora (Mexico)
        self.assertFalse(is_in_arizona(31.20, -109.55))
        # Las Vegas, NV
        self.assertFalse(is_in_arizona(36.17, -115.14))

    def test_non_numeric_values_are_outside(self):
        self.assertFalse(is_in_arizona(None, -112.0))
        self.assertFalse(is_in_arizona("33.4", "-112.0"))
        self.assertFalse(is_in_arizona(True, -112.0))


class FilterSnapshotTests(unittest.TestCase):
    def test_out_of_state_records_are_dropped_and_summary_recomputed(self):
        data = _snapshot([PHOENIX, RESERVE_NM, SHOW_LOW])
        filtered, dropped, dropped_customers = filter_snapshot_to_arizona(data)

        self.assertEqual(dropped, 1)
        self.assertEqual(dropped_customers, 156)
        self.assertEqual(filtered["summary"]["outage_count"], 2)
        self.assertEqual(filtered["summary"]["customers_affected"], 15)
        self.assertNotIn(RESERVE_NM, filtered["outages"])

    def test_records_without_coordinates_are_kept(self):
        data = _snapshot([NO_COORDS, RESERVE_NM])
        filtered, dropped, _ = filter_snapshot_to_arizona(data)
        self.assertEqual(dropped, 1)
        self.assertEqual(filtered["outages"], [NO_COORDS])

    def test_clean_snapshot_is_returned_untouched(self):
        data = _snapshot([PHOENIX, SHOW_LOW])
        filtered, dropped, dropped_customers = filter_snapshot_to_arizona(data)
        self.assertIs(filtered, data)
        self.assertEqual((dropped, dropped_customers), (0, 0))


class ReaderHidesOutOfStateTests(unittest.TestCase):
    def test_archived_out_of_state_records_are_hidden_and_counted(self):
        # Simulates snapshots archived before the collector-side filter.
        with tempfile.TemporaryDirectory() as tmp:
            prov_dir = os.path.join(tmp, "navopache")
            os.makedirs(prov_dir)
            with open(
                os.path.join(prov_dir, "2026-07-29_15-00.json"), "w",
                encoding="utf-8",
            ) as f:
                json.dump(_snapshot([PHOENIX, RESERVE_NM, SHOW_LOW]), f)

            snapshots, stats = scan_archive(tmp)

            self.assertEqual(len(snapshots), 1)
            outages = snapshots[0]["outages"]
            self.assertEqual(len(outages), 2)
            self.assertTrue(all(o["longitude"] <= -109.045 for o in outages))
            self.assertEqual(stats.out_of_state, 1)
            # Customer total excludes the hidden New Mexico record.
            self.assertEqual(snapshots[0]["customers_affected"], 15)


if __name__ == "__main__":
    unittest.main()
