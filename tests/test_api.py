"""
tests/test_api.py
=================
Verifies FastAPI REST endpoints using TestClient.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.app import app
from core.db.repository import init_db
from server.auth.service import ensure_default_user


class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        ensure_default_user()
        cls.client = TestClient(app)

    def test_01_api_root(self):
        resp = self.client.get("/api")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "AIAutoShorts")

    def test_02_system_health(self):
        resp = self.client.get("/api/system/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["app_name"], "AIAutoShorts")

    def test_03_auth_and_channels(self):
        # 1. Login demo user
        login_resp = self.client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get me
        me_resp = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["username"], "demo")

        # 3. List channels
        chan_resp = self.client.get("/api/channels", headers=headers)
        self.assertEqual(chan_resp.status_code, 200)
        channels = chan_resp.json()
        self.assertTrue(len(channels) >= 1)

    def test_04_pipeline_runs_listing(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = self.client.get("/api/pipeline/runs", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_05_create_channel_with_none_lists(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        import uuid
        chan_name = f"test_chan_{uuid.uuid4().hex[:6]}"
        create_resp = self.client.post("/api/channels", json={
            "name": chan_name,
            "display_name": "Test Channel Null Lists",
            "niche": "Tech",
            "tone": "Engaging",
            "tags": None,
            "rss_feeds": None,
            "vocabulary": None
        }, headers=headers)

        self.assertEqual(create_resp.status_code, 200)
        data = create_resp.json()
        self.assertIsInstance(data["tags"], list)
        self.assertIsInstance(data["rss_feeds"], list)
        self.assertIsInstance(data["vocabulary"], list)

        # Verify GET single channel
        get_resp = self.client.get(f"/api/channels/{data['id']}", headers=headers)
        self.assertEqual(get_resp.status_code, 200)
        self.assertIsInstance(get_resp.json()["tags"], list)

    def test_06_strict_authentication_enforced(self):
        """Protected endpoints must reject unauthenticated requests with 401."""
        # Unauthenticated calls (no Authorization header)
        for endpoint in ["/api/auth/me", "/api/channels", "/api/pipeline/runs", "/api/keys", "/api/media/videos"]:
            resp = self.client.get(endpoint)
            self.assertEqual(resp.status_code, 401, f"Expected 401 for {endpoint}, got {resp.status_code}")
            self.assertIn("Authentication required", resp.json().get("detail", ""))

        # Invalid token call
        invalid_resp = self.client.get("/api/auth/me", headers={"Authorization": "Bearer bogus_token_123"})
        self.assertEqual(invalid_resp.status_code, 401)
        self.assertIn("Invalid or expired token", invalid_resp.json().get("detail", ""))


if __name__ == "__main__":
    unittest.main()
