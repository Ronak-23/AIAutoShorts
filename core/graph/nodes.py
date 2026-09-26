"""
core/graph/nodes.py
===================
Implementation of pure LangGraph nodes for each stage of the AutoReel
video production pipeline.
"""

import os
import sys
import json
import time
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

from core.graph.state import VideoProductionState
from core.channel_context import ChannelContext
from core.experiment_engine import ExperimentEngine
from core.trend_fetcher import TrendFetcher
from core.script_generator import ScriptGenerator
from core.voiceover import VoiceoverGenerator
from core.video_clipper import VideoClipper
from core.video_assembler import VideoAssembler
from core.youtube_uploader import YouTubeUploader
from core.notifier import send_message
from core.agents.legal import LegalAgent
from core.agents.quality_control import QualityControlAgent
from core.agents.thumbnail_designer import ThumbnailDesigner
from core.agents.music_director import MusicDirectorAgent
from core.agents.video_quality_reviewer import VideoQualityReviewer
from config.settings import (
    LOG_DIR, OUTPUT_DIR, THUMBNAIL_DIR,
    AUTO_POST_YOUTUBE, QUALITY_SCORE_THRESHOLD,
    get_video_encoder_args, MIN_DISK_SPACE_GB
)


def _log(state: VideoProductionState, msg: str, node: str = None) -> None:
    run_id = state.get("run_id", "init")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [AIAutoShorts] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode("ascii"), flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        with open(os.path.join(LOG_DIR, "pipeline.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

    try:
        from core.db.repository import record_pipeline_event
        record_pipeline_event(run_id=run_id, event_type="log", node_name=node or state.get("current_node"), message=msg)
    except Exception:
        pass


def _get_ctx(state: VideoProductionState) -> ChannelContext:
    channel_name = state.get("channel_name") or "demo_channel"
    user_id = state.get("user_id")
    config_dict = state.get("channel_config")
    ctx = ChannelContext(channel_identifier=channel_name, user_id=user_id, config_dict=config_dict)
    from core.ai_client import set_current_context
    set_current_context(ctx)
    return ctx


# ─── Node 0: Pre-Flight & Setup ───────────────────────────────────────────────

def init_pipeline_node(state: VideoProductionState) -> Dict[str, Any]:
    """Validates disk space, loads channel context, and selects A/B test recipe."""
    run_id = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
    channel_name = state.get("channel_name") or os.environ.get("ACTIVE_CHANNEL", "demo_channel")
    ctx = _get_ctx(state)

    _log(state, f"=== Initializing Pipeline Run: {run_id} | Channel: {ctx.display_name} ===")

    # Check disk space
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    free_gb = shutil.disk_usage(OUTPUT_DIR).free / (1024 ** 3)
    if free_gb < MIN_DISK_SPACE_GB:
        err_msg = f"Insufficient disk space: {free_gb:.1f}GB free (need >= {MIN_DISK_SPACE_GB}GB)"
        _log(state, err_msg)
        return {
            "run_id": run_id,
            "channel_name": channel_name,
            "channel_display_name": ctx.display_name,
            "channel_config": ctx._data if hasattr(ctx, "_data") else {},
            "status": "failed",
            "error": err_msg,
        }

    # Generate A/B recipe (locking topic to custom_topic if provided)
    custom_topic = None
    if state.get("story") and state["story"].get("title"):
        custom_topic = state["story"]["title"]
    elif state.get("custom_topic"):
        custom_topic = state.get("custom_topic")

    engine = ExperimentEngine(ctx=ctx)
    recipe = state.get("recipe") or engine.generate_recipe(custom_topic=custom_topic)
    _log(state, f"Experiment Recipe selected: {json.dumps(recipe)}")

    return {
        "run_id": run_id,
        "channel_name": channel_name,
        "channel_display_name": ctx.display_name,
        "channel_config": ctx._data if hasattr(ctx, "_data") else {},
        "recipe": recipe,
        "status": "initialized",
        "script_retry_count": 0,
        "max_script_retries": state.get("max_script_retries", 3),
        "story_swap_count": 0,
        "auto_post_youtube": state.get("auto_post_youtube", AUTO_POST_YOUTUBE),
        "execution_manifest": {},
    }


# ─── Node 1: Trend Discovery ──────────────────────────────────────────────────

def scout_trend_node(state: VideoProductionState) -> Dict[str, Any]:
    """Scouts trending stories and research angles matching channel profile."""
    if state.get("story"):
        _log(state, f"Using pre-provided story: {state['story'].get('title')}")
        return {"status": "story_ready"}

    ctx = _get_ctx(state)
    recipe = state.get("recipe", {})
    _log(state, "Fetching trending story from RSS & Google Trends...")

    fetcher = TrendFetcher(ctx=ctx)
    story = fetcher.get_todays_story(recipe=recipe)
    _log(state, f"Discovered Story: {story.get('title')} (Angle: {story.get('angle', 'N/A')})")

    return {
        "story": story,
        "status": "story_discovered"
    }


# ─── Node 2: Script Generation ────────────────────────────────────────────────

def scriptwriter_node(state: VideoProductionState) -> Dict[str, Any]:
    """Generates viral 3-act script with pattern interrupts, hooks, and SSML tags."""
    ctx = _get_ctx(state)
    story = state["story"]
    recipe = state.get("recipe", {})
    correction_feedback = state.get("correction_feedback")
    retry_count = state.get("script_retry_count", 0)

    _log(state, f"Generating script (Attempt {retry_count + 1})...")
    if correction_feedback:
        _log(state, f"Applying feedback: {correction_feedback[:100]}...")

    script_gen = ScriptGenerator()
    try:
        script = script_gen.generate(story, recipe, correction_feedback=correction_feedback, ctx=ctx)
        _log(state, f"Script generated successfully. Title: '{script.get('title')}'")
        return {
            "script": script,
            "scenes": script.get("scenes", []),
            "script_retry_count": retry_count + 1,
            "status": "script_generated"
        }
    except Exception as e:
        _log(state, f"Script generation error: {e}")
        return {
            "script_retry_count": retry_count + 1,
            "error": str(e),
            "status": "script_generation_failed"
        }


# ─── Node 2.1: Legal Compliance Gate ──────────────────────────────────────────

def legal_check_node(state: VideoProductionState) -> Dict[str, Any]:
    """Evaluates copyright and community guidelines safety."""
    ctx = _get_ctx(state)
    script = state.get("script", {})
    full_script = script.get("full_script", "")

    _log(state, "Legal Agent reviewing script for YouTube compliance...")
    legal = LegalAgent(ctx=ctx)
    legal_check = legal.assess_risk(full_script)

    is_safe = legal_check.get("is_safe", True)
    reason = legal_check.get("reason", "Passed compliance.")
    _log(state, f"Legal check: safe={is_safe} | Reason: {reason}")

    return {
        "legal_checked": True,
        "legal_safe": is_safe,
        "legal_reason": reason,
    }


# ─── Node 2.2: Creative QC Gate ───────────────────────────────────────────────

def quality_control_node(state: VideoProductionState) -> Dict[str, Any]:
    """Evaluates viral retention score, hook power, and host personality."""
    ctx = _get_ctx(state)
    script = state.get("script", {})
    title = script.get("title", "")
    full_script = script.get("full_script", "")

    _log(state, "Creative QC Agent evaluating hook, rhythm, and viral angle...")
    qc = QualityControlAgent(ctx=ctx)
    qc_res = qc.evaluate(title, full_script)

    approved = qc_res.get("approved", True)
    feedback = qc_res.get("feedback", "Approved")

    fix_map = {
        "Hook Power": "Rewrite the opening 1-2 sentences. Start mid-conflict, mid-drama or mid-shock. No warm-up phrases allowed.",
        "Emotional Category": "Lock the entire script into ONE emotional lens: Drama, Money, Fear, Mistakes, Secrets, or Conflict.",
        "Angle Surprise": "The angle is too obvious. Find the CONTRARIAN or UNEXPECTED perspective on this story.",
        "Host Personality": "Rewrite completely in the channel's specific host voice and persona with opinionated urgency.",
        "Human Rhythm": "The script reads like a list of facts. Rewrite using natural spoken transitions and varying sentence lengths.",
    }
    specific_fix = "Rewrite with stronger personality, a more surprising angle, and better emotional hook."
    for criteria_key, fix_instruction in fix_map.items():
        if criteria_key.lower() in feedback.lower():
            specific_fix = fix_instruction
            break

    correction_feedback = None
    if not approved:
        correction_feedback = f"- [CREATIVE QC REVISION] {feedback}\n  Fix: {specific_fix}"
        _log(state, f"QC Rejected script: {feedback}")
    else:
        _log(state, f"QC Approved script: {feedback}")

    return {
        "qc_approved": approved,
        "qc_score": qc_res.get("score", 95.0 if approved else 50.0),
        "qc_feedback": feedback,
        "correction_feedback": correction_feedback,
    }


# ─── Node 3: Voiceover & Subtitles ────────────────────────────────────────────

def voiceover_node(state: VideoProductionState) -> Dict[str, Any]:
    """Synthesizes neural voiceover and generates word-level ASS subtitles."""
    ctx = _get_ctx(state)
    script = state["script"]
    recipe = state.get("recipe", {})
    run_id = state["run_id"]

    _log(state, "Generating Neural Voiceover + ASS Karaoke Subtitles...")
    voice_gen = VoiceoverGenerator()
    audio_path, voice_actuals = voice_gen.generate(
        script=script,
        filename=f"{run_id}_voice.mp3",
        recipe=recipe,
        ctx=ctx
    )
    _log(state, f"Voiceover complete: {audio_path}")

    return {
        "audio_path": audio_path,
        "voice_actuals": voice_actuals,
    }


# ─── Node 4: Visual Retrieval & B-Roll ────────────────────────────────────────

def visual_curator_node(state: VideoProductionState) -> Dict[str, Any]:
    """Downloads HD vertical stock clips and images matching scene queries."""
    ctx = _get_ctx(state)
    script = state["script"]
    recipe = state.get("recipe", {})
    run_id = state["run_id"]

    _log(state, "Visual Curator retrieving vertical stock footage...")
    clipper = VideoClipper(ctx=ctx)
    bg_clip, overlays = clipper.get_clip_for_story(
        script,
        run_id,
        recipe=recipe,
        log_callback=lambda msg: _log(state, msg)
    )
    _log(state, f"Retrieved {len(overlays)} visual clips.")

    return {
        "broll_clips": overlays,
        "bg_clip": bg_clip,
    }


# ─── Node 4.1: Dynamic Music Director ─────────────────────────────────────────

def music_director_node(state: VideoProductionState) -> Dict[str, Any]:
    """Scores background music matching script mood and sets dynamic ducking."""
    ctx = _get_ctx(state)
    script = state["script"]
    recipe = state.get("recipe", {})
    run_id = state["run_id"]

    _log(state, "Music Director scoring dynamic background audio...")
    music_agent = MusicDirectorAgent(ctx=ctx)
    bgm_path = music_agent.score_video(script, run_id, recipe=recipe)
    mood = getattr(music_agent, "last_mood", "suspense")
    track_id = getattr(music_agent, "last_track_id", "fallback")
    _log(state, f"Selected BGM: {bgm_path} (Mood: {mood})")

    return {
        "bgm_path": bgm_path,
        "bgm_mood": mood,
        "bgm_track_id": track_id,
    }


# ─── Node 5.1: Thumbnail Designer ─────────────────────────────────────────────

def thumbnail_node(state: VideoProductionState) -> Dict[str, Any]:
    """Generates high-CTR AI thumbnail graphic and custom overlay."""
    ctx = _get_ctx(state)
    script = state["script"]
    recipe = state.get("recipe", {})
    run_id = state["run_id"]
    overlays = state.get("broll_clips", [])

    _log(state, "Generating high-CTR thumbnail...")
    try:
        designer = ThumbnailDesigner(ctx=ctx)
        ai_thumbnail, thumb_actuals = designer.generate(
            script["title"],
            script["full_script"],
            run_id,
            thumbnail_text=script.get("thumbnail_text"),
            thumb_color=recipe.get("thumbnail_color", "Blue"),
            first_clip_path=overlays[0] if (overlays and len(overlays) > 0) else None,
            all_clip_paths=overlays if overlays else None,
            visual_prompt=script.get("thumbnail_visual_prompt")
        )
        _log(state, f"Thumbnail generated: {ai_thumbnail}")
        return {
            "thumbnail_path": ai_thumbnail,
            "thumbnail_actuals": thumb_actuals,
        }
    except Exception as e:
        _log(state, f"Thumbnail generation failed (will use video frame): {e}")
        return {
            "thumbnail_path": None,
            "thumbnail_actuals": {},
        }


# ─── Node 5: Video Assembly ───────────────────────────────────────────────────

def _inject_thumb_frame(video_path: str, thumbnail_path: str, run_id: str) -> bool:
    if not thumbnail_path or not os.path.exists(video_path) or not os.path.exists(thumbnail_path):
        return False
    base, ext = os.path.splitext(video_path)
    temp_clip = f"{base}_thumb_clip{ext}"
    concat_list = f"{base}_concat_list.txt"
    injected_out = f"{base}_injected{ext}"
    try:
        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", thumbnail_path,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "0.2", "-vf", "scale=1080:1920,setsar=1",
            "-r", "30", "-c:a", "aac", "-b:a", "192k",
            "-ar", "44100", "-ac", "2"
        ] + get_video_encoder_args() + [temp_clip]
        subprocess.run(cmd_clip, capture_output=True, check=True)

        with open(concat_list, "w", encoding="utf-8") as f:
            f.write(f"file '{os.path.abspath(video_path).replace(os.sep, '/')}'\n")
            f.write(f"file '{os.path.abspath(temp_clip).replace(os.sep, '/')}'\n")

        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", injected_out],
                       capture_output=True, check=True)

        from core.utils import safe_atomic_replace
        safe_atomic_replace(injected_out, video_path)
        return True
    except Exception:
        return False
    finally:
        for fp in [temp_clip, concat_list, injected_out]:
            if os.path.exists(fp):
                try: os.remove(fp)
                except Exception: pass


