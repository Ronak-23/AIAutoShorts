"""
core/channel_context.py
=======================
Database-backed, thread-safe, immutable channel configuration context.
Loads channel configuration primarily from the SQLite database, with
graceful fallbacks to dictionary configs.
"""

import os
import re
from typing import Dict, Any, Optional, List
from config.settings import OUTPUT_DIR, THUMBNAIL_DIR, LOG_DIR
from core.db.repository import get_channel_by_name, get_channel_by_id, list_channels


class ChannelContext:
    """
    Immutable snapshot of a channel's configuration for a pipeline execution.
    Attributes are resolved at construction time and never mutated.
    """

    def __init__(self, channel_identifier: str, user_id: Optional[str] = None, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initializes ChannelContext.
        Args:
            channel_identifier: Channel ID or Channel Name slug (e.g. "demo_channel")
            user_id: Optional user ID for multi-tenant channel resolution
            config_dict: Optional direct dictionary override
        """
        cfg: Dict[str, Any] = {}

        if config_dict:
            cfg = dict(config_dict)
        else:
            # 1. Try finding by ID
            found = get_channel_by_id(channel_identifier)
            # 2. Try finding by user_id and name
            if not found and user_id:
                found = get_channel_by_name(user_id, channel_identifier)
            # 3. Try finding by name across any channel matching slug
            if not found:
                all_chans = list_channels()
                for c in all_chans:
                    if c["name"] == channel_identifier.strip().lower():
                        found = c
                        break
            if found:
                cfg = found

        self._data = cfg
        self.raw_config = cfg
        self.config = cfg

        # Identification
        self.id = str(cfg.get("id", ""))
        self.user_id = str(user_id or cfg.get("user_id") or "demo")
        self.channel_name = cfg.get("name") or channel_identifier.strip().lower()
        self.display_name = cfg.get("display_name") or cfg.get("CHANNEL_NAME") or self.channel_name.title()
        self.niche = cfg.get("niche") or cfg.get("NICHE") or "Artificial intelligence and future tech news"
        self.tone = cfg.get("tone") or cfg.get("CHANNEL_TONE") or "Engaging, futuristic, and fast-paced"
        self.target_audience = cfg.get("target_audience") or cfg.get("TARGET_AUDIENCE") or "Curious minds and tech enthusiasts"

        # Publishing & Metadata
        self.youtube_channel_id = cfg.get("youtube_channel_id") or cfg.get("YOUTUBE_CHANNEL_ID") or ""
        self.youtube_category_id = str(cfg.get("youtube_category_id") or cfg.get("YOUTUBE_CATEGORY_ID") or "28")
        self.default_tags = cfg.get("tags") or cfg.get("YOUTUBE_DEFAULT_TAGS") or ["shorts", "tech", "ai"]
        self.rss_feeds = cfg.get("rss_feeds") or cfg.get("RSS_FEEDS") or ["https://techcrunch.com/feed/"]
        self.vocabulary = cfg.get("vocabulary") or cfg.get("VOCABULARY") or []
        self.active = bool(cfg.get("is_active", cfg.get("active", True)))

        # Audio & Voiceover
        self.voice_provider = cfg.get("voice_provider") or cfg.get("VOICE_PROVIDER") or "edge"
        self.voice_name = cfg.get("voice_name") or cfg.get("voice") or "en-US-ChristopherNeural"
        self.voice_rate = str(cfg.get("voice_rate") or "+8%")
        pitch_raw = cfg.get("voice_pitch", "+0Hz")
        if isinstance(pitch_raw, (int, float)):
            self.voice_pitch = float(pitch_raw)
        else:
            match = re.search(r'([+-]?\d+(?:\.\d+)?)', str(pitch_raw))
            self.voice_pitch = float(match.group(1)) if match else 0.0

        # Video & Pacing
        self.video_duration_seconds = int(cfg.get("video_duration_seconds", 55))
        self.min_words = int(cfg.get("min_words", 110))
        self.max_words = int(cfg.get("max_words", 140))
        self.fps = int(cfg.get("fps") or cfg.get("FPS") or 30)

        # Visuals & Stock
        self.visual_mode = cfg.get("visual_mode") or cfg.get("VISUAL_MODE") or "stock_plus_wiki"
        self.stock_provider = cfg.get("stock_provider") or cfg.get("STOCK_PROVIDER") or "pexels"
        self.default_bgm_mood = cfg.get("default_bgm_mood") or cfg.get("DEFAULT_BGM_MOOD") or "suspense"
        self.bgm_volume = float(cfg.get("bgm_volume") or cfg.get("BGM_VOLUME") or 0.22)
        self.bgm_pool = cfg.get("bgm_pool", {})

        # Subtitles & Captions
        self.caption_style = cfg.get("caption_style") or cfg.get("CAPTION_STYLE") or "yellow_glow"
        self.caption_y = cfg.get("caption_y")
        if "caption_shift" in cfg:
            self.caption_shift = float(cfg["caption_shift"])
        else:
            # Dynamic calculation
            rate_percent = 0.0
            if self.voice_rate:
                m = re.search(r'([+-]?\d+)%', self.voice_rate)
                if m:
                    rate_percent = float(m.group(1))
            self.caption_shift = round(max(0.04, min(0.18, 0.08 + (rate_percent / 100.0) * 0.05)), 3)

        self.show_watermark = bool(cfg.get("show_watermark", cfg.get("SHOW_WATERMARK", False)))
        self.workspace_dir = OUTPUT_DIR
        self.thumbnail_dir = THUMBNAIL_DIR
        self.log_dir = LOG_DIR
        self.token_path = cfg.get("token_path") or os.path.join(LOG_DIR, f"token_{self.channel_name}.json")

        # In-memory decrypted YouTube OAuth credentials
        self.youtube_channel_title = cfg.get("youtube_channel_title") or ""
        self.youtube_token_data = None
        encrypted_token = cfg.get("youtube_token_encrypted")
        if encrypted_token:
            try:
                from server.auth.crypto import decrypt_token_dict
                self.youtube_token_data = decrypt_token_dict(encrypted_token)
            except Exception as e:
                print(f"[ChannelContext] Failed to decrypt token for {self.channel_name}: {e}")
        self.has_youtube_auth = bool(self.youtube_token_data)

        # Resolve user BYOK API keys if user_id is provided
        self.api_keys: Dict[str, List[str]] = {}
        if self.user_id:
            try:
                from server.auth.crypto import get_user_decrypted_keys
                self.api_keys = get_user_decrypted_keys(self.user_id)
            except Exception:
                self.api_keys = {}

    def get_provider_keys(self, provider: str) -> List[str]:
        """Returns scoped user BYOK keys for a specific provider, if configured."""
        return self.api_keys.get(provider.lower().strip(), [])

    def get(self, key: str, default: Any = None) -> Any:
        """Enables dict-like get() access on ChannelContext."""
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Enables subscript access on ChannelContext."""
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        """Enables in operator check on ChannelContext."""
        return key in self._data

    def to_dict(self) -> Dict[str, Any]:
        """Converts context into JSON-serializable dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.channel_name,
            "display_name": self.display_name,
            "niche": self.niche,
            "tone": self.tone,
            "target_audience": self.target_audience,
            "voice_provider": self.voice_provider,
            "voice_name": self.voice_name,
            "voice_rate": self.voice_rate,
            "voice_pitch": f"{self.voice_pitch:+.1f}Hz",
            "video_duration_seconds": self.video_duration_seconds,
            "min_words": self.min_words,
            "max_words": self.max_words,
            "fps": self.fps,
            "visual_mode": self.visual_mode,
            "stock_provider": self.stock_provider,
            "default_bgm_mood": self.default_bgm_mood,
            "bgm_volume": self.bgm_volume,
            "caption_style": self.caption_style,
            "is_active": self.active,
            "youtube_channel_id": self.youtube_channel_id,
            "youtube_category_id": self.youtube_category_id,
            "tags": self.default_tags,
            "rss_feeds": self.rss_feeds,
            "vocabulary": self.vocabulary,
        }
