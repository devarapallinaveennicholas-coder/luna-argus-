"""Automated tests for Project Luna Argus.
Run: python -m unittest discover tests -v
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as luna


class LunaArgusTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        luna.app.config["DB_PATH"] = self.path
        luna.init_db()
        self.client = luna.app.test_client()

    def tearDown(self):
        os.remove(self.path)

    def test_bay_initialisation(self):
        data = self.client.get("/api/bays").json
        self.assertEqual(data["total"], 24)
        self.assertEqual(data["available"], 24)

    def test_status_update_changes_counts(self):
        response = self.client.post(
            "/api/telemetry",
            json={"bay_id": "A1", "distance_cm": 10},
        )
        self.assertTrue(response.json["occupied"])
        data = self.client.get("/api/bays").json
        self.assertEqual((data["occupied"], data["available"]), (1, 23))
        self.assertAlmostEqual(data["utilisation"], 4.2, places=1)

    def test_event_is_stored_only_on_change(self):
        for _ in range(3):
            self.client.post(
                "/api/telemetry",
                json={"bay_id": "B2", "distance_cm": 12},
            )
        self.assertEqual(len(self.client.get("/api/events").json), 1)

    def test_vehicle_leaves(self):
        self.client.post(
            "/api/telemetry",
            json={"bay_id": "C3", "occupied": True},
        )
        self.client.post(
            "/api/telemetry",
            json={"bay_id": "C3", "distance_cm": 150},
        )
        self.assertEqual(self.client.get("/api/bays").json["occupied"], 0)
        self.assertEqual(len(self.client.get("/api/events").json), 2)

    def test_repeated_updates_keep_latest_state(self):
        for distance in (10, 120, 8, 200, 15):
            self.client.post(
                "/api/telemetry",
                json={"bay_id": "A4", "distance_cm": distance},
            )
        bay = next(
            b for b in self.client.get("/api/bays").json["bays"]
            if b["bay_id"] == "A4"
        )
        self.assertEqual(bay["occupied"], 1)

    def test_validation_rejects_bad_input(self):
        self.assertEqual(
            self.client.post(
                "/api/telemetry",
                json={"bay_id": "Z9", "occupied": True},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                "/api/telemetry",
                json={"bay_id": "A1", "distance_cm": "abc"},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/api/telemetry",
                json={"bay_id": "A1", "distance_cm": 9999},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/api/telemetry", json={"bay_id": "A1"}).status_code,
            400,
        )

    def test_reset_and_export(self):
        self.client.post(
            "/api/telemetry",
            json={"bay_id": "A1", "occupied": True},
        )
        self.assertIn("A1", self.client.get("/api/export.csv").get_data(as_text=True))
        self.client.post("/api/reset")
        self.assertEqual(self.client.get("/api/bays").json["occupied"], 0)

    def test_dashboard_loads(self):
        self.assertEqual(self.client.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
