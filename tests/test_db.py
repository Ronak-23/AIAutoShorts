"""
tests/test_db.py
================
Verifies SQLite schema initialization, user creation, channel CRUD,
pipeline run state persistence, and event logging.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.repository import (
    init_db,
    create_user,
    get_user_by_username,
    create_channel,
    get_channel_by_id,
    list_channels,
    update_channel,
    delete_channel,
    create_pipeline_run,
    update_pipeline_run,
    get_pipeline_run,
    record_pipeline_event,
    get_pipeline_events,
    create_schedule,
    get_schedule,
    delete_schedule,
    is_story_duplicate,
    mark_story_seen
)


class TestDatabaseRepository(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_user_lifecycle(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        user_id = f"user_{uid}"
        username = f"creator_{uid}"
        user = create_user(user_id, username, "hashed_dummy_pw", f"{username}@test.com")
        self.assertEqual(user["username"], username)

        fetched = get_user_by_username(username)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], user_id)

    def test_02_channel_crud(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        user_id = f"user_ch_{uid}"
        create_user(user_id, f"ch_user_{uid}", "pw", "ch@test.com")

        chan_id = f"chan_{uid}"
        chan_data = {
            "id": chan_id,
            "user_id": user_id,
            "name": f"tech_{uid}",
            "display_name": "Tech Test Channel",
            "niche": "AI and Robotics",
            "tone": "Fast-paced, engaging",
            "voice_name": "en-US-ChristopherNeural",
            "voice_rate": "+8%",
            "default_bgm_mood": "suspense",
            "bgm_volume": 0.25,
            "caption_style": "yellow_glow"
        }
        chan = create_channel(chan_data)
        self.assertEqual(chan["name"], f"tech_{uid}")

        # Fetch
        fetched = get_channel_by_id(chan_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["display_name"], "Tech Test Channel")

        # Update
        updated = update_channel(chan_id, {"display_name": "Tech Test Pro"})
        self.assertEqual(updated["display_name"], "Tech Test Pro")

        # List
        user_chans = list_channels(user_id=user_id)
        self.assertTrue(any(c["id"] == chan_id for c in user_chans))

    def test_03_pipeline_run_persistence(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        user_id = f"user_run_{uid}"
        create_user(user_id, f"run_user_{uid}", "pw", "run@test.com")
        chan_id = f"chan_run_{uid}"
        create_channel({
            "id": chan_id,
            "user_id": user_id,
            "name": f"run_chan_{uid}",
            "display_name": "Run Channel"
        })

        run_id = f"run_{uid}"
        run_data = {
            "id": run_id,
            "user_id": user_id,
            "channel_id": chan_id,
            "channel_name": f"run_chan_{uid}",
            "status": "running",
            "progress_percentage": 10,
            "current_node": "init_pipeline",
            "completed_nodes": ["init_pipeline"],
            "custom_topic": "Quantum Computing Breakthrough",
            "auto_post_youtube": False
        }
        created = create_pipeline_run(run_data)
        self.assertEqual(created["id"], run_id)
        self.assertEqual(created["status"], "running")

        # Update run with script and progress
        updated = update_pipeline_run(run_id, {
            "status": "completed",
            "progress_percentage": 100,
            "current_node": "assemble_video",
            "completed_nodes": ["init_pipeline", "scout_trend", "scriptwriter", "assemble_video"],
            "qc_score": 94.5,
            "final_video_path": "output/videos/test_output.mp4"
        })
        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["qc_score"], 94.5)
        self.assertEqual(updated["progress_percentage"], 100)

        # Verify query
        r = get_pipeline_run(run_id)
        self.assertEqual(r["final_video_path"], "output/videos/test_output.mp4")

    def test_04_pipeline_events_logging(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        user_id = f"user_ev_{uid}"
        create_user(user_id, f"ev_user_{uid}", "pw", "ev@test.com")
        chan_id = f"chan_ev_{uid}"
        create_channel({
            "id": chan_id,
            "user_id": user_id,
            "name": f"ev_chan_{uid}",
            "display_name": "Event Channel"
        })
        run_id = f"run_ev_{uid}"
        create_pipeline_run({
            "id": run_id,
            "user_id": user_id,
            "channel_id": chan_id,
            "channel_name": f"ev_chan_{uid}",
            "status": "running"
        })

        record_pipeline_event(
            run_id=run_id,
            event_type="node_completed",
            node_name="scriptwriter",
            message="Script generated with 125 words",
            data={"word_count": 125}
        )
        events = get_pipeline_events(run_id)
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[-1]["node_name"], "scriptwriter")

    def test_05_story_dedup(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        channel_name = f"chan_dedup_{uid}"
        title = f"OpenAI Releases Revolutionary Quantum Reasoning Engine {uid}"
        self.assertFalse(is_story_duplicate(channel_name, title))
        mark_story_seen(channel_name, title)
        self.assertTrue(is_story_duplicate(channel_name, title))


if __name__ == "__main__":
    unittest.main()
