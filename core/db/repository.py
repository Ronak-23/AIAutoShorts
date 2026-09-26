"""
AIAutoShorts Database Repository
================================
Thread-safe, transaction-protected SQLite repository layer.
Implements exponential-backoff write retries, WAL concurrency,
and normalized data operations.
"""

import sqlite3
import os
import json
import time
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from config.settings import DB_PATH, LOG_DIR
from core.db.schema import DDL_STATEMENTS


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured for concurrent multi-tenant usage."""
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def _retry_write(conn: sqlite3.Connection, sql: str, params: tuple = (), max_retries: int = 3) -> bool:
    """Executes a write query with exponential backoff on database lock contention."""
    for attempt in range(max_retries):
        try:
            conn.execute(sql, params)
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                wait = (2 ** attempt) * 0.5
                time.sleep(wait)
            else:
                raise
    return False


def init_db():
    """Executes all schema migrations and ensures database tables and indexes exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for statement in DDL_STATEMENTS:
            cursor.execute(statement)

        # Dynamic migration for YouTube OAuth columns in channels table
        try:
            cursor.execute("PRAGMA table_info(channels)")
            existing_cols = [row["name"] for row in cursor.fetchall()]
            if "youtube_token_encrypted" not in existing_cols:
                cursor.execute("ALTER TABLE channels ADD COLUMN youtube_token_encrypted TEXT")
            if "youtube_channel_title" not in existing_cols:
                cursor.execute("ALTER TABLE channels ADD COLUMN youtube_channel_title TEXT")
            if "youtube_authenticated_at" not in existing_cols:
                cursor.execute("ALTER TABLE channels ADD COLUMN youtube_authenticated_at DATETIME")
        except Exception as e:
            print(f"[DB] Notice: channels table column check: {e}")

        # Monthly VACUUM check
        try:
            cursor.execute("SELECT value FROM _meta WHERE key = 'last_vacuum'")
            row = cursor.fetchone()
            last_vacuum_str = row["value"] if row else "2000-01-01T00:00:00"
            last_vacuum = datetime.fromisoformat(last_vacuum_str)
            if (datetime.now() - last_vacuum).days >= 30:
                conn.execute("VACUUM;")
                cursor.execute(
                    "INSERT OR REPLACE INTO _meta (key, value) VALUES ('last_vacuum', ?)",
                    (datetime.now().isoformat(),)
                )
        except Exception:
            pass

        conn.commit()
    finally:
        conn.close()


# ── User Operations ──────────────────────────────────────────────────────────

def create_user(user_id: str, username: str, hashed_password: str, email: Optional[str] = None, role: str = "user") -> Dict[str, Any]:
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        _retry_write(
            conn,
            "INSERT INTO users (id, username, email, hashed_password, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username.strip().lower(), email, hashed_password, role, now, now)
        )
        return {"id": user_id, "username": username, "email": email, "role": role, "created_at": now}
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── Channel Operations ───────────────────────────────────────────────────────

