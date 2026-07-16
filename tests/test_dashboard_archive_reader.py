import unittest
import tempfile
import os
import json
import time
from datetime import datetime
from dashboard.archive_reader import scan_archive
from dashboard.filters import apply_filters
from dashboard.cache import global_cache

class TestDashboardArchiveReader(unittest.TestCase):

    def setUp(self):
        global_cache.clear()

    def test_dynamic_provider_and_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Dynamic discovery structure
            prov_dir = os.path.join(temp_dir, "aps")
            os.makedirs(prov_dir)

            snap_data = {
                "metadata": {
                    "provider": "APS",
                    "scraped_at": "2026-07-15 16:00:00 MST",
                    "source": "Mock"
                },
                "summary": {
                    "outage_count": 1,
                    "customers_affected": 20
                },
                "outages": [
                    {
                        "latitude": 33.4,
                        "longitude": -112.0,
                        "customers": 20,
                        "cause": "Weather",
                        "start_time": "2026-07-15 15:30:00 MST"
                    }
                ]
            }

            file_path = os.path.join(prov_dir, "2026-07-15_16-00.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(snap_data, f)

            snapshots, stats = scan_archive(temp_dir)
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(stats.total_snapshots, 1)
            self.assertEqual(stats.malformed_files, 0)
            self.assertEqual(stats.missing_coords, 0)
            
            snap = snapshots[0]
            self.assertEqual(snap["provider"], "aps")
            self.assertEqual(snap["scraped_at"], "2026-07-15 16:00:00 MST")
            self.assertEqual(len(snap["outages"]), 1)
            self.assertEqual(snap["outages"][0]["customers"], 20)

    def test_invalid_json_and_empty_snapshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prov_dir = os.path.join(temp_dir, "srp")
            os.makedirs(prov_dir)

            # Write invalid JSON file
            with open(os.path.join(prov_dir, "broken.json"), "w") as f:
                f.write("{broken json...")

            # Write empty snapshot
            empty_snap = {
                "metadata": {"provider": "SRP", "scraped_at": "2026-07-15 12:00:00 MST", "source": "Mock"},
                "summary": {"outage_count": 0, "customers_affected": 0},
                "outages": []
            }
            with open(os.path.join(prov_dir, "2026-07-15_12-00.json"), "w") as f:
                json.dump(empty_snap, f)

            snapshots, stats = scan_archive(temp_dir)
            
            # The broken file should be logged and skipped; the empty one should load.
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(stats.total_snapshots, 2)
            self.assertEqual(stats.malformed_files, 1)
            self.assertEqual(len(snapshots[0]["outages"]), 0)

    def test_missing_and_invalid_coordinates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prov_dir = os.path.join(temp_dir, "tep")
            os.makedirs(prov_dir)

            snap_data = {
                "metadata": {"provider": "TEP", "scraped_at": "2026-07-15 10:00:00 MST", "source": "Mock"},
                "summary": {"outage_count": 3, "customers_affected": 15},
                "outages": [
                    # Missing coords
                    {"customers": 5, "cause": "Unknown", "city": "Tucson"},
                    # Invalid bounds
                    {"latitude": 95.0, "longitude": -110.0, "customers": 5},
                    # Valid
                    {"latitude": 32.2, "longitude": -110.9, "customers": 5}
                ]
            }
            with open(os.path.join(prov_dir, "2026-07-15_10-00.json"), "w") as f:
                json.dump(snap_data, f)

            snapshots, stats = scan_archive(temp_dir)
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(stats.missing_coords, 1)
            self.assertEqual(stats.invalid_coords, 1)

            outages = snapshots[0]["outages"]
            self.assertIsNone(outages[0]["latitude"])
            self.assertIsNone(outages[1]["latitude"])
            self.assertEqual(outages[2]["latitude"], 32.2)

    def test_timestamp_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prov_dir = os.path.join(temp_dir, "ues")
            os.makedirs(prov_dir)

            # Metadata is missing scraped_at, fallback to filename time
            snap_data = {
                "metadata": {"provider": "UES", "source": "Mock"},
                "summary": {"outage_count": 0, "customers_affected": 0},
                "outages": []
            }
            file_path = os.path.join(prov_dir, "2026-07-14_23-45.json")
            with open(file_path, "w") as f:
                json.dump(snap_data, f)

            snapshots, _ = scan_archive(temp_dir)
            self.assertEqual(snapshots[0]["scraped_at"], "2026-07-14 23:45:00 MST")

    def test_cache_invalidation_after_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prov_dir = os.path.join(temp_dir, "ssvec")
            os.makedirs(prov_dir)

            snap_data = {
                "metadata": {"provider": "SSVEC", "scraped_at": "2026-07-15 08:00:00 MST", "source": "Mock"},
                "summary": {"outage_count": 1, "customers_affected": 10},
                "outages": [{"latitude": 31.5, "longitude": -109.8, "customers": 10}]
            }
            file_path = os.path.join(prov_dir, "2026-07-15_08-00.json")
            with open(file_path, "w") as f:
                json.dump(snap_data, f)

            # First scan parses and caches
            scan_archive(temp_dir)
            
            # Edit file content, update mtime
            snap_data["summary"]["customers_affected"] = 25
            snap_data["outages"][0]["customers"] = 25
            
            # Tiny sleep to ensure mtime differences on fast filesystems
            time.sleep(0.1)
            with open(file_path, "w") as f:
                json.dump(snap_data, f)
            
            # Second scan detects file modification
            snapshots, _ = scan_archive(temp_dir)
            self.assertEqual(snapshots[0]["outages"][0]["customers"], 25)

    def test_filter_modes(self):
        # Set up a list of synthetic snapshots
        snapshots = [
            {
                "file_path": "data/aps/file1.json",
                "provider": "aps",
                "scraped_at": "2026-07-15 10:00:00 MST",
                "outages": [{"latitude": 33.0, "longitude": -112.0, "customers": 10, "provider": "aps", "incident_id": "out1", "start_time": "2026-07-15 09:00:00 MST"}],
                "customers_affected": 10
            },
            {
                "file_path": "data/aps/file2.json",
                "provider": "aps",
                "scraped_at": "2026-07-15 12:00:00 MST",
                "outages": [
                    {"latitude": 33.0, "longitude": -112.0, "customers": 10, "provider": "aps", "incident_id": "out1", "start_time": "2026-07-15 09:00:00 MST"},
                    {"latitude": 34.0, "longitude": -111.0, "customers": 5, "provider": "aps", "incident_id": "out2", "start_time": "2026-07-15 11:00:00 MST"}
                ],
                "customers_affected": 15
            },
            {
                "file_path": "data/srp/file1.json",
                "provider": "srp",
                "scraped_at": "2026-07-15 11:00:00 MST",
                "outages": [{"latitude": 33.5, "longitude": -111.8, "customers": 40, "provider": "srp", "boundary": "Cross1", "start_time": "2026-07-15 10:00:00 MST"}],
                "customers_affected": 40
            }
        ]

        # 1. Latest mode
        outs, summary = apply_filters(snapshots, {"display_mode": "latest"})
        # Should include latest aps (file2) and latest srp (file1) -> 2+1 = 3 outages
        self.assertEqual(len(outs), 3)
        self.assertEqual(summary["total_customers"], 55)

        # 2. Snapshot-at-time mode (target: 11:30 MST)
        # aps should match file1 (10:00 <= 11:30), srp should match file1 (11:00 <= 11:30)
        outs, summary = apply_filters(snapshots, {
            "display_mode": "snapshot_at_time",
            "snapshot_time": "2026-07-15 11:30:00 MST"
        })
        self.assertEqual(len(outs), 2) # out1 (aps) and srp out
        self.assertEqual(summary["total_customers"], 50)

        # 3. Historical mode in date range
        # Should pull all outages from all 3 files (1+2+1 = 4 total)
        outs, summary = apply_filters(snapshots, {
            "display_mode": "historical",
            "start_date": "2026-07-15 09:00:00",
            "end_date": "2026-07-15 13:00:00"
        })
        self.assertEqual(len(outs), 4)

        # 4. Unique Outages deduplication mode
        # Should deduplicate 'out1' from aps, keeping the latest one. Total unique: 3
        outs, summary = apply_filters(snapshots, {
            "display_mode": "unique_outages",
            "start_date": "2026-07-15 09:00:00",
            "end_date": "2026-07-15 13:00:00"
        })
        self.assertEqual(len(outs), 3)
        
        # Verify provider/date/customer range filters combination
        outs, summary = apply_filters(snapshots, {
            "display_mode": "historical",
            "providers": ["aps"],
            "min_customers": 6,
            "max_customers": 20
        })
        # From aps snapshots: outages have 10, 10, 5 customers. Filter min=6, max=20 -> should match the two '10' customer records
        self.assertEqual(len(outs), 2)
        self.assertTrue(all(o["customers"] == 10 for o in outs))

if __name__ == "__main__":
    unittest.main()
