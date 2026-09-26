"""
youtube_uploader.py
Uploads the final video to YouTube as a Short.
Uses YouTube Data API v3 with OAuth2 — free.

Setup (one time):
1. Go to console.cloud.google.com
2. Create project → Enable YouTube Data API v3
3. Create OAuth2 credentials → Desktop App
4. Download JSON → save as config/youtube_client_secrets.json
5. Run this script once — it'll open browser for auth
6. Token saved to channels/<channel_name>_token.json — never needs re-auth

ChannelContext integration:
  Pass a ChannelContext instance to authenticate() and upload() so the uploader
  reads the correct per-channel token file without relying on os.environ.
"""

import os
import json
import random
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from config.settings import (
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_CATEGORY_ID,
    AUTO_POST_YOUTUBE,
    CHANNELS_DIR
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


class YouTubeUploader:

    def __init__(self, ctx=None):
        self.ctx = ctx
        self.youtube = None

    def authenticate(self, ctx=None):
        """
        OAuth2 authentication — loads decrypted tokens from ChannelContext or token file.

        Args:
            ctx: Optional ChannelContext. When provided, reads youtube_token_data
                 or token_path directly from the context object.
        """
        ctx = ctx or self.ctx
        creds = None
        channel_name = ctx.channel_name if ctx is not None else os.environ.get("ACTIVE_CHANNEL", "demo_channel").strip()

        # 1. Check in-memory decrypted token from ChannelContext (DB-backed)
        token_data = getattr(ctx, "youtube_token_data", None) if ctx is not None else None
        if token_data and isinstance(token_data, dict):
            client_id = token_data.get("client_id") or os.getenv("YOUTUBE_CLIENT_ID", "").strip()
            client_secret = token_data.get("client_secret") or os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
            try:
                creds = Credentials(
                    token=token_data.get("token") or token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=SCOPES
                )
            except Exception as e:
                print(f"[YouTube] Could not construct credentials from DB token: {e}")
                creds = None

        # 2. Filesystem fallback if DB token not present
        if not creds:
            token_path = ctx.token_path if ctx is not None else os.path.join(CHANNELS_DIR, f"{channel_name}_token.json")
            if os.path.exists(token_path):
                try:
                    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                except Exception as e:
                    print(f"[YouTube] Could not read token file {token_path}: {e}")
                    creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                import time
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        creds.refresh(Request())
                        # Persist refreshed token back to SQLite database if ctx has an id
                        if ctx is not None and getattr(ctx, "id", None):
                            try:
                                from server.auth.crypto import encrypt_token_dict
                                from core.db.repository import save_channel_youtube_token
                                updated_dict = {
                                    "token": creds.token,
                                    "refresh_token": creds.refresh_token,
                                    "token_uri": creds.token_uri,
                                    "client_id": creds.client_id,
                                    "client_secret": creds.client_secret,
                                    "scopes": list(creds.scopes or SCOPES),
                                }
                                enc_str = encrypt_token_dict(updated_dict)
                                save_channel_youtube_token(ctx.id, enc_str, ctx.youtube_channel_title, ctx.youtube_channel_id)
                                ctx.youtube_token_data = updated_dict
                                print(f"[YouTube] Refreshed access token persisted to database for {channel_name}.")
                            except Exception as save_err:
                                print(f"[YouTube] Notice: failed to persist refreshed token to DB: {save_err}")
                        break  # Success
                    except Exception as refresh_err:
                        if "invalid_grant" in str(refresh_err) or attempt == max_retries - 1:
                            from core.notifier import send_message as _tg
                            _tg(
                                f"⚠️ *YouTube Token Refresh Failed* — {channel_name}\n"
                                f"Error: {refresh_err}\n"
                                f"👉 Reconnect your channel in the AIAutoShorts Web Studio (Channels tab)."
                            )
                            print(f"[YouTube] [ERROR] Token refresh failed: {refresh_err}")
                            return False
                        
                        print(f"[YouTube] [WARNING] Token refresh attempt {attempt + 1} failed, retrying... ({refresh_err})")
                        time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
            else:
                from core.notifier import send_message as _tg
                _tg(
                    f"🔑 *YouTube Authentication Required* — {channel_name}\n"
                    f"Token missing or invalid.\n"
                    f"👉 Open the Web Studio and click 'Connect YouTube' on your channel."
                )
                print(f"[YouTube] [ERROR] Valid YouTube token not found for {channel_name}.")
                print(f"[YouTube] Please connect your YouTube channel from the Web Studio UI.")
                return False

        self.youtube = build("youtube", "v3", credentials=creds)
        print(f"[YouTube] Authenticated for channel: {channel_name.upper()}")
        return True

    # ----------------------------------------------------------
    def upload(self, video_path: str, thumbnail_path: str = None,
               title: str = "", description: str = "", tags: list[str] = None, ctx=None, **kwargs) -> str | None:
        """
        Upload video and set thumbnail.
        Returns YouTube video ID on success.
        """
        ctx = ctx or self.ctx
        tags = tags or []

        if not self.youtube:
            success = self.authenticate(ctx)
            if not success:
                return None

        # Format tags back into hashtags and append them to the description for SEO
        # Ensure #shorts is always present and prioritized at the front
        clean_tags = [t.lower() for t in tags]
        if "shorts" not in clean_tags:
            clean_tags.insert(0, "shorts")
        else:
            clean_tags.remove("shorts")
            clean_tags.insert(0, "shorts")
            
        # Randomize hashtag count (5-9) — always exactly 8 is a bot signal
        hashtag_count = random.randint(5, 9)
        hashtags_str = " ".join([f"#{t}" for t in clean_tags[:hashtag_count]])
        full_description = f"{description}\n\n{hashtags_str}"

        category_id = ctx.youtube_category_id if ctx is not None else YOUTUBE_CATEGORY_ID
        body = {
            "snippet": {
                "title": title[:100],
                "description": full_description[:5000],
                "tags": tags[:30],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            }
        }

        if not os.path.exists(video_path):
            print(f"[YouTube] [ERROR] Video file not found: {video_path}")
            return None

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5   # 5MB chunks
        )

        try:
            print(f"[YouTube] Uploading: {title}")
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    print(f"[YouTube] Upload progress: {pct}%")

            video_id = response["id"]
            print(f"[YouTube] Uploaded! https://youtube.com/shorts/{video_id}")

            # Set thumbnail in an isolated try-except so thumbnail rejection (e.g. unverified phone number)
            # never masks a successful video upload or causes duplicate uploads.
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    self.youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail_path)
                    ).execute()
                    print("[YouTube] Thumbnail set successfully.")
                except HttpError as thumb_err:
                    if thumb_err.resp.status == 403:
                        print(
                            f"[YouTube] [INFO] Custom thumbnail skipped: Channel requires phone verification in YouTube Studio "
                            f"(Settings -> Channel -> Feature eligibility -> Intermediate features). Video remains successfully published."
                        )
                    else:
                        print(f"[YouTube] [WARNING] Failed to set custom thumbnail ({thumb_err}). Video remains successfully published.")
                except Exception as thumb_err:
                    print(f"[YouTube] [WARNING] Failed to set custom thumbnail ({thumb_err}). Video remains successfully published.")

            return video_id

        except HttpError as e:
            # ── Quota exhaustion: catch explicitly so pipeline can handle retry ──
            if e.resp.status == 403 and b"quotaExceeded" in e.content:
                channel_name = ctx.channel_name if ctx is not None else os.environ.get("ACTIVE_CHANNEL", "unknown")
                print(f"[YouTube] [ERROR] QUOTA EXHAUSTED for project. Daily limit reached.")
                from core.notifier import send_message as _tg
                _tg(
                    f"🚫 *YouTube API Quota Exhausted* — {channel_name}\n"
                    f"Daily 10,000-unit limit hit. Upload skipped for today.\n\n"
                    f"📋 *Action Required:* Apply for a quota increase at:\n"
                    f"`console.cloud.google.com → APIs → YouTube Data API v3 → Quotas → Request increase`\n\n"
                    f"The rendered video is saved and will be retried at the next scheduled run."
                )
                # Return sentinel so run_pipeline.py keeps the files for tomorrow's retry
                return "QUOTA_EXHAUSTED"
            print(f"[YouTube] Upload failed: {e}")
            return None
