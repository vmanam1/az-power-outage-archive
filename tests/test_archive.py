import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.archive as archive


def _snapshot(scraped_at, customers=10):
    return {
        "metadata": {
            "provider": "APS",
            "scraped_at": scraped_at,
            "source": "Mock",
            "scraper_version": "1.0.0",
        },
        "summary": {"outage_count": 1, "customers_affected": customers},
        "outages": [
            {"latitude": 33.4, "longitude": -112.0, "customers": customers}
        ],
    }


class SaveSnapshotTests(unittest.TestCase):
    def test_identical_outages_not_resaved_despite_new_timestamp(self):
        # Regression: the dedup hash previously included metadata.scraped_at,
        # which changes every run, so identical outages were always re-saved.
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(archive, "DATA_FOLDER", Path(tmp)):
                saved1, path1 = archive.save_snapshot(
                    "aps", _snapshot("2026-07-18 10:00:00 MST")
                )
                self.assertTrue(saved1)

                saved2, path2 = archive.save_snapshot(
                    "aps", _snapshot("2026-07-18 11:00:00 MST")
                )
                self.assertFalse(saved2)
                self.assertEqual(Path(path1), Path(path2))

                files = list((Path(tmp) / "aps").glob("*.json"))
                self.assertEqual(len(files), 1)

    def test_changed_outages_creates_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(archive, "DATA_FOLDER", Path(tmp)):
                archive.save_snapshot(
                    "aps", _snapshot("2026-07-18 10:00:00 MST", customers=10)
                )
                saved, _ = archive.save_snapshot(
                    "aps", _snapshot("2026-07-18 11:00:00 MST", customers=25)
                )
                self.assertTrue(saved)

                files = list((Path(tmp) / "aps").glob("*.json"))
                self.assertEqual(len(files), 2)

    def test_filename_derived_from_metadata_timestamp(self):
        # The filename must match metadata.scraped_at so the two never drift.
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(archive, "DATA_FOLDER", Path(tmp)):
                _, path = archive.save_snapshot(
                    "aps", _snapshot("2026-07-18 09:05:00 MST")
                )
                self.assertEqual(Path(path).name, "2026-07-18_09-05.json")

    def test_empty_outages_are_deduplicated(self):
        empty = {
            "metadata": {
                "provider": "APS",
                "scraped_at": "2026-07-18 10:00:00 MST",
                "source": "Mock",
                "scraper_version": "1.0.0",
            },
            "summary": {"outage_count": 0, "customers_affected": 0},
            "outages": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(archive, "DATA_FOLDER", Path(tmp)):
                saved1, _ = archive.save_snapshot("aps", dict(empty))
                later = dict(empty)
                later["metadata"] = dict(empty["metadata"])
                later["metadata"]["scraped_at"] = "2026-07-18 11:00:00 MST"
                saved2, _ = archive.save_snapshot("aps", later)

                self.assertTrue(saved1)
                self.assertFalse(saved2)
                files = list((Path(tmp) / "aps").glob("*.json"))
                self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()