def create_channel(channel_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        channel_id = channel_data.get("id") or str(int(time.time() * 1000))
        name = channel_data["name"].strip().lower()
        tags = channel_data.get("tags")
        if not tags or not isinstance(tags, list):
            tags = ["shorts", "viral"]
        tags_json = json.dumps(tags)

        rss_feeds = channel_data.get("rss_feeds")
        if not rss_feeds or not isinstance(rss_feeds, list):
            rss_feeds = ["https://techcrunch.com/feed/"]
        rss_json = json.dumps(rss_feeds)

        vocab = channel_data.get("vocabulary")
        if not vocab or not isinstance(vocab, list):
            vocab = []
        vocab_json = json.dumps(vocab)

        _retry_write(
            conn,
            """
            INSERT INTO channels (
                id, user_id, name, display_name, niche, tone, target_audience,
                voice_provider, voice_name, voice_rate, voice_pitch,
                video_duration_seconds, min_words, max_words, fps,
                visual_mode, stock_provider, default_bgm_mood, bgm_volume,
                caption_style, is_active, youtube_channel_id, youtube_category_id,
                tags_json, rss_feeds_json, vocabulary_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                channel_id,
                channel_data["user_id"],
                name,
                channel_data.get("display_name", name.title()),
                channel_data.get("niche", "Technology and AI Innovations"),
                channel_data.get("tone", "Engaging, authoritative, fast-paced"),
                channel_data.get("target_audience", "General audience"),
                channel_data.get("voice_provider", "edge"),
                channel_data.get("voice_name", "en-US-ChristopherNeural"),
                channel_data.get("voice_rate", "+8%"),
                channel_data.get("voice_pitch", "+0Hz"),
                int(channel_data.get("video_duration_seconds", 55)),
                int(channel_data.get("min_words", 110)),
                int(channel_data.get("max_words", 140)),
                int(channel_data.get("fps", 30)),
                channel_data.get("visual_mode", "stock_plus_wiki"),
                channel_data.get("stock_provider", "pexels"),
                channel_data.get("default_bgm_mood", "suspense"),
                float(channel_data.get("bgm_volume", 0.22)),
                channel_data.get("caption_style", "yellow_glow"),
                1 if channel_data.get("is_active", True) else 0,
                channel_data.get("youtube_channel_id", ""),
                channel_data.get("youtube_category_id", "28"),
                tags_json,
                rss_json,
                vocab_json,
                now,
                now
            )
        )
        return get_channel_by_id(channel_id)
    finally:
        conn.close()


def _parse_channel_row(d: Dict[str, Any]) -> Dict[str, Any]:
    def _safe_json_list(raw, default):
        if not raw or raw == "null":
            return list(default)
        try:
            val = json.loads(raw)
            return val if isinstance(val, list) else list(default)
        except Exception:
            return list(default)

    d["tags"] = _safe_json_list(d.get("tags_json"), ["shorts", "viral"])
    d["rss_feeds"] = _safe_json_list(d.get("rss_feeds_json"), ["https://techcrunch.com/feed/"])
    d["vocabulary"] = _safe_json_list(d.get("vocabulary_json"), [])
    d["is_active"] = bool(d.get("is_active", 1))
    d["has_youtube_auth"] = bool(d.get("youtube_token_encrypted"))
    d["youtube_channel_title"] = d.get("youtube_channel_title") or ""
    d["youtube_authenticated_at"] = d.get("youtube_authenticated_at")
    return d


def get_channel_by_id(channel_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _parse_channel_row(dict(row))
    finally:
        conn.close()


def get_channel_by_name(user_id: str, channel_name: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE user_id = ? AND name = ?", (user_id, channel_name.strip().lower()))
        row = cursor.fetchone()
        if not row:
            return None
        return _parse_channel_row(dict(row))
    finally:
        conn.close()


def list_channels(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM channels WHERE user_id = ? ORDER BY created_at ASC", (user_id,))
        else:
            cursor.execute("SELECT * FROM channels ORDER BY created_at ASC")
        rows = cursor.fetchall()
        return [_parse_channel_row(dict(row)) for row in rows]
    finally:
        conn.close()


def update_channel(channel_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        allowed = [
            "display_name", "niche", "tone", "target_audience",
            "voice_provider", "voice_name", "voice_rate", "voice_pitch",
            "video_duration_seconds", "min_words", "max_words", "fps",
            "visual_mode", "stock_provider", "default_bgm_mood", "bgm_volume",
            "caption_style", "is_active", "youtube_channel_id", "youtube_category_id",
            "youtube_token_encrypted", "youtube_channel_title", "youtube_authenticated_at"
        ]
        set_clauses = []
        params = []
        for k, v in updates.items():
            if k in allowed:
                set_clauses.append(f"{k} = ?")
                params.append(v)
            elif k == "tags":
                set_clauses.append("tags_json = ?")
                params.append(json.dumps(v if isinstance(v, list) else ["shorts", "viral"]))
            elif k == "rss_feeds":
                set_clauses.append("rss_feeds_json = ?")
                params.append(json.dumps(v if isinstance(v, list) else ["https://techcrunch.com/feed/"]))
            elif k == "vocabulary":
                set_clauses.append("vocabulary_json = ?")
                params.append(json.dumps(v if isinstance(v, list) else []))

        if not set_clauses:
            return get_channel_by_id(channel_id)

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(channel_id)

        sql = f"UPDATE channels SET {', '.join(set_clauses)} WHERE id = ?"
        _retry_write(conn, sql, tuple(params))
        return get_channel_by_id(channel_id)
    finally:
        conn.close()


def save_channel_youtube_token(channel_id: str, encrypted_token: str, channel_title: str = "", youtube_channel_id: str = "") -> bool:
    """Saves encrypted OAuth token and channel metadata to the channel record."""
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        updates = ["youtube_token_encrypted = ?", "youtube_authenticated_at = ?", "updated_at = ?"]
        params = [encrypted_token, now, now]
        if channel_title:
            updates.append("youtube_channel_title = ?")
            params.append(channel_title)
        if youtube_channel_id:
            updates.append("youtube_channel_id = ?")
            params.append(youtube_channel_id)
        params.append(channel_id)
        sql = f"UPDATE channels SET {', '.join(updates)} WHERE id = ?"
        return _retry_write(conn, sql, tuple(params))
    finally:
        conn.close()


def delete_channel_youtube_token(channel_id: str) -> bool:
    """Removes stored YouTube token and resets authentication status for a channel."""
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        sql = """
            UPDATE channels 
            SET youtube_token_encrypted = NULL, 
                youtube_channel_title = NULL, 
                youtube_authenticated_at = NULL,
                updated_at = ? 
            WHERE id = ?
        """
        return _retry_write(conn, sql, (now, channel_id))
    finally:
        conn.close()


def delete_channel(channel_id: str) -> bool:
    conn = get_connection()
    try:
        _retry_write(conn, "DELETE FROM channels WHERE id = ?", (channel_id,))
        return True
    finally:
        conn.close()


# ── Pipeline Run Operations ──────────────────────────────────────────────────

def create_pipeline_run(run_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        run_id = run_data["id"]
        _retry_write(
            conn,
            """
            INSERT INTO pipeline_runs (
                id, user_id, channel_id, channel_name, status,
                progress_percentage, current_node, completed_nodes_json,
                custom_topic, auto_post_youtube, interrupt_before_publish,
                started_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                run_data["user_id"],
                run_data["channel_id"],
                run_data["channel_name"],
                run_data.get("status", "running"),
                run_data.get("progress_percentage", 5),
                run_data.get("current_node", "init_pipeline"),
                json.dumps(run_data.get("completed_nodes", [])),
                run_data.get("custom_topic"),
                1 if run_data.get("auto_post_youtube") else 0,
                1 if run_data.get("interrupt_before_publish") else 0,
                now,
                now,
                now
            )
        )
        return get_pipeline_run(run_id)
    finally:
        conn.close()


def update_pipeline_run(run_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        set_clauses = []
        params = []

        direct_keys = [
            "status", "progress_percentage", "current_node",
            "audio_path", "thumbnail_path", "final_video_path", "video_duration",
            "qc_approved", "qc_score", "qc_feedback",
            "video_qc_approved", "video_qc_score", "video_qc_feedback",
            "youtube_video_id", "error", "completed_at"
        ]

        for k in direct_keys:
            if k in updates:
                set_clauses.append(f"{k} = ?")
                params.append(updates[k])

        if "completed_nodes" in updates:
            set_clauses.append("completed_nodes_json = ?")
            params.append(json.dumps(updates["completed_nodes"]))
        if "story" in updates:
            set_clauses.append("story_json = ?")
            params.append(json.dumps(updates["story"]))
        if "script" in updates:
            set_clauses.append("script_json = ?")
            params.append(json.dumps(updates["script"]))
        if "scenes" in updates:
            set_clauses.append("scenes_json = ?")
            params.append(json.dumps(updates["scenes"]))

        if not set_clauses:
            return get_pipeline_run(run_id)

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(run_id)

        sql = f"UPDATE pipeline_runs SET {', '.join(set_clauses)} WHERE id = ?"
        _retry_write(conn, sql, tuple(params))
        return get_pipeline_run(run_id)
    finally:
        conn.close()


def get_pipeline_run(run_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["completed_nodes"] = json.loads(d.get("completed_nodes_json") or "[]")
        d["story"] = json.loads(d.get("story_json") or "{}") if d.get("story_json") else None
        d["script"] = json.loads(d.get("script_json") or "{}") if d.get("script_json") else None
        d["scenes"] = json.loads(d.get("scenes_json") or "[]") if d.get("scenes_json") else []
        d["auto_post_youtube"] = bool(d.get("auto_post_youtube", 0))
        d["interrupt_before_publish"] = bool(d.get("interrupt_before_publish", 0))
        return d
    finally:
        conn.close()


def get_pipeline_run_by_video_filename(filename: str) -> Optional[Dict[str, Any]]:
    """Retrieves the pipeline run that owns the given video filename."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM pipeline_runs 
            WHERE final_video_path LIKE '%' || ? 
               OR final_video_path = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (filename, filename)
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["completed_nodes"] = json.loads(d.get("completed_nodes_json") or "[]")
        d["story"] = json.loads(d.get("story_json") or "{}") if d.get("story_json") else None
        d["script"] = json.loads(d.get("script_json") or "{}") if d.get("script_json") else None
        d["scenes"] = json.loads(d.get("scenes_json") or "[]") if d.get("scenes_json") else []
        d["auto_post_youtube"] = bool(d.get("auto_post_youtube", 0))
        d["interrupt_before_publish"] = bool(d.get("interrupt_before_publish", 0))
        return d
    finally:
        conn.close()


def list_pipeline_runs(user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM pipeline_runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
        else:
            cursor.execute("SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["completed_nodes"] = json.loads(d.get("completed_nodes_json") or "[]")
            d["story"] = json.loads(d.get("story_json") or "{}") if d.get("story_json") else None
            d["script"] = json.loads(d.get("script_json") or "{}") if d.get("script_json") else None
            d["scenes"] = json.loads(d.get("scenes_json") or "[]") if d.get("scenes_json") else []
            d["auto_post_youtube"] = bool(d.get("auto_post_youtube", 0))
            d["interrupt_before_publish"] = bool(d.get("interrupt_before_publish", 0))
            results.append(d)
        return results
    finally:
        conn.close()


# ── Pipeline Events Operations ───────────────────────────────────────────────

def record_pipeline_event(run_id: str, event_type: str, node_name: Optional[str] = None, message: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        _retry_write(
            conn,
            "INSERT INTO pipeline_events (run_id, event_type, node_name, message, data_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, event_type, node_name, message, json.dumps(data) if data else None, now)
        )
    finally:
        conn.close()


def get_pipeline_events(run_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pipeline_events WHERE run_id = ? ORDER BY id ASC LIMIT ?", (run_id, limit))
        rows = cursor.fetchall()
        events = []
        for row in rows:
            ev = dict(row)
            ev["data"] = json.loads(ev.get("data_json") or "{}") if ev.get("data_json") else {}
            events.append(ev)
        return events
    finally:
        conn.close()


# ── Schedules Operations ─────────────────────────────────────────────────────

def create_schedule(sched_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        sched_id = sched_data.get("id") or str(int(time.time() * 1000))
        _retry_write(
            conn,
            """
            INSERT INTO schedules (
                id, user_id, channel_id, channel_name, frequency, time_of_day,
                auto_post_youtube, is_active, next_run_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sched_id,
                sched_data["user_id"],
                sched_data["channel_id"],
                sched_data["channel_name"],
                sched_data["frequency"],
                sched_data.get("time_of_day", "09:00"),
                1 if sched_data.get("auto_post_youtube") else 0,
                1 if sched_data.get("is_active", True) else 0,
                sched_data.get("next_run_at"),
                now,
                now
            )
        )
        return get_schedule(sched_id)
    finally:
        conn.close()


def get_schedule(schedule_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["auto_post_youtube"] = bool(d.get("auto_post_youtube", 0))
        d["is_active"] = bool(d.get("is_active", 1))
        return d
    finally:
        conn.close()


def list_schedules(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM schedules WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        else:
            cursor.execute("SELECT * FROM schedules ORDER BY created_at DESC")
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["auto_post_youtube"] = bool(d.get("auto_post_youtube", 0))
            d["is_active"] = bool(d.get("is_active", 1))
            results.append(d)
        return results
    finally:
        conn.close()


def list_due_schedules() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM schedules
            WHERE is_active = 1
              AND (next_run_at IS NULL OR next_run_at <= CURRENT_TIMESTAMP)
        """)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["auto_post_youtube"] = bool(d.get("auto_post_youtube", 0))
            d["is_active"] = bool(d.get("is_active", 1))
            results.append(d)
        return results
    finally:
        conn.close()


def update_schedule(schedule_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        set_clauses = []
        params = []
        for k in ["frequency", "time_of_day", "auto_post_youtube", "is_active", "last_run_at", "next_run_at", "last_run_id"]:
            if k in updates:
                set_clauses.append(f"{k} = ?")
                params.append(updates[k])
        if not set_clauses:
            return get_schedule(schedule_id)

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(schedule_id)

        sql = f"UPDATE schedules SET {', '.join(set_clauses)} WHERE id = ?"
        _retry_write(conn, sql, tuple(params))
        return get_schedule(schedule_id)
    finally:
        conn.close()


def delete_schedule(schedule_id: str) -> bool:
    conn = get_connection()
    try:
        _retry_write(conn, "DELETE FROM schedules WHERE id = ?", (schedule_id,))
        return True
    finally:
        conn.close()


# ── Seen Stories Deduplication ───────────────────────────────────────────────

def _title_hash(title: str) -> str:
    _stop = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at"}
    words = [w for w in title.lower().strip().split() if w not in _stop]
    return hashlib.md5(" ".join(words).encode("utf-8")).hexdigest()


def is_story_duplicate(channel_name: str, title: str, url: Optional[str] = None, lookback_days: int = 7) -> bool:
    h = _title_hash(title)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM seen_stories
            WHERE channel_name = ? AND title_hash = ?
              AND seen_at >= datetime('now', ?)
            LIMIT 1
        """, (channel_name, h, f"-{lookback_days} days"))
        if cursor.fetchone():
            return True
        if url:
            cursor.execute("""
                SELECT 1 FROM seen_stories
                WHERE channel_name = ? AND story_url = ?
                  AND seen_at >= datetime('now', ?)
                LIMIT 1
            """, (channel_name, url, f"-{lookback_days} days"))
            if cursor.fetchone():
                return True
        return False
    finally:
        conn.close()


def mark_story_seen(channel_name: str, title: str, url: Optional[str] = None):
    h = _title_hash(title)
    conn = get_connection()
    try:
        _retry_write(
            conn,
            "INSERT INTO seen_stories (channel_name, story_url, title_hash, title) VALUES (?, ?, ?, ?)",
            (channel_name, url or "", h, title[:500])
        )
    finally:
        conn.close()


def is_story_semantically_similar(channel_name: str, title: str, lookback_days: int = 3) -> bool:
    _stop = {
        "the","a","an","is","are","was","were","in","on","at","to","of",
        "and","or","for","by","it","its","has","had","have","been","this",
        "that","with","from","but","not","can","will","do","did","so","as","if"
    }
    def _sig_words(t: str) -> list:
        return [w.lower() for w in re.findall(r'[a-zA-Z]{3,}', t) if w.lower() not in _stop][:8]

    words = _sig_words(title)
    if len(words) < 3:
        return False

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title FROM seen_stories
            WHERE channel_name = ? AND seen_at >= datetime('now', ?)
        """, (channel_name, f"-{lookback_days} days"))
        for (existing,) in cursor.fetchall():
            if not existing:
                continue
            ex_words = _sig_words(existing)
            if len(ex_words) < 3:
                continue
            ratio = len(set(words) & set(ex_words)) / max(len(words), len(ex_words))
            if ratio >= 0.6:
                return True
        return False
    finally:
        conn.close()


# ── A/B Testing ──────────────────────────────────────────────────────────────

def save_ab_test(user_id: str, channel_name: str, video_id: str, title_a: str, title_b: str):
    conn = get_connection()
    try:
        _retry_write(
            conn,
            "INSERT INTO ab_tests (user_id, channel_name, video_id, title_a, title_b) VALUES (?, ?, ?, ?, ?)",
            (user_id, channel_name, video_id, title_a, title_b)
        )
    finally:
        conn.close()


def get_pending_ab_tests(min_age_hours: float = 8.0) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM ab_tests
            WHERE active = 1 AND created_at <= datetime('now', ?)
        """, (f"-{int(min_age_hours)} hours",))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def resolve_ab_test(test_id: int, switched: bool):
    conn = get_connection()
    try:
        _retry_write(
            conn,
            "UPDATE ab_tests SET active = 0, switched = ?, resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if switched else 0, test_id)
        )
    finally:
        conn.close()


# ── AI Review Operations ─────────────────────────────────────────────────────

def save_ai_review(review_dict: Dict[str, Any]):
    conn = get_connection()
    try:
        _retry_write(
            conn,
            """
            INSERT INTO ai_reviews (
                run_id, channel_name, attempt, overall_score, visual_score,
                audio_score, caption_score, flow_score, retention_dropoff_ts,
                watch_likelihood, upload_recommended, issues_json, fix_applied,
                skipped, skip_reason, summary, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_dict["run_id"],
                review_dict.get("channel_name", ""),
                review_dict.get("attempt", 1),
                review_dict.get("overall_score"),
                review_dict.get("visual_score"),
                review_dict.get("audio_score"),
                review_dict.get("caption_score"),
                review_dict.get("flow_score"),
                review_dict.get("retention_dropoff_ts"),
                review_dict.get("watch_likelihood"),
                1 if review_dict.get("upload_recommended", True) else 0,
                json.dumps(review_dict.get("issues", [])),
                1 if review_dict.get("fix_applied", False) else 0,
                1 if review_dict.get("skipped", False) else 0,
                review_dict.get("skip_reason"),
                review_dict.get("summary", ""),
                review_dict.get("raw_json", "")
            )
        )
    finally:
        conn.close()


# ── Legacy Experiments Compatibility ─────────────────────────────────────────

def save_experiment(run_id: str, user_id: str, video_id: str, parameters: dict, metrics: dict = None):
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        _retry_write(
            conn,
            """
            INSERT OR REPLACE INTO experiments (run_id, user_id, video_id, uploaded_at, parameters, metrics)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, user_id, video_id, now, json.dumps(parameters), json.dumps(metrics or {}))
        )
    finally:
        conn.close()


def list_experiments(user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM experiments WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT ?", (user_id, limit))
        else:
            cursor.execute("SELECT * FROM experiments ORDER BY uploaded_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["parameters"] = json.loads(d.get("parameters") or "{}")
            d["metrics"] = json.loads(d.get("metrics") or "{}")
            results.append(d)
        return results
    finally:
        conn.close()


# ─── User BYOK API Keys ───────────────────────────────────────────────────────

def save_user_api_key(
    user_id: Any = None,
    provider: Optional[str] = None,
    encrypted_key: Optional[bytes] = None,
    nonce: Optional[bytes] = None,
    tag: Optional[bytes] = None,
    key_preview: Optional[str] = None,
    key_alias: str = "Default"
) -> Dict[str, Any]:
    """Saves an encrypted user API key into SQLite."""
    if isinstance(user_id, dict):
        d = user_id
        user_id = d["user_id"]
        provider = d["provider"]
        encrypted_key = d["encrypted_key"]
        nonce = d["nonce"]
        tag = d["tag"]
        key_preview = d["key_preview"]
        key_alias = d.get("key_alias", "Default")

    conn = get_connection()
    try:
        key_id = f"key_{uuid.uuid4().hex[:12]}" if 'uuid' in globals() else f"key_{hashlib.md5(f'{user_id}:{provider}:{time.time()}'.encode()).hexdigest()[:12]}"
        now = datetime.now().isoformat()
        _retry_write(
            conn,
            """
            INSERT INTO user_api_keys (id, user_id, provider, key_alias, encrypted_key, nonce, tag, key_preview, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (key_id, user_id, provider.lower().strip(), key_alias.strip(), encrypted_key, nonce, tag, key_preview, now, now)
        )
        return {
            "id": key_id,
            "user_id": user_id,
            "provider": provider.lower().strip(),
            "key_alias": key_alias.strip(),
            "key_preview": key_preview,
            "is_active": True,
            "created_at": now
        }
    finally:
        conn.close()


def list_user_api_keys(user_id: str) -> List[Dict[str, Any]]:
    """Returns safe masked metadata for a user's configured API keys."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, provider, key_alias, key_preview, is_active, created_at, updated_at
            FROM user_api_keys
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_user_api_key(key_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Returns a specific key record for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, provider, key_alias, key_preview, is_active, created_at FROM user_api_keys WHERE id = ? AND user_id = ?",
            (key_id, user_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_user_api_key(key_id: str, user_id: str) -> bool:
    """Deletes a user's API key."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_raw_user_api_keys(user_id: str, provider: Optional[str] = None) -> List[Dict[str, Any]]:
    """Internal method returning cipher components for decryption."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if provider:
            cursor.execute(
                """
                SELECT id, provider, encrypted_key, nonce, tag, key_preview
                FROM user_api_keys
                WHERE user_id = ? AND provider = ? AND is_active = 1
                ORDER BY created_at ASC
                """,
                (user_id, provider.lower().strip())
            )
        else:
            cursor.execute(
                """
                SELECT id, provider, encrypted_key, nonce, tag, key_preview
                FROM user_api_keys
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at ASC
                """,
                (user_id,)
            )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
