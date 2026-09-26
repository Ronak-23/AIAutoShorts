"""
server/app.py
=============
FastAPI Application for AIAutoShorts.
Serves REST APIs, Web Studio UI, Multi-Tenant Auth, Server-Sent Events (SSE),
and Background Automation Scheduling.
"""

import os
import sys
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.settings import APP_NAME, APP_VERSION
from core.db.repository import init_db
from server.auth.service import ensure_default_user
from server.manager import get_manager
from server.scheduler.manager import get_scheduler
from server.routes import auth, channels, pipeline, media, schedules, analytics, system, keys

_UI_DIR = os.path.join(_ROOT, "ui")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown handler."""
    # 1. Initialize SQLite schema & default user
    init_db()
    ensure_default_user()

    # 2. Start automation scheduler in background
    pipeline_mgr = get_manager()
    scheduler = get_scheduler(pipeline_manager=pipeline_mgr)
    scheduler.start()

    yield

    # 3. Shutdown scheduler gracefully
    scheduler.stop()


app = FastAPI(
    title=f"{APP_NAME} Production API",
    description="Autonomous LangGraph Multi-Agent YouTube Shorts Production Pipeline with User Auth & Scheduling",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── Enable CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    """Ensure static UI assets and index pages are not cached aggressively by browsers."""
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static") or path in ("/", "/ui", "/index.html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ── Mount Static UI Assets ──
if os.path.exists(_UI_DIR):
    app.mount("/static", StaticFiles(directory=_UI_DIR), name="static")

# ── Include Modular Routers ──
app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(pipeline.router)
app.include_router(media.router)
app.include_router(schedules.router)
app.include_router(analytics.router)
app.include_router(system.router)
app.include_router(keys.router)


@app.get("/api", tags=["General"])
async def api_root():
    """API metadata and endpoints index."""
    return JSONResponse({
        "name": APP_NAME,
        "version": APP_VERSION,
        "engine": "LangGraph Multi-Agent Architecture",
        "database": "SQLite WAL Engine",
        "documentation": "/docs",
        "endpoints": {
            "auth": "/api/auth",
            "channels": "/api/channels",
            "pipeline_runs": "/api/pipeline/runs",
            "media_videos": "/api/media/videos",
            "schedules": "/api/schedules",
            "analytics": "/api/analytics/overview",
            "system_health": "/api/system/health"
        }
    })


@app.get("/ui", tags=["UI Dashboard"], response_class=FileResponse)
@app.get("/", tags=["UI Dashboard"], response_class=FileResponse)
async def serve_ui():
    """Serves the AIAutoShorts Web Studio SPA."""
    index_file = os.path.join(_UI_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({
        "name": APP_NAME,
        "version": APP_VERSION,
        "documentation": "/docs"
    })


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")
    args = parser.parse_args()

    print(f"\n==================================================")
    print(f"  {APP_NAME} v{APP_VERSION} — Autonomous Studio")
    print(f"  Web Dashboard: http://localhost:{args.port}/")
    print(f"  API Docs:      http://localhost:{args.port}/docs")
    print(f"==================================================\n")

    uvicorn.run("server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
