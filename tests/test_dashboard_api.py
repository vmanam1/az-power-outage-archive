import unittest
import tempfile
import os
import json

# Setup mock data directory before importing app
temp_dir = tempfile.TemporaryDirectory()
os.environ["DATA_DIR"] = temp_dir.name

from app import app
from dashboard.cache import global_cache

class TestDashboardAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = temp_dir
        
        # Populate dynamic folder
        prov_dir = os.path.join(cls.temp_dir.name, "aps")
        os.makedirs(prov_dir)
        
        snap = {
            "metadata": {
                "provider": "APS",
                "scraped_at": "2026-07-15 16:00:00 MST",
                "source": "Mock"
            },
            "summary": {
                "outage_count": 1,
                "customers_affected": 30
            },
            "outages": [
                {
                    "latitude": 33.45,
                    "longitude": -112.07,
                    "customers": 30,
                    "cause": "Equipment failure",
                    "start_time": "2026-07-15 15:10:00 MST"
                }
            ]
        }
        
        with open(os.path.join(prov_dir, "2026-07-15_16-00.json"), "w", encoding="utf-8") as f:
            json.dump(snap, f)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        global_cache.clear()
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "healthy"})

    def test_file_status_endpoint(self):
        response = self.client.get("/api/file-status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["file_count"], 1)
        self.assertGreater(data["max_mtime"], 0.0)

    def test_metadata_endpoint(self):
        response = self.client.get("/api/metadata")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data["snapshot_count"], 1)
        self.assertIn("aps", data["providers"])
        self.assertEqual(data["date_bounds"]["earliest"], "2026-07-15 16:00:00 MST")
        self.assertEqual(data["date_bounds"]["latest"], "2026-07-15 16:00:00 MST")
        self.assertIn("Equipment failure", data["available_causes"])
        self.assertEqual(data["data_quality_counts"]["malformed_files"], 0)

    def test_outages_query_endpoint(self):
        response = self.client.get("/api/outages?providers=aps&display_mode=latest")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data["summary"]["visible_records"], 1)
        self.assertEqual(data["summary"]["total_customers"], 30)
        self.assertEqual(len(data["outages"]), 1)
        self.assertEqual(data["outages"][0]["provider"], "aps")
        self.assertEqual(data["outages"][0]["cause"], "Equipment failure")

    def test_timeline_endpoint(self):
        response = self.client.get("/api/timeline?providers=aps")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["outages_count"], 1)
        self.assertEqual(data[0]["customers_affected"], 30)
        self.assertEqual(data[0]["provider"], "aps")

    def test_csv_export_endpoint(self):
        response = self.client.get("/api/export.csv?providers=aps")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn("attachment; filename=outages_export.csv", response.headers["Content-Disposition"])
        
        csv_data = response.get_data(as_text=True)
        # Check headers and data
        self.assertIn("Provider", csv_data)
        self.assertIn("Customers Affected", csv_data)
        self.assertIn("APS", csv_data)
        self.assertIn("30", csv_data)
        self.assertIn("Equipment failure", csv_data)

if __name__ == "__main__":
    unittest.main()
