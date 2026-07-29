import json
import os
import tempfile
import unittest
from unittest.mock import patch

import app as app_module


def _snapshot(provider, scraped_at, customers, total=None, restored=None):
    summary = {"outage_count": 1, "customers_affected": customers}
    if total is not None:
        summary["total_customers"] = total
    return {
        "metadata": {
            "provider": provider.upper(),
            "scraped_at": scraped_at,
            "source": "Mock",
            "scraper_version": "1.0.0",
        },
        "summary": summary,
        "outages": [{
            "latitude": 33.4, "longitude": -112.0, "customers": customers,
            "restored_time": restored,
        }],
    }


class ProviderSummaryTests(unittest.TestCase):
    def test_summary_uses_newest_snapshot_per_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov = os.path.join(tmp, "mohave")
            os.makedirs(prov)
            with open(os.path.join(prov, "2026-07-29_10-00.json"), "w", encoding="utf-8") as f:
                json.dump(_snapshot("mohave", "2026-07-29 10:00:00 MST", 5, total=47046), f)
            with open(os.path.join(prov, "2026-07-29_11-00.json"), "w", encoding="utf-8") as f:
                json.dump(_snapshot("mohave", "2026-07-29 11:00:00 MST", 93, total=47046), f)

            with patch.object(app_module, "DATA_DIR", tmp):
                res = app_module.app.test_client().get("/api/provider-summary")

            self.assertEqual(res.status_code, 200)
            rows = res.get_json()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["provider"], "mohave")
            self.assertEqual(row["customers_out"], 93)          # newest snapshot
            self.assertEqual(row["outage_count"], 1)
            self.assertEqual(row["total_customers"], 47046)
            self.assertEqual(row["scraped_at"], "2026-07-29 11:00:00 MST")

    def test_restored_outages_do_not_count_as_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov = os.path.join(tmp, "aps")
            os.makedirs(prov)
            with open(os.path.join(prov, "2026-07-29_11-00.json"), "w", encoding="utf-8") as f:
                json.dump(
                    _snapshot("aps", "2026-07-29 11:00:00 MST", 42,
                              restored="2026-07-29 10:30:00 MST"), f)

            with patch.object(app_module, "DATA_DIR", tmp):
                rows = app_module.app.test_client().get("/api/provider-summary").get_json()

            self.assertEqual(rows[0]["outage_count"], 0)
            self.assertEqual(rows[0]["customers_out"], 0)
            self.assertIsNone(rows[0]["total_customers"])


if __name__ == "__main__":
    unittest.main()
