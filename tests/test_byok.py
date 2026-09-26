"""
tests/test_byok.py
==================
Comprehensive test suite for Multi-Tenant BYOK (Bring Your Own Key) architecture:
  1. Cryptographic encryption/decryption round-trip (AES-256-GCM) & tamper resistance
  2. Masked key preview formatting
  3. Database repository CRUD and multi-tenant user isolation
  4. Preflight key validation
  5. REST API endpoints (GET, POST, DELETE, /validate) via TestClient
  6. Pipeline runtime key scoping via ChannelContext & ai_client
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.repository import (
    init_db,
    save_user_api_key,
    list_user_api_keys,
    get_user_api_key,
    delete_user_api_key,
    get_raw_user_api_keys,
)
from server.auth.crypto import (
    encrypt_api_key,
    decrypt_api_key,
    make_key_preview,
    get_user_decrypted_keys,
    validate_provider_key,
)
from server.auth.service import register_user, authenticate_user
from server.app import app
from core.channel_context import ChannelContext
from core.ai_client import scoped_context, _resolve_keys


class TestBYOK(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

        # Create two isolated test users
        import uuid
        uid = uuid.uuid4().hex[:6]
        cls.user_a = register_user(f"byok_user_a_{uid}", "pass_a_12345", f"a_{uid}@test.com")
        cls.user_b = register_user(f"byok_user_b_{uid}", "pass_b_12345", f"b_{uid}@test.com")

        # Get JWT tokens
        token_a = cls.client.post("/api/auth/login", json={"username": cls.user_a["username"], "password": "pass_a_12345"}).json()["access_token"]
        token_b = cls.client.post("/api/auth/login", json={"username": cls.user_b["username"], "password": "pass_b_12345"}).json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {token_a}"}
        cls.headers_b = {"Authorization": f"Bearer {token_b}"}

    # ── 1. Cryptography ────────────────────────────────────────────────────────
    def test_01_crypto_round_trip(self):
        secret = "gsk_test_secret_key_1234567890abcdef"
        enc = encrypt_api_key(secret)

        ciphertext = enc["encrypted_key"]
        nonce = enc["nonce"]
        tag = enc["tag"]

        self.assertNotEqual(secret, ciphertext)
        self.assertEqual(len(nonce), 12)  # 12 raw bytes
        self.assertEqual(len(tag), 16)    # 16 raw bytes

        decrypted = decrypt_api_key(ciphertext, nonce, tag)
        self.assertEqual(secret, decrypted)

    def test_02_crypto_tamper_resistance(self):
        secret = "AIzaSySecretGeminiKey123456789"
        enc = encrypt_api_key(secret)
        ciphertext = enc["encrypted_key"]
        nonce = enc["nonce"]
        tag = enc["tag"]

        # Alter tag -> must raise ValueError / InvalidTag
        tampered_tag = b"\x00" * 16
        with self.assertRaises(Exception):
            decrypt_api_key(ciphertext, nonce, tampered_tag)

        # Alter ciphertext -> must raise ValueError / InvalidTag
        tampered_cipher = ciphertext[:-2] + b"\xff\xff"
        with self.assertRaises(Exception):
            decrypt_api_key(tampered_cipher, nonce, tag)

    # ── 2. Key Preview Formatting ──────────────────────────────────────────────
    def test_03_key_previews(self):
        self.assertEqual(make_key_preview("gsk_1234567890abcdef"), "gsk_1...cdef")
        self.assertEqual(make_key_preview("AIzaSyVeryLongGoogleApiKey987654321"), "AIzaS...4321")
        self.assertEqual(make_key_preview("short"), "...ort")
        self.assertEqual(make_key_preview(""), "...")

    # ── 3. Database Repository & Multi-Tenant Isolation ────────────────────────
    def test_04_repository_crud_and_isolation(self):
        user_a_id = self.user_a["id"]
        user_b_id = self.user_b["id"]

        # User A saves a key
        enc_a = encrypt_api_key("gsk_user_a_key_xyz987")
        key_record = save_user_api_key({
            "user_id": user_a_id,
            "provider": "groq",
            "key_alias": "Personal Groq",
            "encrypted_key": enc_a["encrypted_key"],
            "nonce": enc_a["nonce"],
            "tag": enc_a["tag"],
            "key_preview": enc_a["key_preview"]
        })
        key_id = key_record["id"]
        self.assertIsNotNone(key_id)

        # User A lists keys -> sees it
        keys_a = list_user_api_keys(user_a_id)
        self.assertTrue(any(k["id"] == key_id for k in keys_a))
        # Ensure raw secrets/ciphers are NOT returned by list_user_api_keys
        self.assertNotIn("encrypted_key", keys_a[0])
        self.assertNotIn("nonce", keys_a[0])
        self.assertNotIn("tag", keys_a[0])
        self.assertEqual(keys_a[0]["key_preview"], "gsk_u...z987")

        # User B lists keys -> User A's key is NOT visible
        keys_b = list_user_api_keys(user_b_id)
        self.assertFalse(any(k["id"] == key_id for k in keys_b))

        # User B attempts to get User A's key -> None
        self.assertIsNone(get_user_api_key(key_id, user_id=user_b_id))

        # User B attempts to delete User A's key -> False
        deleted_by_b = delete_user_api_key(key_id, user_id=user_b_id)
        self.assertFalse(deleted_by_b)

        # Key still exists
        self.assertIsNotNone(get_user_api_key(key_id, user_id=user_a_id))

        # User A deletes their own key -> True
        deleted_by_a = delete_user_api_key(key_id, user_id=user_a_id)
        self.assertTrue(deleted_by_a)
        self.assertIsNone(get_user_api_key(key_id, user_id=user_a_id))

    # ── 4. Preflight Validation ────────────────────────────────────────────────
    @patch("requests.get")
    def test_05_preflight_groq_validation(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
        mock_get.return_value = mock_resp

        valid, msg = validate_provider_key("groq", "gsk_dummy_valid_key")
        self.assertTrue(valid)
        self.assertIn("verified", msg.lower())

    def test_06_preflight_invalid_provider_or_key(self):
        valid, msg = validate_provider_key("unknown_provider", "some_key")
        self.assertFalse(valid)
        self.assertIn("unsupported", msg.lower())

        valid, msg = validate_provider_key("groq", "")
        self.assertFalse(valid)
        self.assertIn("blank", msg.lower())

    # ── 5. REST API Endpoints ──────────────────────────────────────────────────
    def test_07_api_unauthorized_access(self):
        resp = self.client.get("/api/keys", headers={"Authorization": "Bearer invalid_token_12345"})
        self.assertEqual(resp.status_code, 401)

    @patch("server.routes.keys.validate_provider_key")
    def test_08_api_add_list_delete_key(self, mock_validate):
        mock_validate.return_value = (True, "Mock key is active")

        # 1. Add key as user A
        post_resp = self.client.post("/api/keys", headers=self.headers_a, json={
            "provider": "groq",
            "api_key": "gsk_live_test_user_a_key_555",
            "key_alias": "User A Groq Primary"
        })
        self.assertEqual(post_resp.status_code, 201)
        created_key = post_resp.json()
        self.assertEqual(created_key["provider"], "groq")
        self.assertEqual(created_key["key_alias"], "User A Groq Primary")
        self.assertEqual(created_key["key_preview"], "gsk_l..._555")
        key_id = created_key["id"]

        # 2. List keys for user A
        list_resp_a = self.client.get("/api/keys", headers=self.headers_a)
        self.assertEqual(list_resp_a.status_code, 200)
        user_a_keys = list_resp_a.json()
        self.assertTrue(any(k["id"] == key_id for k in user_a_keys))

        # 3. User B cannot see User A's key
        list_resp_b = self.client.get("/api/keys", headers=self.headers_b)
        self.assertEqual(list_resp_b.status_code, 200)
        self.assertFalse(any(k["id"] == key_id for k in list_resp_b.json()))

        # 4. User B cannot delete User A's key
        del_resp_b = self.client.delete(f"/api/keys/{key_id}", headers=self.headers_b)
        self.assertEqual(del_resp_b.status_code, 404)

        # 5. User A deletes their key
        del_resp_a = self.client.delete(f"/api/keys/{key_id}", headers=self.headers_a)
        self.assertEqual(del_resp_a.status_code, 200)
        self.assertEqual(del_resp_a.json()["status"], "success")

    # ── 6. ChannelContext & Runtime Scoping ───────────────────────────────────
    def test_09_runtime_key_resolution_and_fallback(self):
        user_id = self.user_a["id"]

        # User A adds a custom Groq key
        enc = encrypt_api_key("gsk_scoped_user_a_superkey")
        saved = save_user_api_key({
            "user_id": user_id,
            "provider": "groq",
            "key_alias": "Scoped Groq",
            "encrypted_key": enc["encrypted_key"],
            "nonce": enc["nonce"],
            "tag": enc["tag"],
            "key_preview": enc["key_preview"]
        })

        # ChannelContext for User A loads the decrypted key
        ctx = ChannelContext("demo_channel", user_id=user_id)
        groq_keys = ctx.get_provider_keys("groq")
        self.assertIn("gsk_scoped_user_a_superkey", groq_keys)

        # Scoped context overrides default resolution
        with scoped_context(ctx):
            resolved_groq = _resolve_keys("groq")
            self.assertEqual(resolved_groq, ["gsk_scoped_user_a_superkey"])

        # Outside scoped context, resolves back to global keys
        resolved_outside = _resolve_keys("groq")
        self.assertNotIn("gsk_scoped_user_a_superkey", resolved_outside)

        # Cleanup
        delete_user_api_key(saved["id"], user_id=user_id)


if __name__ == "__main__":
    unittest.main()
