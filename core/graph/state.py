"""
core/graph/state.py
===================
Defines the shared typed state dictionary and supporting models
for the AutoReel LangGraph multi-agent video production pipeline.
"""

from typing import TypedDict, List, Dict, Optional, Any
from pydantic import BaseModel, Field


class Scene(BaseModel):
    """Represents a single scene segment in a Short script."""
    scene_id: int
    narration_act: str = ""        # e.g., "The Hook", "The Escalation", "The Payoff"
    text: str = ""
    duration_est_seconds: float = 0.0
    visual_query: str = ""         # 2-3 word stock footage search query
    broll_path: Optional[str] = None


class VideoProductionState(TypedDict, total=False):
    """
    The central state schema passed across all nodes in the LangGraph workflow.
    """
    # ── Pipeline Metadata ──
    run_id: str
    user_id: str
    channel_id: str
    channel_name: str
    channel_display_name: str
    channel_config: Dict[str, Any]
    status: str                         # "initializing", "scripting", "producing", "assembled", "published", "failed"
    current_node: str
    logs: List[str]
    error: Optional[str]

    # ── Step 0: Experiment Recipe ──
    recipe: Dict[str, Any]

    # ── Step 1: Story & Research ──
    story: Dict[str, Any]
    story_swap_count: int

    # ── Step 2: Script Generation ──
    script: Dict[str, Any]
    scenes: List[Dict[str, Any]]
    script_retry_count: int
    max_script_retries: int
    correction_feedback: Optional[str]

    # ── Step 2.1: Legal Compliance Gate ──
    legal_checked: bool
    legal_safe: bool
    legal_reason: str

    # ── Step 2.2: Creative QC Gate ──
    qc_approved: bool
    qc_score: float
    qc_feedback: str

    # ── Step 3: Neural Voiceover & Subtitles ──
    audio_path: Optional[str]
    voice_actuals: Dict[str, Any]

    # ── Step 4: Visual Retrieval & B-Roll ──
    broll_clips: List[str]
    bg_clip: Optional[str]

    # ── Step 4.1: Dynamic Music Direction ──
    bgm_path: Optional[str]
    bgm_mood: Optional[str]
    bgm_track_id: Optional[str]

    # ── Step 5.1: Thumbnail Design ──
    thumbnail_path: Optional[str]
    thumbnail_actuals: Dict[str, Any]

    # ── Step 5: Final Video Assembly ──
    final_video_path: Optional[str]
    video_duration: float

    # ── Step 5.2 / 5.3: Video QC & Review ──
    video_qc_score: float
    video_qc_approved: bool
    video_qc_feedback: str

    # ── Step 6: Human-in-the-Loop & Publishing ──
    human_approved: bool
    auto_post_youtube: bool
    youtube_video_id: Optional[str]
    execution_manifest: Dict[str, Any]