def cleanup_intermediate_assets(
    run_id: str,
    final_video_path: str,
    thumbnail_path: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None
) -> int:
    """
    Deletes all temporary intermediate video, audio, and subtitle assets created
    during production of run_id, strictly retaining only the final video and thumbnail.
    """
    cleaned = 0
    protected_paths = set()
    if final_video_path:
        protected_paths.add(os.path.abspath(final_video_path).lower())
    if thumbnail_path:
        protected_paths.add(os.path.abspath(thumbnail_path).lower())

    # 1. State explicit files (broll_clips, audio_path, bgm_path)
    if state:
        for clip in state.get("broll_clips", []):
            if clip and os.path.exists(clip):
                if os.path.abspath(clip).lower() not in protected_paths:
                    try:
                        os.remove(clip)
                        cleaned += 1
                    except Exception:
                        pass
        for path_key in ["audio_path", "bgm_path"]:
            p = state.get(path_key)
            if p and os.path.exists(p) and os.path.abspath(p).lower() not in protected_paths:
                try:
                    os.remove(p)
                    cleaned += 1
                except Exception:
                    pass

    # 2. Clips subfolder: output/videos/clips/{run_id}_*
    clips_dir = os.path.join(OUTPUT_DIR, "clips")
    if os.path.exists(clips_dir):
        for fname in os.listdir(clips_dir):
            if fname.startswith(run_id):
                fp = os.path.join(clips_dir, fname)
                if os.path.abspath(fp).lower() not in protected_paths:
                    try:
                        os.remove(fp)
                        cleaned += 1
                    except Exception:
                        pass

    # 3. Main OUTPUT_DIR files starting with run_id (raw clips, merged video, voice/bgm files, concat lists)
    if os.path.exists(OUTPUT_DIR):
        for fname in os.listdir(OUTPUT_DIR):
            if fname.startswith(run_id):
                fp = os.path.join(OUTPUT_DIR, fname)
                if os.path.abspath(fp).lower() not in protected_paths:
                    try:
                        if os.path.isfile(fp):
                            os.remove(fp)
                            cleaned += 1
                    except Exception:
                        pass

    # 4. Old intermediate thumbnail files starting with run_id in THUMBNAIL_DIR
    if os.path.exists(THUMBNAIL_DIR):
        for fname in os.listdir(THUMBNAIL_DIR):
            if fname.startswith(run_id):
                fp = os.path.join(THUMBNAIL_DIR, fname)
                if os.path.abspath(fp).lower() not in protected_paths:
                    try:
                        if os.path.isfile(fp):
                            os.remove(fp)
                            cleaned += 1
                    except Exception:
                        pass

    return cleaned


