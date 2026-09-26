"""
tests/test_auth.py
==================
Verifies password hashing, JWT issue/validation, and multi-tenant starter channel provisioning.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.auth.security import hash_password, verify_password, create_access_token, decode_access_token
from server.auth.service import register_user, authenticate_user, get_user_channels
from core.db.repository import init_db


class TestAuthService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_password_hashing(self):
        plain = "MySecretPass_2026"
        hashed = hash_password(plain)
        self.assertNotEqual(plain, hashed)
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_02_jwt_token(self):
        payload = {"sub": "user_123", "username": "alice"}
        token = create_access_token(payload)
        self.assertIsInstance(token, str)

        decoded = decode_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "user_123")
        self.assertEqual(decoded["username"], "alice")

    def test_03_registration_and_starter_channel(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        username = f"alex_{uid}"
        user = register_user(username, "alex_password_123", f"{username}@example.com")
        self.assertEqual(user["username"], username)

        # Authenticate
        auth = authenticate_user(username, "alex_password_123")
        self.assertIsNotNone(auth)
        self.assertEqual(auth["id"], user["id"])

        # Check starter channel was provisioned
        channels = get_user_channels(user["id"])
        self.assertTrue(len(channels) >= 1)
        self.assertEqual(channels[0]["name"], f"{username}_channel")
        self.assertTrue("technology" in channels[0]["niche"].lower())


if __name__ == "__main__":
    unittest.main()
