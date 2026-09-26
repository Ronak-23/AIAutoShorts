"""
server/schemas.py
=================
Pydantic v2 data models for API requests, responses, and state tracking.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ── Authentication ───────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str = "user"
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Channels ─────────────────────────────────────────────────────────────────

class ChannelCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    display_name: Optional[str] = None
    niche: str = "Technology, AI, and Future Innovations"
    tone: str = "Engaging, authoritative, fast-paced"
    target_audience: Optional[str] = "Tech enthusiasts and curious thinkers"
    voice_provider: str = "edge"
    voice_name: str = "en-US-ChristopherNeural"
    voice_rate: str = "+8%"
    voice_pitch: str = "+0Hz"
    video_duration_seconds: int = 55
    min_words: int = 110
    max_words: int = 140
    fps: int = 30
    visual_mode: str = "stock_plus_wiki"
    stock_provider: str = "pexels"
    default_bgm_mood: str = "suspense"
    bgm_volume: float = 0.22
    caption_style: str = "yellow_glow"
    is_active: bool = True
    tags: Optional[List[str]] = None
    rss_feeds: Optional[List[str]] = None
    vocabulary: Optional[List[str]] = None


class ChannelUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    niche: Optional[str] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_name: Optional[str] = None
    voice_rate: Optional[str] = None
    voice_pitch: Optional[str] = None
    video_duration_seconds: Optional[int] = None
    min_words: Optional[int] = None
    max_words: Optional[int] = None
    fps: Optional[int] = None
    visual_mode: Optional[str] = None
    stock_provider: Optional[str] = None
    default_bgm_mood: Optional[str] = None
    bgm_volume: Optional[float] = None
    caption_style: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None
    rss_feeds: Optional[List[str]] = None
    vocabulary: Optional[List[str]] = None


class ChannelResponse(BaseModel):
    id: str
    user_id: str
    name: str
    display_name: str
    niche: str
    tone: str
    target_audience: Optional[str] = None
    voice_provider: str
    voice_name: str
    voice_rate: str
    voice_pitch: str
    video_duration_seconds: int
    min_words: int
    max_words: int
    fps: int
    visual_mode: str
    stock_provider: str
    default_bgm_mood: str
    bgm_volume: float
    caption_style: str
    is_active: bool
    youtube_channel_id: Optional[str] = None
    youtube_category_id: Optional[str] = "28"
    has_youtube_auth: bool = False
    youtube_channel_title: Optional[str] = None
    youtube_authenticated_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    rss_feeds: List[str] = Field(default_factory=list)
    vocabulary: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("tags", "rss_feeds", "vocabulary", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if not v or not isinstance(v, list):
            return []
        return v


class YouTubeAuthUrlResponse(BaseModel):
    auth_url: Optional[str] = None
    configured: bool = True
    message: Optional[str] = None


class TestVoiceRequest(BaseModel):
    voice_name: str = "en-US-ChristopherNeural"
    voice_rate: str = "+8%"
    text: str = "Welcome to AIAutoShorts. This is a real-time voice synthesis preview."


# ── Pipeline Runs ────────────────────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    channel_name: str = "demo_channel"
    channel_id: Optional[str] = None
    custom_topic: Optional[str] = None
    auto_post_youtube: bool = False
    interrupt_before_publish: bool = False


class PipelineRunStatus(BaseModel):
    run_id: str
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    channel_name: str
    channel_display_name: Optional[str] = None
    status: str
    progress_percentage: int = 0
    current_node: Optional[str] = None
    completed_nodes: List[str] = []
    created_at: str
    updated_at: str
    error: Optional[str] = None
    custom_topic: Optional[str] = None
    story_title: Optional[str] = None
    script_title: Optional[str] = None
    full_script: Optional[str] = None
    qc_approved: Optional[bool] = None
    qc_score: Optional[float] = None
    qc_feedback: Optional[str] = None
    video_qc_approved: Optional[bool] = None
    video_qc_score: Optional[float] = None
    video_qc_feedback: Optional[str] = None
    audio_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    final_video_path: Optional[str] = None
    video_duration: Optional[float] = None
    youtube_video_id: Optional[str] = None
    auto_post_youtube: bool = False
    interrupt_before_publish: bool = False


class HITLApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


# ── Schedules ────────────────────────────────────────────────────────────────

class ScheduleCreateRequest(BaseModel):
    channel_name: str
    frequency: str = "daily"  # 'hourly', 'every_6_hours', 'every_12_hours', 'daily'
    time_of_day: str = "09:00"
    auto_post_youtube: bool = False
    is_active: bool = True


class ScheduleUpdateRequest(BaseModel):
    frequency: Optional[str] = None
    time_of_day: Optional[str] = None
    auto_post_youtube: Optional[bool] = None
    is_active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    id: str
    user_id: str
    channel_id: str
    channel_name: str
    frequency: str
    time_of_day: Optional[str] = None
    auto_post_youtube: bool
    is_active: bool
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    created_at: Optional[str] = None


# ── System Health & Media ────────────────────────────────────────────────────

class SystemHealthResponse(BaseModel):
    status: str = "healthy"
    app_name: str
    version: str
    database_connected: bool
    groq_keys_count: int
    gemini_keys_count: int
    openrouter_keys_count: int
    pexels_keys_count: int
    disk_free_gb: float
    gpu_acceleration: bool
