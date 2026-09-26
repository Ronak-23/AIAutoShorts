"""
server/routes/media.py
======================
Media gallery, direct MP4 streaming, downloads, and thumbnail asset delivery.
Strictly isolates media by user and blocks unauthorized cross-user access.
"""

import os
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional

from config.settings import OUTPUT_DIR, THUMBNAIL_DIR
from server.routes.auth import get_current_user
from server.auth.service import get_user_from_token
from server.auth.security import create_access_token
from core.db.repository import (
    list_pipeline_runs,
    get_pipeline_run,
    get_pipeline_run_by_video_filename,
    update_pipeline_run
)
from core.channel_context import ChannelContext
from core.youtube_uploader import YouTubeUploader

router = APIRouter(prefix="/api/media", tags=["Media"])


@router.get("/videos")
async def list_videos(current_user: dict = Depends(get_current_user)):
    """Returns only completed final videos owned by the current authenticated user."""
    runs = list_pipeline_runs(user_id=current_user["id"], limit=100)
    videos: List[Dict[str, Any]] = []

    # Generate a user token for media streaming links
    token = create_access_token({"sub": current_user["id"], "username": current_user["username"]})

    for r in runs:
        final_video = r.get("final_video_path")
        if final_video and os.path.exists(final_video):
            filename = os.path.basename(final_video)
            file_size = os.path.getsize(final_video)
            thumb = r.get("thumbnail_path")
            thumb_filename = os.path.basename(thumb) if thumb and os.path.exists(thumb) else None

            videos.append({
                "run_id": r["id"],
                "filename": filename,
                "title": (r.get("story") or {}).get("title") or (r.get("script") or {}).get("title") or filename,
                "channel_name": r.get("channel_name"),
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "duration_seconds": r.get("video_duration"),
                "qc_score": r.get("qc_score"),
                "video_qc_score": r.get("video_qc_score"),
                "youtube_video_id": r.get("youtube_video_id"),
                "stream_url": f"/api/media/video/{filename}?token={token}",
                "thumbnail_url": f"/api/media/thumbnail/{thumb_filename}?token={token}" if thumb_filename else None,
                "created_at": r.get("created_at")
            })

    return videos


@router.get("/video/{filename}")
async def stream_video(
    filename: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """Streams the requested MP4 video with strict user ownership validation."""
    video_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    # Resolve requesting user
    user = None
    tok = token or (authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None)
    if tok:
        user = get_user_from_token(tok)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Enforce ownership check
    run = get_pipeline_run_by_video_filename(filename)
    if run:
        is_owner = run.get("user_id") == user.get("id")
        is_admin = user.get("role") == "admin"
        if not is_owner and not is_admin:
            raise HTTPException(status_code=403, detail="Access denied: you do not own this video.")

    return FileResponse(video_path, media_type="video/mp4", filename=filename)


@router.get("/thumbnail/{filename}")
async def get_thumbnail(
    filename: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """Serves the thumbnail image with ownership validation."""
    thumb_path = os.path.join(THUMBNAIL_DIR, filename)
    if not os.path.exists(thumb_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    user = None
    tok = token or (authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None)
    if tok:
        user = get_user_from_token(tok)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    base = os.path.splitext(filename)[0]
    run = get_pipeline_run_by_video_filename(f"{base}.mp4")
    if run:
        is_owner = run.get("user_id") == user.get("id")
        is_admin = user.get("role") == "admin"
        if not is_owner and not is_admin:
            raise HTTPException(status_code=403, detail="Access denied: you do not own this thumbnail.")

    media_type = "image/png" if filename.endswith(".png") else "image/jpeg"
    return FileResponse(thumb_path, media_type=media_type)


@router.post("/upload-youtube/{run_id}")
async def upload_gallery_video_to_youtube(
    run_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Uploads an existing rendered video from the media gallery directly to its channel's YouTube account."""
    run = get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Video run not found")
    if run.get("user_id") != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied: you do not own this video.")

    final_video = run.get("final_video_path")
    if not final_video or not os.path.exists(final_video):
        raise HTTPException(status_code=400, detail="Video file does not exist on disk.")

    channel_name = run.get("channel_name") or "demo_channel"
    ctx = ChannelContext(channel_identifier=channel_name, user_id=current_user["id"])

    if not ctx.has_youtube_auth:
        raise HTTPException(
            status_code=400,
            detail=f"Channel '{ctx.display_name}' is not connected to YouTube. Please connect your YouTube channel in the Channels tab first."
        )

    script = run.get("script") or {}
    title = script.get("title") or (run.get("story") or {}).get("title") or os.path.basename(final_video)
    description = script.get("description") or ""
    tags = script.get("hashtags") or ["shorts", "viral"]
    thumbnail_path = run.get("thumbnail_path")

    try:
        uploader = YouTubeUploader(ctx=ctx)
        upload_result = uploader.upload(
            final_video,
            title=title,
            description=description,
            tags=tags,
            thumbnail_path=thumbnail_path,
            run_id=run_id
        )

        if not upload_result or upload_result == "QUOTA_EXHAUSTED":
            raise HTTPException(
                status_code=500,
                detail="YouTube upload failed. Daily API quota may be exhausted or channel token was rejected."
            )

        video_id = upload_result.get("id") if isinstance(upload_result, dict) else str(upload_result)

        # Update run in database
        update_pipeline_run(run_id, {
            "youtube_video_id": video_id,
            "status": "published",
            "auto_post_youtube": 1
        })

        return {
            "success": True,
            "youtube_video_id": video_id,
            "video_url": f"https://youtube.com/shorts/{video_id}",
            "channel_title": ctx.youtube_channel_title or ctx.display_name
        }

    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"YouTube upload error: {str(ex)}")

