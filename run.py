"""
run.py
======
Canonical execution entry point for AIAutoShorts.
Starts the FastAPI server, background scheduler, and Web Studio.

Usage:
    python run.py
    python run.py --port 8000
    python run.py --pipeline --channel demo_channel
"""

import os
import sys
import argparse

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.settings import APP_NAME, APP_VERSION
from core.db.repository import init_db
from server.auth.service import ensure_default_user


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Unified Runner")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload")
    parser.add_argument("--pipeline", action="store_true", help="Run a single CLI pipeline execution")
    parser.add_argument("--channel", default="demo_channel", help="Channel slug for CLI pipeline")
    parser.add_argument("--topic", default=None, help="Custom topic for CLI pipeline")
    args = parser.parse_args()

    # Always initialize SQLite database schema and seed default user
    init_db()
    ensure_default_user()

    if args.pipeline:
        import asyncio
        from server.manager import get_manager
        from server.schemas import PipelineRunRequest

        async def _run_cli():
            mgr = get_manager()
            req = PipelineRunRequest(
                channel_name=args.channel,
                custom_topic=args.topic,
                auto_post_youtube=False,
                interrupt_before_publish=False
            )
            print(f"[{APP_NAME}] Starting CLI pipeline execution on channel '{args.channel}'...")
            status = await mgr.start_run(req, user_id="demo")
            print(f"[{APP_NAME}] Run started: {status.run_id}. Awaiting completion...")
            while True:
                await asyncio.sleep(2)
                curr = mgr.get_run(status.run_id)
                print(f"[{APP_NAME}] Progress: {curr.progress_percentage}% | Node: {curr.current_node} | Status: {curr.status}")
                if curr.status in ("completed", "failed", "cancelled"):
                    print(f"[{APP_NAME}] Run finished with status: {curr.status}")
                    if curr.final_video_path:
                        print(f"[{APP_NAME}] Final Video: {curr.final_video_path}")
                    break

        asyncio.run(_run_cli())
        return

    # Start FastAPI Web Server
    import uvicorn
    print(f"\n=================================================================")
    print(f"  {APP_NAME} v{APP_VERSION} — Autonomous YouTube Shorts Production Studio")
    print(f"  Web Studio UI: http://localhost:{args.port}/")
    print(f"  REST API Docs: http://localhost:{args.port}/docs")
    print(f"=================================================================\n")

    uvicorn.run("server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
