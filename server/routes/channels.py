"""
server/routes/channels.py
=========================
Channel management and voice testing endpoints.
"""

import os
import io
import asyncio
import urllib.parse
from datetime import datetime, timezone, timedelta
import jwt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response, HTMLResponse
from typing import List, Optional

from server.schemas import (
    ChannelCreateRequest,
    ChannelUpdateRequest,
    ChannelResponse,
    TestVoiceRequest,
    YouTubeAuthUrlResponse
)
from server.routes.auth import get_current_user
from config.settings import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    YOUTUBE_REDIRECT_URI,
    get_youtube_oauth_config
)
from server.auth.crypto import encrypt_token_dict
from core.db.repository import (
    create_channel,
    get_channel_by_id,
    list_channels,
    update_channel,
    delete_channel,
    save_channel_youtube_token,
    delete_channel_youtube_token
)

router = APIRouter(prefix="/api/channels", tags=["Channels"])


@router.get("", response_model=List[ChannelResponse])
async def get_channels(current_user: dict = Depends(get_current_user)):
    """Returns all channels owned by the current user."""
    user_id = current_user["id"]
    channels = list_channels(user_id=user_id)
    return [ChannelResponse(**c) for c in channels]


@router.post("", response_model=ChannelResponse)
async def create_new_channel(req: ChannelCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new channel profile in SQLite."""
    user_id = current_user["id"]
    channel_dict = req.model_dump()
    channel_dict["user_id"] = user_id
    channel_dict["name"] = channel_dict["name"].strip().lower()
    if not channel_dict.get("display_name"):
        channel_dict["display_name"] = channel_dict["name"].title()
    if not channel_dict.get("tags") or not isinstance(channel_dict["tags"], list):
        channel_dict["tags"] = ["shorts", "viral"]
    if not channel_dict.get("rss_feeds") or not isinstance(channel_dict["rss_feeds"], list):
        channel_dict["rss_feeds"] = ["https://techcrunch.com/feed/"]
    if not channel_dict.get("vocabulary") or not isinstance(channel_dict["vocabulary"], list):
        channel_dict["vocabulary"] = []

    # Check for name collision
    existing = [c for c in list_channels(user_id=user_id) if c["name"] == channel_dict["name"]]
    if existing:
        raise HTTPException(status_code=400, detail=f"Channel '{channel_dict['name']}' already exists.")

    created = create_channel(channel_dict)
    return ChannelResponse(**created)


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_single_channel(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Returns details for a single channel."""
    c = get_channel_by_id(channel_id)
    if not c or c["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChannelResponse(**c)


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_existing_channel(channel_id: str, req: ChannelUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates a channel profile."""
    c = get_channel_by_id(channel_id)
    if not c or c["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Channel not found")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = update_channel(channel_id, updates)
    return ChannelResponse(**updated)


@router.delete("/{channel_id}")
async def delete_existing_channel(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Deletes a channel profile."""
    c = get_channel_by_id(channel_id)
    if not c or c["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Channel not found")

    user_channels = list_channels(user_id=current_user["id"])
    if len(user_channels) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete your only remaining channel.")

    delete_channel(channel_id)
    return {"message": "Channel deleted successfully"}


@router.post("/test-voice")
async def test_voice_sample(req: TestVoiceRequest):
    """Synthesizes a short test audio snippet using Edge TTS and returns audio/mpeg bytes."""
    import edge_tts
    try:
        communicate = edge_tts.Communicate(
            text=req.text,
            voice=req.voice_name,
            rate=req.voice_rate
        )
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])

        audio_bytes = audio_stream.getvalue()
        if not audio_bytes:
            raise RuntimeError("No audio data was generated.")

        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {e}")


@router.get("/{channel_id}/youtube/auth-url", response_model=YouTubeAuthUrlResponse)
async def get_youtube_auth_url(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Generates Google OAuth 2.0 consent URL for connecting a YouTube channel."""
    c = get_channel_by_id(channel_id)
    if not c or c["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Channel not found")

    oauth_cfg = get_youtube_oauth_config()
    if not oauth_cfg:
        return YouTubeAuthUrlResponse(
            configured=False,
            message="YouTube OAuth credentials not found. Please set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in your .env file."
        )

    client_info = oauth_cfg.get("web") or oauth_cfg.get("installed", {})
    client_id = client_info.get("client_id")
    if not client_id:
        return YouTubeAuthUrlResponse(
            configured=False,
            message="Invalid YouTube OAuth configuration: missing client_id."
        )

    redirect_uris = client_info.get("redirect_uris", [])
    redirect_uri = redirect_uris[0] if redirect_uris else YOUTUBE_REDIRECT_URI

    # Secure signed state token (valid for 15 minutes)
    payload = {
        "channel_id": channel_id,
        "user_id": current_user["id"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    state_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube",
        "access_type": "offline",
        "prompt": "consent",
        "state": state_token,
        "include_granted_scopes": "true",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return YouTubeAuthUrlResponse(auth_url=auth_url, configured=True)


@router.get("/youtube/callback", response_class=HTMLResponse)
async def youtube_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """Google OAuth 2.0 redirect callback endpoint."""
    def _html_page(title: str, heading: str, text: str, is_success: bool, channel_id: str = "", channel_title: str = ""):
        accent_color = "#10b981" if is_success else "#f43f5e"
        bg_card = "#1e293b"
        script = f"""
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: '{"YOUTUBE_AUTH_SUCCESS" if is_success else "YOUTUBE_AUTH_ERROR"}',
                        channelId: '{channel_id}',
                        channelTitle: '{channel_title}',
                        error: '{text}'
                    }}, '*');
                    setTimeout(function() {{ window.close(); }}, 1500);
                }} else {{
                    setTimeout(function() {{ window.location.href = '/'; }}, 2000);
                }}
            </script>
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: #0f172a;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    color: #f8fafc;
                }}
                .card {{
                    background: {bg_card};
                    border: 1px solid #334155;
                    border-radius: 20px;
                    padding: 32px 40px;
                    text-align: center;
                    max-width: 440px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                }}
                h2 {{ color: {accent_color}; margin-top: 0; margin-bottom: 12px; font-size: 20px; }}
                p {{ color: #94a3b8; font-size: 14px; line-height: 1.5; margin-bottom: 16px; }}
                .hint {{ color: #64748b; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>{heading}</h2>
                <p>{text}</p>
                <p class="hint">This window will close automatically...</p>
            </div>
            {script}
        </body>
        </html>
        """

    if error:
        return HTMLResponse(_html_page("Connection Failed", "Connection Cancelled", f"Google returned error: {error}", False))

    if not code or not state:
        return HTMLResponse(_html_page("Connection Failed", "Invalid Request", "Missing authorization code or state token.", False))

    try:
        payload = jwt.decode(state, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        channel_id = payload.get("channel_id")
        user_id = payload.get("user_id")
    except Exception:
        return HTMLResponse(_html_page("Connection Failed", "Invalid Session", "Security state token expired or invalid. Please retry.", False))

    c = get_channel_by_id(channel_id)
    if not c or c["user_id"] != user_id:
        return HTMLResponse(_html_page("Connection Failed", "Channel Not Found", "Target channel could not be resolved.", False))

    oauth_cfg = get_youtube_oauth_config()
    if not oauth_cfg:
        return HTMLResponse(_html_page("Connection Failed", "Server Misconfiguration", "OAuth configuration missing on server.", False))

    client_info = oauth_cfg.get("web") or oauth_cfg.get("installed", {})
    client_id = client_info.get("client_id")
    client_secret = client_info.get("client_secret")
    redirect_uris = client_info.get("redirect_uris", [])
    redirect_uri = redirect_uris[0] if redirect_uris else YOUTUBE_REDIRECT_URI

    # Exchange authorization code for tokens
    try:
        import requests
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            },
            timeout=15
        )
        if token_resp.status_code != 200:
            err_details = token_resp.text
            return HTMLResponse(_html_page("Connection Failed", "Token Exchange Failed", f"Google token error: {err_details}", False))

        token_json = token_resp.json()
    except Exception as req_err:
        return HTMLResponse(_html_page("Connection Failed", "Network Error", f"Failed to contact Google token endpoint: {req_err}", False))

    # Fetch YouTube channel info
    channel_title = c.get("display_name", "")
    yt_channel_id = ""
    access_token = token_json.get("access_token")
    if access_token:
        try:
            yt_res = requests.get(
                "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if yt_res.status_code == 200:
                items = yt_res.json().get("items", [])
                if items:
                    yt_channel_id = items[0].get("id", "")
                    channel_title = items[0].get("snippet", {}).get("title") or channel_title
        except Exception:
            pass

    # Build token dict and encrypt
    token_dict = {
        "token": access_token,
        "refresh_token": token_json.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"],
    }
    try:
        encrypted_token = encrypt_token_dict(token_dict)
        save_channel_youtube_token(channel_id, encrypted_token, channel_title, yt_channel_id)
    except Exception as enc_err:
        return HTMLResponse(_html_page("Connection Failed", "Storage Error", f"Failed to securely save token: {enc_err}", False))

    return HTMLResponse(_html_page(
        "YouTube Connected",
        "✓ Channel Connected!",
        f"Channel <strong>{channel_title}</strong> is now authorized for automatic uploads.",
        True,
        channel_id=channel_id,
        channel_title=channel_title
    ))


@router.delete("/{channel_id}/youtube")
async def disconnect_youtube_channel(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Disconnects YouTube authorization and clears tokens for a channel."""
    c = get_channel_by_id(channel_id)
    if not c or c["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Channel not found")

    delete_channel_youtube_token(channel_id)
    return {"message": "YouTube authorization removed successfully"}

