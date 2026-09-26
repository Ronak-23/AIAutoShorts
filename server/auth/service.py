"""
server/auth/service.py
======================
Multi-tenant authentication and user lifecycle service for AIAutoShorts.
Manages user accounts, JWT credentials, and isolated starter channels in SQLite.
"""

import uuid
from typing import Optional, Dict, Any, List
from core.db.repository import (
    get_user_by_username,
    get_user_by_id,
    create_user as db_create_user,
    list_channels,
    create_channel
)
from server.auth.security import hash_password, verify_password, decode_access_token


def provision_starter_channel(user_id: str, username: str) -> Dict[str, Any]:
    """Provisions a default starter channel in SQLite for a new user."""
    channel_name = f"{username.lower().strip()}_channel"
    existing = [c for c in list_channels(user_id=user_id) if c["name"] == channel_name]
    if existing:
        return existing[0]

    starter_data = {
        "user_id": user_id,
        "name": channel_name,
        "display_name": f"{username.title()}'s Channel",
        "niche": "Technology, AI, and Future Innovations",
        "tone": "Engaging, authoritative, fast-paced",
        "target_audience": "Tech enthusiasts, creators, and curious thinkers",
        "voice_provider": "edge",
        "voice_name": "en-US-ChristopherNeural",
        "voice_rate": "+8%",
        "voice_pitch": "+0Hz",
        "video_duration_seconds": 55,
        "min_words": 110,
        "max_words": 140,
        "fps": 30,
        "visual_mode": "stock_plus_wiki",
        "stock_provider": "pexels",
        "default_bgm_mood": "suspense",
        "bgm_volume": 0.22,
        "caption_style": "yellow_glow",
        "is_active": True,
        "tags": ["shorts", "tech", "ai", "future"],
        "rss_feeds": ["https://techcrunch.com/feed/"],
        "vocabulary": []
    }
    return create_channel(starter_data)


def register_user(username: str, password: str, email: Optional[str] = None, role: str = "user") -> Dict[str, Any]:
    """Registers a new user account and provisions their personal starter channel."""
    clean_username = username.strip().lower()
    existing = get_user_by_username(clean_username)
    if existing:
        raise ValueError(f"Username '{clean_username}' is already registered.")

    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password(password)
    user = db_create_user(user_id, clean_username, hashed_pwd, email, role)

    # Automatically provision starter channel
    provision_starter_channel(user_id, clean_username)
    return user


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifies username and password, returning sanitized user info."""
    user = get_user_by_username(username.strip().lower())
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "created_at": user.get("created_at")
    }


def ensure_default_user() -> Dict[str, Any]:
    """Ensures a default demo user and starter channel exist in SQLite for quick testing."""
    demo = get_user_by_username("demo")
    if not demo:
        try:
            demo = register_user("demo", "demo123", email="demo@aiautoshorts.local", role="admin")
        except Exception:
            demo = get_user_by_username("demo")
    else:
        # Ensure demo channel exists
        provision_starter_channel(demo["id"], "demo")
    return demo


def get_user_channels(user_id: str) -> List[Dict[str, Any]]:
    """Returns list of channels owned by the given user."""
    return list_channels(user_id=user_id)


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Validates JWT access token and resolves user record."""
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    return get_user_by_id(user_id)
