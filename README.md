# AIAutoShorts: Production Autonomous YouTube Shorts Pipeline

**AIAutoShorts** is an autonomous, multi-tenant AI video production pipeline engineered to research, generate, validate, assemble, and publish viral YouTube Shorts (1080x1920 vertical video, 60fps) from scratch.

Built with **FastAPI**, **LangGraph Multi-Agent Orchestrator**, a **Normalized SQLite WAL Engine**, an **interactive React 18 Web Studio**, and **pure hardware-accelerated FFmpeg**.

---

## 1. Key Capabilities & Architecture

- **LangGraph Multi-Agent Engine**: 12-stage StateGraph with cyclic script revision loops, parallel asset fan-out (`voiceover`, `visual_curator`, `music_director`, `thumbnail`), and Human-in-the-Loop review gates.
- **Multi-Tenant Persistence**: Fully normalized SQLite database with Write-Ahead Logging (`PRAGMA journal_mode=WAL`). Channels, pipeline executions, streaming logs, and cron schedules are persistent and isolated per user.
- **Multi-Provider AI Key Cascade**: Round-robin key rotation across Groq (`compound`, `gpt-oss-120b`, `llama-3.3-70b`) with instant failover to Gemini (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`) and OpenRouter.
- **Neural Voiceover & Karaoke Subtitles**: Edge TTS + Whisper word-level alignment with animated ASS subtitle generation.
- **Stock Visuals & Zero-Token Validation**: Pexels, Pixabay, Wikimedia, and YouTube scraper backed by offline CLIP semantic similarity matching.
- **Pure FFmpeg Video Assembler**: Dynamic audio ducking (background music drops 14–18dB during voiceover), vertical 1080x1920 auto-crop, flash-frame thumbnail injection, and NVIDIA NVENC GPU acceleration.
- **Modular React 18 Web Studio**: Zero-build native ES Modules SPA with real-time SSE execution streaming, interactive SVG topology graph, and 9:16 vertical video player.

---

## 2. Quickstart

### Prerequisites
- Python 3.10+
- FFmpeg 6.0+ installed and on system PATH

### Installation
```bash
# 1. Clone repository / enter directory
cd d:\Projects\AIAutoShorts

# 2. Configure environment credentials
cp .env.example .env
# Edit .env with your Groq and Gemini API keys

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server and Web Studio
python run.py --port 8000
```

Open **http://localhost:8000/** in your browser.
Default developer account: `demo` / `demo123`.

---

## 3. Directory Layout

```
AIAutoShorts/
├── run.py                    # Unified entry point (FastAPI server + scheduler)
├── requirements.txt          # Production dependencies
├── config/
│   ├── settings.py           # Centralized settings & hardware auto-detection
│   └── bgm_defaults/         # Bundled royalty-free emergency audio by mood
├── core/
│   ├── db/                   # Normalized SQLite WAL engine & repositories
│   ├── graph/                # LangGraph StateGraph, nodes, and typed state
│   ├── agents/               # Legal, QC, Music Director, Thumbnail, Video QC
│   ├── gemini_client.py      # Multi-provider cascade with key rotation
│   ├── script_generator.py   # Fast single-pass viral script generator
│   ├── voiceover.py          # Multi-tier TTS + Whisper word-level alignment
│   ├── ass_generator.py      # Karaoke-style ASS subtitle animator
│   ├── video_clipper.py      # Stock footage retrieval engine + CLIP validation
│   ├── video_assembler.py    # FFmpeg dynamic ducking, scaling, and rendering
│   └── channel_context.py    # Database-backed channel configuration loader
├── server/
│   ├── app.py                # FastAPI server application
│   ├── manager.py            # Persisted PipelineRunManager & SSE broadcaster
│   ├── schemas.py            # Pydantic v2 request/response models
│   ├── auth/                 # Multi-tenant user auth & starter channel provisioning
│   ├── scheduler/            # Background cron automation engine
│   └── routes/               # Modular REST endpoints
├── ui/
│   ├── index.html            # Web studio HTML container with importmap
│   └── src/                  # React 18 components, context, and pages
└── tests/                    # Automated test suite (DB, Auth, Graph, API)
```