def video_assembler_node(state: VideoProductionState) -> Dict[str, Any]:
    """Renders 1080x1920 60fps MP4 with dynamic subtitles, audio ducking, and mastered audio."""
    from core.utils import title_to_snake_case
    ctx = _get_ctx(state)
    script = state.get("script", {})
    recipe = state.get("recipe", {})
    run_id = state.get("run_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
    audio_path = state.get("audio_path")
    broll_clips = state.get("broll_clips", [])
    bgm_path = state.get("bgm_path")
    thumbnail_path = state.get("thumbnail_path")

    # Defensive fallback for audio_path
    if not audio_path or not os.path.exists(audio_path):
        _log(state, "Audio path missing or pending. Generating voiceover before final assembly...")
        voice_gen = VoiceoverGenerator()
        audio_path, _ = voice_gen.generate(
            script=script,
            filename=f"{run_id}_voice.mp3",
            recipe=recipe,
            ctx=ctx
        )

    # Defensive fallback for broll_clips
    if not broll_clips:
        _log(state, "B-roll clips pending or empty. Sourcing visuals before assembly...")
        clipper = VideoClipper(ctx=ctx)
        _, broll_clips = clipper.get_clip_for_story(script, run_id, recipe=recipe)

    # Derive clean snake_case filename from video title
    title = script.get("title") or (state.get("story") or {}).get("title") or "short_video"
    snake_title = title_to_snake_case(title)
    final_filename = f"{snake_title}.mp4"
    target_path = os.path.join(OUTPUT_DIR, final_filename)
    if os.path.exists(target_path):
        # Prevent collisions across identical titles or re-runs
        final_filename = f"{snake_title}_{run_id[-4:]}.mp4"

    _log(state, f"Assembling final video via FFmpeg engine ({len(broll_clips)} visual clips) as '{final_filename}'...")
    assembler = VideoAssembler(ctx=ctx)
    output = assembler.assemble(
        broll_clips, audio_path, script, run_id, recipe, bgm_path=bgm_path, final_filename=final_filename
    )
    final_video = output.get("video")

    if not final_video or not os.path.exists(final_video):
        raise RuntimeError(f"Video assembly produced missing file: {final_video}")

    # Harmonize thumbnail name to match snake_case title
    if thumbnail_path and os.path.exists(thumbnail_path):
        thumb_base = os.path.splitext(final_filename)[0]
        target_thumb = os.path.join(THUMBNAIL_DIR, f"{thumb_base}.jpg")
        if os.path.abspath(thumbnail_path) != os.path.abspath(target_thumb):
            try:
                shutil.copy2(thumbnail_path, target_thumb)
                thumbnail_path = target_thumb
            except Exception as e:
                _log(state, f"Note: Could not sync thumbnail name: {e}")

    # Inject thumbnail frame if present
    if thumbnail_path and os.path.exists(thumbnail_path):
        _inject_thumb_frame(final_video, thumbnail_path, run_id)

    # Check duration
    duration = 55.0
    try:
        dur_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", final_video]
        duration = float(subprocess.check_output(dur_cmd).decode().strip())
        _log(state, f"Final video duration: {duration:.2f}s")
    except Exception:
        pass

    # Purge all intermediate generation media (clips, merged video, voice/bgm audio)
    cleaned_count = cleanup_intermediate_assets(
        run_id=run_id,
        final_video_path=final_video,
        thumbnail_path=thumbnail_path,
        state=state
    )
    _log(state, f"Cleaned up {cleaned_count} intermediate generation media files. Retained final video & thumbnail.")

    return {
        "final_video_path": final_video,
        "thumbnail_path": thumbnail_path,
        "video_duration": duration,
        "status": "video_assembled",
    }


# ─── Node 5.2 / 5.3: Video QC ─────────────────────────────────────────────────

def video_qc_node(state: VideoProductionState) -> Dict[str, Any]:
    """Executes AI visual and text quality review on compiled MP4."""
    ctx = _get_ctx(state)
    run_id = state["run_id"]
    final_video = state.get("final_video_path")

    _log(state, "Running Video Quality Review Engine...")
    try:
        reviewer = VideoQualityReviewer(ctx=ctx)
        review_res = reviewer.evaluate(run_id, final_video)
        score = review_res.get("final_score", 100)
        approved = review_res.get("upload_recommended", True)
        reason = review_res.get("rejection_reason", "Passed video inspection.")
    except Exception as e:
        _log(state, f"Video QC review error (auto-approving to avoid blockage): {e}")
        score = 100
        approved = True
        reason = "Auto-approved."

    _log(state, f"Video QC Result: score={score} | approved={approved} | {reason}")
    return {
        "video_qc_score": score,
        "video_qc_approved": approved,
        "video_qc_feedback": reason,
    }


# ─── Node 6: YouTube Publisher ────────────────────────────────────────────────

def youtube_publisher_node(state: VideoProductionState) -> Dict[str, Any]:
    """Uploads video to YouTube and records experiment metrics in SQLite database."""
    ctx = _get_ctx(state)
    run_id = state["run_id"]
    script = state.get("script", {})
    final_video = state.get("final_video_path")
    thumbnail_path = state.get("thumbnail_path")
    auto_post = state.get("auto_post_youtube", False)

    if not auto_post:
        _log(state, f"[DRY-RUN / AUTO_POST=False] Video saved to: {final_video}. Skipping YouTube upload.")
        return {
            "youtube_video_id": None,
            "status": "completed_offline",
        }

    _log(state, "Uploading video to YouTube Data API v3...")
    try:
        uploader = YouTubeUploader(ctx=ctx)
        upload_result = uploader.upload(
            final_video,
            title=script.get("title", "AIAutoShorts Video"),
            description=script.get("description", ""),
            tags=script.get("hashtags", []),
            thumbnail_path=thumbnail_path,
            run_id=run_id
        )
        if not upload_result or upload_result == "QUOTA_EXHAUSTED":
            err_msg = "YouTube upload failed: channel not authenticated, quota exhausted, or upload error."
            _log(state, err_msg)
            return {
                "youtube_video_id": None,
                "status": "upload_failed",
                "error": err_msg,
            }

        video_id = upload_result.get("id") if isinstance(upload_result, dict) else str(upload_result)
        _log(state, f"Successfully published to YouTube! Video ID: {video_id}")
        send_message(
            f"🎬 *New Video Uploaded — {ctx.display_name}*\n"
            f"*Title:* {script.get('title')}\n"
            f"*Link:* https://youtube.com/shorts/{video_id}"
        )
        return {
            "youtube_video_id": video_id,
            "status": "published",
        }
    except Exception as e:
        _log(state, f"YouTube upload failed: {e}")
        return {
            "error": f"YouTube upload error: {e}",
            "status": "upload_failed",
        }
