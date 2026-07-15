import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestStadiumPulseAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("database_mode", data)
        self.assertIn("genai_mode", data)

    def test_get_zones(self):
        response = self.client.get("/api/zones")
        self.assertEqual(response.status_code, 200)
        zones = response.json()
        self.assertIsInstance(zones, list)
        self.assertEqual(len(zones), 6)
        
        # Verify zone IDs
        zone_ids = [z["zone_id"] for z in zones]
        self.assertEqual(sorted(zone_ids), sorted(['ZONE_A', 'ZONE_B', 'ZONE_C', 'ZONE_D', 'ZONE_E', 'ZONE_F']))

    def test_post_telemetry_valid(self):
        # Post valid telemetry
        payload = {
            "zone_id": "ZONE_A",
            "occupancy": 8000,
            "capacity": 15000,
            "temperature": 90.0,
            "humidity": 60.0
        }
        response = self.client.post("/api/telemetry", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["zone_id"], "ZONE_A")
        
        # Check computed fields
        zone_data = data["data"]
        self.assertEqual(zone_data["density_pct"], 53.33)
        self.assertGreater(zone_data["heat_index"], 90.0)
        self.assertIn("risk_index", zone_data)
        self.assertIn("status", zone_data)

    def test_post_telemetry_invalid_zone(self):
        # Invalid zone ID (not in A-F)
        payload = {
            "zone_id": "ZONE_Z",
            "occupancy": 1000,
            "temperature": 75.0,
            "humidity": 50.0
        }
        response = self.client.post("/api/telemetry", json=payload)
        # Should fail validation (422 Unprocessable Entity)
        self.assertEqual(response.status_code, 422)

    def test_post_telemetry_negative_values(self):
        # Negative occupancy
        payload = {
            "zone_id": "ZONE_A",
            "occupancy": -50,
            "temperature": 75.0,
            "humidity": 50.0
        }
        response = self.client.post("/api/telemetry", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_get_alerts_list(self):
        response = self.client.get("/api/alerts")
        self.assertEqual(response.status_code, 200)
        alerts = response.json()
        self.assertIsInstance(alerts, list)

    def test_post_and_get_incidents(self):
        # 1. Post new incident
        incident_payload = {
            "incident_id": "test-inc-123",
            "zone_id": "ZONE_B",
            "title": "Simulated Alert Test",
            "description": "This is a unit test incident log",
            "priority": "P2",
            "status": "OPEN",
            "timestamp": "2026-07-15T12:00:00Z"
        }
        post_response = self.client.post("/api/incidents", json=incident_payload)
        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(post_response.json()["status"], "success")

        # 2. Get list and check presence
        get_response = self.client.get("/api/incidents")
        self.assertEqual(get_response.status_code, 200)
        incidents = get_response.json()
        self.assertIsInstance(incidents, list)
        
        # Verify the logged incident is in the list
        test_inc = next((inc for inc in incidents if inc["incident_id"] == "test-inc-123"), None)
        self.assertIsNotNone(test_inc)
        self.assertEqual(test_inc["title"], "Simulated Alert Test")

    def test_trigger_reasoning(self):
        # This will query our Gemini Service which will fall back to deterministic mock recommendation cards
        response = self.client.post("/api/reason")
        self.assertEqual(response.status_code, 200)
        cards = response.json()
        self.assertIsInstance(cards, list)
        self.assertGreater(len(cards), 0)
        
        # Verify recommendation card structure
        for card in cards:
            self.assertIn("zone_id", card)
            self.assertIn("severity", card)
            self.assertIn("confidence", card)
            self.assertIn("causal_analysis", card)
            self.assertIn("action_items", card)
            self.assertIn("multilingual_alerts", card)
