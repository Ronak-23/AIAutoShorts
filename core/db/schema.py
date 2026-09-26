"""
AIAutoShorts Database Schema DDL
================================
Defines normalized SQLite tables with foreign keys, indexes,
and check constraints.
"""

DDL_STATEMENTS = [
    # 1. Users
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        hashed_password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",

    # 2. Channels (Multi-tenant)
    """
    CREATE TABLE IF NOT EXISTS channels (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        display_name TEXT NOT NULL,
        niche TEXT NOT NULL,
        tone TEXT NOT NULL,
        target_audience TEXT,
        voice_provider TEXT DEFAULT 'edge',
        voice_name TEXT DEFAULT 'en-US-ChristopherNeural',
        voice_rate TEXT DEFAULT '+8%',
        voice_pitch TEXT DEFAULT '+0Hz',
        video_duration_seconds INTEGER DEFAULT 55,
        min_words INTEGER DEFAULT 110,
        max_words INTEGER DEFAULT 140,
        fps INTEGER DEFAULT 30,
        visual_mode TEXT DEFAULT 'stock_plus_wiki',
        stock_provider TEXT DEFAULT 'pexels',
        default_bgm_mood TEXT DEFAULT 'suspense',
        bgm_volume REAL DEFAULT 0.22,
        caption_style TEXT DEFAULT 'yellow_glow',
        is_active INTEGER DEFAULT 1,
        youtube_channel_id TEXT,
        youtube_category_id TEXT DEFAULT '28',
        youtube_channel_title TEXT,
        youtube_token_encrypted TEXT,
        youtube_authenticated_at DATETIME,
        tags_json TEXT DEFAULT '[]',
        rss_feeds_json TEXT DEFAULT '[]',
        vocabulary_json TEXT DEFAULT '[]',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, name)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_channels_user ON channels(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_channels_name ON channels(name);",

    # 3. Pipeline Runs (Persistent execution state)
    """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
        channel_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        progress_percentage INTEGER DEFAULT 0,
        current_node TEXT DEFAULT 'init_pipeline',
        completed_nodes_json TEXT DEFAULT '[]',
        custom_topic TEXT,
        story_json TEXT,
        script_json TEXT,
        scenes_json TEXT,
        audio_path TEXT,
        thumbnail_path TEXT,
        final_video_path TEXT,
        video_duration REAL,
        qc_approved INTEGER,
        qc_score REAL,
        qc_feedback TEXT,
        video_qc_approved INTEGER,
        video_qc_score REAL,
        video_qc_feedback TEXT,
        youtube_video_id TEXT,
        auto_post_youtube INTEGER DEFAULT 0,
        interrupt_before_publish INTEGER DEFAULT 0,
        error TEXT,
        started_at DATETIME,
        completed_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_runs_user ON pipeline_runs(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_runs_status ON pipeline_runs(status);",
    "CREATE INDEX IF NOT EXISTS idx_runs_channel ON pipeline_runs(channel_id);",
    "CREATE INDEX IF NOT EXISTS idx_runs_created ON pipeline_runs(created_at DESC);",

    # 4. Pipeline Events (Streaming logs & live state transitions)
    """
    CREATE TABLE IF NOT EXISTS pipeline_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        node_name TEXT,
        message TEXT,
        data_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_run ON pipeline_events(run_id);",
    "CREATE INDEX IF NOT EXISTS idx_events_created ON pipeline_events(created_at);",

    # 5. Schedules (Automated production recurrence)
    """
    CREATE TABLE IF NOT EXISTS schedules (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
        channel_name TEXT NOT NULL,
        frequency TEXT NOT NULL,
        time_of_day TEXT,
        auto_post_youtube INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        last_run_at DATETIME,
        next_run_at DATETIME,
        last_run_id TEXT REFERENCES pipeline_runs(id) ON DELETE SET NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_schedules_user ON schedules(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_schedules_active_next ON schedules(is_active, next_run_at);",

    # 6. Seen Stories (Deduplication engine)
    """
    CREATE TABLE IF NOT EXISTS seen_stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_name TEXT NOT NULL,
        story_url TEXT,
        title_hash TEXT NOT NULL,
        title TEXT,
        seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_seen_channel ON seen_stories(channel_name);",
    "CREATE INDEX IF NOT EXISTS idx_seen_hash ON seen_stories(title_hash);",
    "CREATE INDEX IF NOT EXISTS idx_seen_channel_seen_at ON seen_stories(channel_name, seen_at);",

    # 7. A/B Tests
    """
    CREATE TABLE IF NOT EXISTS ab_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        channel_name TEXT NOT NULL,
        video_id TEXT NOT NULL,
        title_a TEXT NOT NULL,
        title_b TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        switched INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_ab_channel ON ab_tests(channel_name);",
    "CREATE INDEX IF NOT EXISTS idx_ab_video ON ab_tests(video_id);",

    # 8. Replied Comments
    """
    CREATE TABLE IF NOT EXISTS replied_comments (
        comment_id TEXT PRIMARY KEY,
        channel_name TEXT NOT NULL,
        replied_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # 9. AI Reviews (Self-learning loop & VLM feedback)
    """
    CREATE TABLE IF NOT EXISTS ai_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
        channel_name TEXT NOT NULL,
        attempt INTEGER DEFAULT 1,
        overall_score INTEGER,
        visual_score INTEGER,
        audio_score INTEGER,
        caption_score INTEGER,
        flow_score INTEGER,
        retention_dropoff_ts TEXT,
        watch_likelihood INTEGER,
        upload_recommended INTEGER DEFAULT 1,
        issues_json TEXT,
        fix_applied INTEGER DEFAULT 0,
        skipped INTEGER DEFAULT 0,
        skip_reason TEXT,
        summary TEXT,
        raw_json TEXT,
        reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_reviews_run ON ai_reviews(run_id);",
    "CREATE INDEX IF NOT EXISTS idx_reviews_channel ON ai_reviews(channel_name);",

    # 10. Legacy Experiments Table (Backward compatibility for auto_tune analysis)
    """
    CREATE TABLE IF NOT EXISTS experiments (
        run_id TEXT PRIMARY KEY,
        user_id TEXT DEFAULT 'demo',
        video_id TEXT,
        uploaded_at DATETIME,
        metrics_fetched_at DATETIME,
        parameters TEXT,
        metrics TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_exp_video ON experiments(video_id);",

    # 11. Meta table (VACUUM tracking)
    """
    CREATE TABLE IF NOT EXISTS _meta (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """,

    # 12. User BYOK API Keys (AES-256-GCM Encrypted)
    """
    CREATE TABLE IF NOT EXISTS user_api_keys (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL CHECK(provider IN ('groq', 'gemini', 'openrouter', 'pexels', 'elevenlabs')),
        key_alias TEXT DEFAULT 'Default',
        encrypted_key BLOB NOT NULL,
        nonce BLOB NOT NULL,
        tag BLOB NOT NULL,
        key_preview TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_provider ON user_api_keys(user_id, provider);"
]
