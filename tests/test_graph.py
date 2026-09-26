"""
tests/test_graph.py
===================
Verifies LangGraph topology construction and conditional routing.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph.workflow import build_aiautoshorts_graph, route_after_qc, should_revise_script
from core.graph.state import VideoProductionState


class TestGraphWorkflow(unittest.TestCase):

    def test_01_graph_compilation(self):
        app = build_aiautoshorts_graph()
        self.assertIsNotNone(app)
        nodes = list(app.nodes.keys())
        expected = [
            "init_pipeline", "scout_trend", "scriptwriter",
            "legal_check", "quality_control", "voiceover",
            "visual_curator", "music_director", "thumbnail",
            "assemble_video", "video_qc", "publish_youtube"
        ]
        for node in expected:
            self.assertIn(node, nodes)

    def test_02_routing_qc_approved(self):
        state: VideoProductionState = {
            "qc_approved": True,
            "script_retry_count": 0,
            "max_script_retries": 3
        }
        decision = should_revise_script(state)
        self.assertEqual(decision, "proceed_to_production")
        next_nodes = route_after_qc(state)
        self.assertEqual(next_nodes, ["voiceover", "visual_curator", "music_director", "thumbnail"])

    def test_03_routing_qc_rejected_with_retries(self):
        state: VideoProductionState = {
            "qc_approved": False,
            "script_retry_count": 1,
            "max_script_retries": 3
        }
        decision = should_revise_script(state)
        self.assertEqual(decision, "revise_script")
        next_nodes = route_after_qc(state)
        self.assertEqual(next_nodes, ["scriptwriter"])

    def test_04_routing_qc_retries_exhausted(self):
        state: VideoProductionState = {
            "qc_approved": False,
            "script_retry_count": 3,
            "max_script_retries": 3
        }
        decision = should_revise_script(state)
        self.assertEqual(decision, "proceed_to_production")
        next_nodes = route_after_qc(state)
        self.assertEqual(next_nodes, ["voiceover", "visual_curator", "music_director", "thumbnail"])


if __name__ == "__main__":
    unittest.main()
