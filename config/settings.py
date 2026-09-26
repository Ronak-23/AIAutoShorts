"""
AIAutoShorts Configuration Engine
=================================
Centralized settings, environment variables, multi-provider API keys,
directory paths, and hardware-accelerated encoding configurations.
"""

import os
import subprocess
from dotenv import load_dotenv

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(_ENV_PATH)

# Application Info
APP_NAME = "AIAutoShorts"
APP_VERSION = "3.0.0"

# Directories
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "videos")
THUMBNAIL_DIR = os.path.join(BASE_DIR, "output", "thumbnails")
LOG_DIR = os.path.join(BASE_DIR, "output", "logs")
BGM_DEFAULTS_DIR = os.path.join(CONFIG_DIR, "bgm_defaults")
DB_PATH = os.path.join(DATA_DIR, "aiautoshorts.db")

# Ensure required directories exist
for directory in [CONFIG_DIR, DATA_DIR, OUTPUT_DIR, THUMBNAIL_DIR, LOG_DIR, BGM_DEFAULTS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Google Cloud Credentials (if present)
gcp_key_path = os.path.join(CONFIG_DIR, "gcp-credentials.json")
if os.path.exists(gcp_key_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_key_path

# ── Primary AI: Groq (Round-Robin Key Pool) ──────────────────────────────────
GROQ_API_KEYS = []
_groq_idx = 1
while True:
    _key = os.getenv(f"GROQ_API_KEY_{_groq_idx}")
    if not _key:
        break
    GROQ_API_KEYS.append(_key.strip())
    _groq_idx += 1
if not GROQ_API_KEYS and os.getenv("GROQ_API_KEY"):
    GROQ_API_KEYS.append(os.getenv("GROQ_API_KEY").strip())
GROQ_API_KEYS = [k for k in GROQ_API_KEYS if k and len(k) > 10]
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else ""
GROQ_MODEL = os.getenv("GROQ_MODEL", "groq/compound")

# ── Fallback AI: Gemini (Key Pool) ───────────────────────────────────────────
GEMINI_API_KEYS = []
_gemini_idx = 1
while True:
    _key = os.getenv(f"GEMINI_API_KEY_{_gemini_idx}")
    if not _key:
        break
    GEMINI_API_KEYS.append(_key.strip())
    _gemini_idx += 1
if os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY").strip() not in GEMINI_API_KEYS:
    GEMINI_API_KEYS.append(os.getenv("GEMINI_API_KEY").strip())
GEMINI_API_KEYS = [k for k in GEMINI_API_KEYS if k and len(k) > 10]
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# ── Fallback AI: NVIDIA & OpenRouter ──────────────────────────────────────────
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()

OPENROUTER_API_KEYS = []
_openrouter_idx = 1
while True:
    _key = os.getenv(f"OPENROUTER_API_KEY_{_openrouter_idx}")
    if not _key:
        break
    OPENROUTER_API_KEYS.append(_key.strip())
    _openrouter_idx += 1
if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY").strip() not in OPENROUTER_API_KEYS:
    OPENROUTER_API_KEYS.append(os.getenv("OPENROUTER_API_KEY").strip())
OPENROUTER_API_KEYS = [k for k in OPENROUTER_API_KEYS if k and len(k) > 10]
OPENROUTER_API_KEY = OPENROUTER_API_KEYS[0] if OPENROUTER_API_KEYS else ""
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free")

# ── Text-to-Speech: ElevenLabs ────────────────────────────────────────────────
ELEVENLABS_API_KEYS = []
_el_idx = 1
while True:
    _key = os.getenv(f"ELEVENLABS_API_KEY_{_el_idx}")
    if not _key:
        break
    ELEVENLABS_API_KEYS.append(_key.strip())
    _el_idx += 1
if not ELEVENLABS_API_KEYS and os.getenv("ELEVENLABS_API_KEY"):
    ELEVENLABS_API_KEYS.append(os.getenv("ELEVENLABS_API_KEY").strip())
ELEVENLABS_API_KEYS = [k for k in ELEVENLABS_API_KEYS if k and len(k) > 10]
ELEVENLABS_API_KEY = ELEVENLABS_API_KEYS[0] if ELEVENLABS_API_KEYS else ""

# ── Stock Footage APIs ───────────────────────────────────────────────────────
PEXELS_API_KEYS = []
_pex_idx = 1
while True:
    _key = os.getenv(f"PEXELS_API_KEY_{_pex_idx}")
    if not _key:
        break
    PEXELS_API_KEYS.append(_key.strip())
    _pex_idx += 1
if not PEXELS_API_KEYS and os.getenv("PEXELS_API_KEY"):
    PEXELS_API_KEYS.append(os.getenv("PEXELS_API_KEY").strip())
PEXELS_API_KEYS = [k for k in PEXELS_API_KEYS if k and len(k) > 5]
PEXELS_API_KEY = PEXELS_API_KEYS[0] if PEXELS_API_KEYS else ""

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "").strip()

# ── YouTube & Social ─────────────────────────────────────────────────────────
YOUTUBE_DATA_API_KEY = os.getenv("YOUTUBE_DATA_API_KEY", "").strip()
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8000/api/channels/youtube/callback").strip()
YOUTUBE_CLIENT_SECRETS_FILE = os.path.join(CONFIG_DIR, "youtube_client_secrets.json")
AUTO_POST_YOUTUBE = os.getenv("AUTO_POST_YOUTUBE", "false").lower() in ("true", "1", "yes")

def get_youtube_oauth_config() -> dict | None:
    """
    Returns OAuth 2.0 client configuration dictionary.
    Prioritizes YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET from environment.
    Falls back to config/youtube_client_secrets.json if present.
    """
    if YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET:
        return {
            "web": {
                "client_id": YOUTUBE_CLIENT_ID,
                "client_secret": YOUTUBE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [YOUTUBE_REDIRECT_URI]
            }
        }
    if os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
        try:
            import json
            with open(YOUTUBE_CLIENT_SECRETS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

# ── Telegram Bot ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# ── Security & Authentication ────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "aiautoshorts_super_secret_jwt_key_change_in_production_2026")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

# ── Video & Quality Settings ─────────────────────────────────────────────────
DEFAULT_VIDEO_DURATION = 55
DEFAULT_FPS = 30
MIN_DISK_SPACE_GB = float(os.getenv("MIN_DISK_SPACE_GB", "2.0"))
QUALITY_SCORE_THRESHOLD = 80
SKIP_CLIP_VALIDATION = os.getenv("SKIP_CLIP_VALIDATION", "false").lower() in ("true", "1", "yes")

# ── Default Channel Fallbacks & Legacy Compatibility Aliases ─────────────────
DEFAULT_CHANNEL_NAME = "DemoChannel"
DEFAULT_NICHE = "Artificial intelligence and future tech news"
DEFAULT_CHANNEL_TONE = "Engaging, authoritative, fast-paced"
DEFAULT_RSS_FEEDS = ["https://techcrunch.com/feed/"]
DEFAULT_TAGS = ["shorts", "tech", "ai"]
DEFAULT_VOICE = "en-US-ChristopherNeural"
DEFAULT_VOICE_RATE = "+8%"
DEFAULT_VOCABULARY = []

# Legacy Aliases (Channels are now primarily stored in SQLite DB)
CHANNEL_NAME = DEFAULT_CHANNEL_NAME
NICHE = DEFAULT_NICHE
CHANNEL_TONE = DEFAULT_CHANNEL_TONE
RSS_FEEDS = DEFAULT_RSS_FEEDS
YOUTUBE_DEFAULT_TAGS = DEFAULT_TAGS
VOCABULARY = DEFAULT_VOCABULARY
VOICE_NAME = DEFAULT_VOICE
VOICE_RATE = DEFAULT_VOICE_RATE
LANGUAGE = "English"
VIDEO_DURATION_SECONDS = DEFAULT_VIDEO_DURATION
FEATURE_JSON_SCHEMA = False
CHANNELS_DIR = "channels"
YOUTUBE_CHROMIUM_PROFILE_PATH = os.getenv("YOUTUBE_CHROMIUM_PROFILE_PATH", "")
YOUTUBE_CATEGORY_ID = "28"
MIN_SAMPLES_TO_TUNE = 5
PRIMARY_METRIC = "avg_view_percentage"
ANALYTICS_DELAY_HOURS = 48

# ── Hardware Video Acceleration Auto-Detector ────────────────────────────────
_cached_encoder_args = None

def get_video_encoder_args() -> list:
    """
    Auto-detects whether NVIDIA NVENC hardware acceleration is available.
    Returns optimized GPU encoder arguments if supported, otherwise returns CPU fallback.
    """
    global _cached_encoder_args
    if _cached_encoder_args is not None:
        return _cached_encoder_args

    try:
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=192x192:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"]
        res = subprocess.run(cmd, capture_output=True, timeout=5)
        if res.returncode == 0:
            _cached_encoder_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "19"]
        else:
            _cached_encoder_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]
    except Exception:
        _cached_encoder_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

    return _cached_encoder_args
