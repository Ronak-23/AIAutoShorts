"""
tests/test_media_isolation.py
==============================
Tests for:
1. title_to_snake_case slugification
2. Intermediate asset cleanup logic
3. Multi-tenant user isolation on /api/media/videos and /api/media/video/{filename}
"""

import os
import sys
import unittest
import uuid
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils import title_to_snake_case
from core.graph.nodes import cleanup_intermediate_assets
from config.settings import OUTPUT_DIR, THUMBNAIL_DIR
from server.app import app
from server.auth.service import register_user
from server.auth.security import create_access_token
from core.db.repository import init_db, create_pipeline_run, update_pipeline_run


class TestMediaIsolationAndNaming(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "clips"), exist_ok=True)
        os.makedirs(THUMBNAIL_DIR, exist_ok=True)

    def test_01_title_to_snake_case(self):
        self.assertEqual(
            title_to_snake_case("Silicon Chips vs Quantum Doom!"),
            "silicon_chips_vs_quantum_doom"
        )
        self.assertEqual(
            title_to_snake_case("Why AI Won't Replace Coders (Yet)? 🤖"),
            "why_ai_won_t_replace_coders_yet"
        )
        self.assertEqual(
            title_to_snake_case("Café & Résumé: 100% Top-Secret!"),
            "cafe_resume_100_top_secret"
        )
        self.assertEqual(
            title_to_snake_case(""),
            "short_video"
        )
        self.assertEqual(
            title_to_snake_case(None),
            "short_video"
        )
        # Test max length truncation
        long_title = "A " * 50  # 100 chars
        truncated = title_to_snake_case(long_title, max_length=20)
        self.assertTrue(len(truncated) <= 20)
        self.assertFalse(truncated.endswith("_"))

    def test_02_cleanup_intermediate_assets(self):
        mock_run_id = f"test_cleanup_{uuid.uuid4().hex[:8]}"
        
        # Create mock intermediate files
        raw_clip = os.path.join(OUTPUT_DIR, f"{mock_run_id}_raw_body1.mp4")
        merged_vid = os.path.join(OUTPUT_DIR, f"{mock_run_id}_merged.mp4")
        voice_file = os.path.join(OUTPUT_DIR, f"{mock_run_id}_voice.mp3")
        bgm_file = os.path.join(OUTPUT_DIR, f"{mock_run_id}_bgm.mp3")
        sub_clip = os.path.join(OUTPUT_DIR, "clips", f"{mock_run_id}_clip0.mp4")
        concat_txt = os.path.join(OUTPUT_DIR, f"{mock_run_id}_concat_list.txt")
        
        # Create mock final and thumbnail files
        final_vid = os.path.join(OUTPUT_DIR, f"{mock_run_id}_final_video.mp4")
        final_thumb = os.path.join(THUMBNAIL_DIR, f"{mock_run_id}_thumb.jpg")
        
        for fpath in [raw_clip, merged_vid, voice_file, bgm_file, sub_clip, concat_txt, final_vid, final_thumb]:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write("mock")
                
        self.assertTrue(os.path.exists(raw_clip))
        self.assertTrue(os.path.exists(final_vid))
        
        # Execute cleanup
        cleaned = cleanup_intermediate_assets(
            run_id=mock_run_id,
            final_video_path=final_vid,
            thumbnail_path=final_thumb
        )
        
        self.assertGreaterEqual(cleaned, 6)
        # Intermediate files must be deleted
        self.assertFalse(os.path.exists(raw_clip))
        self.assertFalse(os.path.exists(merged_vid))
        self.assertFalse(os.path.exists(voice_file))
        self.assertFalse(os.path.exists(bgm_file))
        self.assertFalse(os.path.exists(sub_clip))
        self.assertFalse(os.path.exists(concat_txt))
        
        # Final video and thumbnail must remain intact
        self.assertTrue(os.path.exists(final_vid))
        self.assertTrue(os.path.exists(final_thumb))
        
        # Clean up test artifacts
        os.remove(final_vid)
        os.remove(final_thumb)

    def test_03_user_media_isolation(self):
        # 1. Register User A and User B
        uid_suffix = uuid.uuid4().hex[:6]
        user_a = register_user(f"user_a_{uid_suffix}", "pwd123", email=f"a_{uid_suffix}@test.com")
        user_b = register_user(f"user_b_{uid_suffix}", "pwd123", email=f"b_{uid_suffix}@test.com")
        
        token_a = create_access_token({"sub": user_a["id"], "username": user_a["username"]})
        token_b = create_access_token({"sub": user_b["id"], "username": user_b["username"]})
        
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # 2. Create mock video files on disk
        vid_a_name = f"user_a_secret_video_{uid_suffix}.mp4"
        vid_b_name = f"user_b_exclusive_video_{uid_suffix}.mp4"
        vid_a_path = os.path.join(OUTPUT_DIR, vid_a_name)
        vid_b_path = os.path.join(OUTPUT_DIR, vid_b_name)
        
        with open(vid_a_path, "w", encoding="utf-8") as f:
            f.write("video content A")
        with open(vid_b_path, "w", encoding="utf-8") as f:
            f.write("video content B")
            
        # 3. Create pipeline run records in DB
        from core.db.repository import list_channels
        ch_a = list_channels(user_id=user_a["id"])[0]
        ch_b = list_channels(user_id=user_b["id"])[0]
        
        run_a_id = f"run_a_{uid_suffix}"
        run_b_id = f"run_b_{uid_suffix}"
        
        create_pipeline_run({
            "id": run_a_id,
            "user_id": user_a["id"],
            "channel_id": ch_a["id"],
            "channel_name": ch_a["name"],
            "status": "completed",
            "progress_percentage": 100,
            "current_node": "completed"
        })
        update_pipeline_run(run_a_id, {
            "final_video_path": vid_a_path,
            "status": "completed"
        })
        
        create_pipeline_run({
            "id": run_b_id,
            "user_id": user_b["id"],
            "channel_id": ch_b["id"],
            "channel_name": ch_b["name"],
            "status": "completed",
            "progress_percentage": 100,
            "current_node": "completed"
        })
        update_pipeline_run(run_b_id, {
            "final_video_path": vid_b_path,
            "status": "completed"
        })
        
        try:
            # 4. User A requests /api/media/videos
            resp_a = self.client.get("/api/media/videos", headers=headers_a)
            self.assertEqual(resp_a.status_code, 200)
            videos_a = resp_a.json()
            filenames_a = [v["filename"] for v in videos_a]
            
            self.assertIn(vid_a_name, filenames_a)
            self.assertNotIn(vid_b_name, filenames_a)
            
            # 5. User B requests /api/media/videos
            resp_b = self.client.get("/api/media/videos", headers=headers_b)
            self.assertEqual(resp_b.status_code, 200)
            videos_b = resp_b.json()
            filenames_b = [v["filename"] for v in videos_b]
            
            self.assertIn(vid_b_name, filenames_b)
            self.assertNotIn(vid_a_name, filenames_b)
            
            # 6. User B attempts to stream User A's video -> HTTP 403 Forbidden!
            resp_forbidden = self.client.get(f"/api/media/video/{vid_a_name}", headers=headers_b)
            self.assertEqual(resp_forbidden.status_code, 403)
            
            # 7. User A streams their own video -> HTTP 200 OK
            resp_ok = self.client.get(f"/api/media/video/{vid_a_name}", headers=headers_a)
            self.assertEqual(resp_ok.status_code, 200)
            
            # 8. User A streams via query param token -> HTTP 200 OK
            resp_token_ok = self.client.get(f"/api/media/video/{vid_a_name}?token={token_a}")
            self.assertEqual(resp_token_ok.status_code, 200)

            # 9. Unauthenticated streaming attempt -> HTTP 401 Unauthorized
            resp_unauth = self.client.get(f"/api/media/video/{vid_a_name}")
            self.assertEqual(resp_unauth.status_code, 401)

        finally:
            if os.path.exists(vid_a_path):
                os.remove(vid_a_path)
            if os.path.exists(vid_b_path):
                os.remove(vid_b_path)


if __name__ == "__main__":
    unittest.main()
