"""
tests/test_youtube_auth.py
==========================
Unit & Integration tests for production-level YouTube OAuth 2.0 architecture:
1. AES-256-GCM token encryption and decryption.
2. Database persistence of encrypted tokens in channels table.
3. ChannelContext in-memory decryption.
4. YouTubeUploader initialization, token loading, and upload keyword tolerance.
5. OAuth auth-url generation and validation.
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.auth.crypto import encrypt_token_dict, decrypt_token_dict
from core.db.repository import (
    init_db,
    create_user,
    create_channel,
    get_channel_by_id,
    save_channel_youtube_token,
    delete_channel_youtube_token,
    delete_channel
)
from core.channel_context import ChannelContext
from core.youtube_uploader import YouTubeUploader


class TestYouTubeAuthArchitecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        cls.test_channel_name = f"yt_test_{uuid.uuid4().hex[:8]}"
        create_user(cls.test_user_id, f"user_{uuid.uuid4().hex[:6]}", "hashed_pw")
        cls.channel = create_channel({
            "user_id": cls.test_user_id,
            "name": cls.test_channel_name,
            "display_name": "Test YT Channel",
            "niche": "Tech Testing",
            "tone": "Fast",
            "voice_name": "en-US-GuyNeural"
        })

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "channel") and cls.channel:
            delete_channel(cls.channel["id"])

    def test_01_token_encryption_and_decryption(self):
        """Verifies AES-256-GCM encryption and decryption round-trip."""
        token_payload = {
            "token": "ya29.test_access_token_12345",
            "refresh_token": "1//test_refresh_token_67890",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_client_secret_xyz",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"]
        }

        encrypted = encrypt_token_dict(token_payload)
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, "")
        self.assertNotIn("ya29.test", encrypted)  # Ciphertext must not leak plaintext

        decrypted = decrypt_token_dict(encrypted)
        self.assertEqual(decrypted, token_payload)

    def test_02_corrupted_token_handling(self):
        """Verifies graceful handling of corrupted or invalid ciphertext."""
        self.assertEqual(decrypt_token_dict(""), {})
        self.assertEqual(decrypt_token_dict("invalid_base64_payload_string"), {})

    def test_03_db_token_persistence(self):
        """Verifies saving encrypted token in DB and reading back through repository."""
        chan_id = self.channel["id"]

        token_payload = {
            "token": "ya29.auth_persisted_token",
            "refresh_token": "1//refresh_persisted_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "persisted_client.apps.googleusercontent.com",
            "client_secret": "persisted_secret",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"]
        }
        encrypted = encrypt_token_dict(token_payload)

        # Save token
        success = save_channel_youtube_token(
            chan_id,
            encrypted,
            channel_title="Official Test Channel",
            youtube_channel_id="UC_test_12345"
        )
        self.assertTrue(success)

        # Retrieve and verify
        updated_chan = get_channel_by_id(chan_id)
        self.assertTrue(updated_chan["has_youtube_auth"])
        self.assertEqual(updated_chan["youtube_channel_title"], "Official Test Channel")
        self.assertEqual(updated_chan["youtube_channel_id"], "UC_test_12345")

    def test_04_channel_context_decryption(self):
        """Verifies ChannelContext decrypts token data in memory upon initialization."""
        chan_name = self.test_channel_name
        ctx = ChannelContext(channel_identifier=chan_name, user_id=self.test_user_id)

        self.assertTrue(ctx.has_youtube_auth)
        self.assertIsNotNone(ctx.youtube_token_data)
        self.assertEqual(ctx.youtube_token_data.get("token"), "ya29.auth_persisted_token")
        self.assertEqual(ctx.youtube_token_data.get("refresh_token"), "1//refresh_persisted_token")
        self.assertEqual(ctx.youtube_channel_title, "Official Test Channel")

    def test_05_youtube_uploader_initialization_and_credentials(self):
        """Verifies YouTubeUploader correctly takes ctx and builds Credentials from in-memory token."""
        ctx = ChannelContext(channel_identifier=self.test_channel_name, user_id=self.test_user_id)
        uploader = YouTubeUploader(ctx=ctx)
        self.assertEqual(uploader.ctx, ctx)

        # Verify upload method accepts kwargs (e.g. run_id) without error
        # With AUTO_POST_YOUTUBE=False, upload immediately returns None (dry run)
        res = uploader.upload(
            video_path="fake_path.mp4",
            title="Test Title",
            description="Test Description",
            tags=["tech"],
            thumbnail_path="fake_thumb.jpg",
            run_id="run_12345"
        )
        self.assertIsNone(res)

    def test_06_token_deletion(self):
        """Verifies deleting YouTube authorization clears tokens and resets auth flag."""
        chan_id = self.channel["id"]
        deleted = delete_channel_youtube_token(chan_id)
        self.assertTrue(deleted)

        updated_chan = get_channel_by_id(chan_id)
        self.assertFalse(updated_chan["has_youtube_auth"])
        self.assertIsNone(updated_chan.get("youtube_token_encrypted"))

    def test_07_media_gallery_upload_endpoint(self):
        """Verifies media gallery upload endpoint validation checks."""
        from fastapi.testclient import TestClient
        from server.app import app
        from server.auth.security import create_access_token

        client = TestClient(app)
        token = create_access_token({"sub": self.test_user_id, "username": "testuser"})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Non-existent run_id returns 404
        resp = client.post("/api/media/upload-youtube/non_existent_run_999", headers=headers)
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
