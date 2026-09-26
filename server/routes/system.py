"""
server/routes/system.py
=======================
System diagnostics, health checks, storage status, and API key metrics.
"""

import os
import shutil
from fastapi import APIRouter
from config.settings import (
    APP_NAME, APP_VERSION, DB_PATH, OUTPUT_DIR,
    GROQ_API_KEYS, GEMINI_API_KEYS, OPENROUTER_API_KEYS, PEXELS_API_KEYS,
    get_video_encoder_args
)
from server.schemas import SystemHealthResponse

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """Returns real-time health metrics for the AIAutoShorts production instance."""
    # Check DB
    db_ok = os.path.exists(DB_PATH)

    # Check disk space
    free_gb = 0.0
    if os.path.exists(OUTPUT_DIR):
        free_gb = round(shutil.disk_usage(OUTPUT_DIR).free / (1024 ** 3), 2)

    # Check GPU
    encoder_args = get_video_encoder_args()
    has_gpu = "nvenc" in " ".join(encoder_args).lower()

    return SystemHealthResponse(
        status="healthy",
        app_name=APP_NAME,
        version=APP_VERSION,
        database_connected=db_ok,
        groq_keys_count=len(GROQ_API_KEYS),
        gemini_keys_count=len(GEMINI_API_KEYS),
        openrouter_keys_count=len(OPENROUTER_API_KEYS),
        pexels_keys_count=len(PEXELS_API_KEYS),
        disk_free_gb=free_gb,
        gpu_acceleration=has_gpu
    )
