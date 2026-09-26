"""
server/manager.py
=================
Database-persisted Pipeline Run Manager and Server-Sent Events (SSE) broadcaster.
Orchestrates LangGraph graph executions, updates SQLite state dynamically,
handles live event broadcasting, cancellation, and Human-in-the-Loop approval.
"""

import os
import sys
import json
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator

from langgraph.checkpoint.memory import MemorySaver
from core.graph.workflow import build_aiautoshorts_graph
from core.graph.state import VideoProductionState
from core.db.repository import (
    create_pipeline_run,
    update_pipeline_run,
    get_pipeline_run,
    list_pipeline_runs,
    record_pipeline_event,
    get_pipeline_events,
    get_channel_by_name,
    list_channels
)
from server.schemas import PipelineRunRequest, PipelineRunStatus, HITLApprovalRequest


def _calc_progress(completed_nodes: List[str], status: str) -> int:
    """Calculates accurate completion percentage (0-100%)."""
    if status == "completed":
        return 100
    if status == "failed":
        return 100
    if status == "cancelled":
        return 100
    if status == "paused_for_approval":
        return 92
    if not completed_nodes:
        return 5

    score = 5
    if "init_pipeline" in completed_nodes:
        score = max(score, 10)
    if "scout_trend" in completed_nodes:
        score = max(score, 25)
    if "scriptwriter" in completed_nodes:
        score = max(score, 45)
    if "legal_check" in completed_nodes:
        score = max(score, 55)
    if "quality_control" in completed_nodes:
        score = max(score, 60)

    fanout = 0
    if "voiceover" in completed_nodes:
        fanout += 8
    if "visual_curator" in completed_nodes:
        fanout += 8
    if "music_director" in completed_nodes:
        fanout += 6
    if "thumbnail" in completed_nodes:
        fanout += 6

    if fanout > 0:
        score = max(score, 60 + fanout)

    if "assemble_video" in completed_nodes:
        score = max(score, 90)
    if "video_qc" in completed_nodes:
        score = max(score, 95)
    if "publish_youtube" in completed_nodes:
        score = 100

    return min(score, 99 if status == "running" else 100)


class PipelineRunManager:
    """Singleton manager executing and streaming AIAutoShorts production runs."""

    def __init__(self):
        self._event_queues: Dict[str, List[asyncio.Queue]] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._checkpointer = MemorySaver()
        self._lock = asyncio.Lock()
        self.reconcile_stale_runs()

    def reconcile_stale_runs(self):
        """Finds any runs in the database marked as 'running' that have no active in-memory task and marks them as interrupted."""
        try:
            db_runs = list_pipeline_runs(limit=200)
            now = datetime.now().isoformat()
            for r in db_runs:
                if r.get("status") in ("running", "pending") and r["id"] not in self._running_tasks:
                    update_pipeline_run(r["id"], {
                        "status": "failed",
                        "error": "Pipeline was interrupted: server process was stopped or restarted.",
                        "completed_at": now
                    })
                    record_pipeline_event(
                        run_id=r["id"],
                        event_type="run_failed",
                        node_name=r.get("current_node"),
                        message="Run marked as interrupted due to server process restart."
                    )
        except Exception as e:
            print(f"[Manager] Warning during stale run reconciliation: {e}")

    def list_runs(self, user_id: Optional[str] = None) -> List[PipelineRunStatus]:
        """Fetches runs from SQLite database, scoped to user_id if provided."""
        db_runs = list_pipeline_runs(user_id=user_id, limit=100)
        results = []
        for r in db_runs:
            status = r.get("status", "pending")
            # If marked running but no active task exists, gracefully treat as interrupted
            if status == "running" and r["id"] not in self._running_tasks:
                status = "failed"
            completed = r.get("completed_nodes", [])
            pct = _calc_progress(completed, status)
            story = r.get("story") or {}
            script = r.get("script") or {}

            results.append(
                PipelineRunStatus(
                    run_id=r["id"],
                    user_id=r.get("user_id"),
                    channel_id=r.get("channel_id"),
                    channel_name=r.get("channel_name", "demo_channel"),
                    channel_display_name=r.get("channel_name", "").title(),
                    status=status,
                    progress_percentage=pct,
                    current_node=r.get("current_node"),
                    completed_nodes=completed,
                    created_at=r.get("created_at") or "",
                    updated_at=r.get("updated_at") or "",
                    error=r.get("error"),
                    custom_topic=r.get("custom_topic"),
                    story_title=story.get("title") if isinstance(story, dict) else None,
                    script_title=script.get("title") if isinstance(script, dict) else None,
                    full_script=script.get("full_script") if isinstance(script, dict) else None,
                    qc_approved=bool(r.get("qc_approved")) if r.get("qc_approved") is not None else None,
                    qc_score=r.get("qc_score"),
                    qc_feedback=r.get("qc_feedback"),
                    video_qc_approved=bool(r.get("video_qc_approved")) if r.get("video_qc_approved") is not None else None,
                    video_qc_score=r.get("video_qc_score"),
                    video_qc_feedback=r.get("video_qc_feedback"),
                    audio_path=r.get("audio_path"),
                    thumbnail_path=r.get("thumbnail_path"),
                    final_video_path=r.get("final_video_path"),
                    video_duration=r.get("video_duration"),
                    youtube_video_id=r.get("youtube_video_id"),
                    auto_post_youtube=bool(r.get("auto_post_youtube", 0)),
                    interrupt_before_publish=bool(r.get("interrupt_before_publish", 0)),
                )
            )
        return results

    def get_run(self, run_id: str, user_id: Optional[str] = None) -> Optional[PipelineRunStatus]:
        """Returns details for a single run ID."""
        r = get_pipeline_run(run_id)
        if not r:
            return None
        if user_id and r.get("user_id") and r.get("user_id") != user_id:
            return None

        status = r.get("status", "pending")
        completed = r.get("completed_nodes", [])
        pct = _calc_progress(completed, status)
        story = r.get("story") or {}
        script = r.get("script") or {}

        return PipelineRunStatus(
            run_id=r["id"],
            user_id=r.get("user_id"),
            channel_id=r.get("channel_id"),
            channel_name=r.get("channel_name", "demo_channel"),
            channel_display_name=r.get("channel_name", "").title(),
            status=status,
            progress_percentage=pct,
            current_node=r.get("current_node"),
            completed_nodes=completed,
            created_at=r.get("created_at") or "",
            updated_at=r.get("updated_at") or "",
            error=r.get("error"),
            custom_topic=r.get("custom_topic"),
            story_title=story.get("title") if isinstance(story, dict) else None,
            script_title=script.get("title") if isinstance(script, dict) else None,
            full_script=script.get("full_script") if isinstance(script, dict) else None,
            qc_approved=bool(r.get("qc_approved")) if r.get("qc_approved") is not None else None,
            qc_score=r.get("qc_score"),
            qc_feedback=r.get("qc_feedback"),
            video_qc_approved=bool(r.get("video_qc_approved")) if r.get("video_qc_approved") is not None else None,
            video_qc_score=r.get("video_qc_score"),
            video_qc_feedback=r.get("video_qc_feedback"),
            audio_path=r.get("audio_path"),
            thumbnail_path=r.get("thumbnail_path"),
            final_video_path=r.get("final_video_path"),
            video_duration=r.get("video_duration"),
            youtube_video_id=r.get("youtube_video_id"),
            auto_post_youtube=bool(r.get("auto_post_youtube", 0)),
            interrupt_before_publish=bool(r.get("interrupt_before_publish", 0)),
        )

    async def broadcast_event(self, run_id: str, event: Dict[str, Any]):
        """Records event to SQLite and broadcasts to active SSE subscribers."""
        event_type = event.get("type", "step_update")
        node_name = event.get("node") or event.get("current_node")
        msg = event.get("message") or f"Event {event_type} at {node_name or 'system'}"

        # Persist to database
        record_pipeline_event(run_id=run_id, event_type=event_type, node_name=node_name, message=msg, data=event)

        # Broadcast live to in-memory queues
        queues = self._event_queues.get(run_id, [])
        for q in list(queues):
            try:
                await q.put(event)
            except Exception:
                pass

    async def subscribe(self, run_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Yields historical events from DB and live events from memory queue."""
        q = asyncio.Queue()
        if run_id not in self._event_queues:
            self._event_queues[run_id] = []
        self._event_queues[run_id].append(q)

        # 1. Replay historical events from SQLite
        past_events = get_pipeline_events(run_id)
        for pe in past_events:
            event_payload = pe.get("data") or {}
            event_payload.setdefault("type", pe["event_type"])
            event_payload.setdefault("timestamp", pe["created_at"])
            event_payload.setdefault("message", pe.get("message"))
            yield event_payload

        # 2. Stream new live events
        try:
            while True:
                event = await q.get()
                yield event
                if event.get("type") in ("run_completed", "run_failed", "run_cancelled"):
                    break
        finally:
            if run_id in self._event_queues and q in self._event_queues[run_id]:
                self._event_queues[run_id].remove(q)

    async def start_run(self, req: PipelineRunRequest, user_id: str = "demo") -> PipelineRunStatus:
        """Creates a pipeline run in SQLite and launches background execution."""
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(2).hex()}"

        # Resolve channel_id
        channel_id = req.channel_id
        if not channel_id:
            chans = list_channels(user_id=user_id)
            match = [c for c in chans if c["name"] == req.channel_name.strip().lower()]
            if match:
                channel_id = match[0]["id"]
            elif chans:
                channel_id = chans[0]["id"]
            else:
                channel_id = "default_channel"

        run_data = {
            "id": run_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "channel_name": req.channel_name,
            "status": "running",
            "progress_percentage": 5,
            "current_node": "init_pipeline",
            "completed_nodes": [],
            "custom_topic": req.custom_topic,
            "auto_post_youtube": req.auto_post_youtube,
            "interrupt_before_publish": req.interrupt_before_publish,
        }
        create_pipeline_run(run_data)

        # Launch execution in background task
        task = asyncio.create_task(self._execute_graph_async(run_id, req, user_id, channel_id))
        self._running_tasks[run_id] = task

        return self.get_run(run_id)

    async def cancel_run(self, run_id: str) -> bool:
        """Cancels a running pipeline execution."""
        task = self._running_tasks.get(run_id)
        if task and not task.done():
            task.cancel()

        update_pipeline_run(run_id, {
            "status": "cancelled",
            "error": "Execution cancelled by user",
            "completed_at": datetime.now().isoformat()
        })
        await self.broadcast_event(run_id, {
            "type": "run_cancelled",
            "run_id": run_id,
            "message": "Pipeline run was cancelled by user.",
            "timestamp": datetime.now().isoformat()
        })
        return True

    async def approve_hitl(self, run_id: str, req: HITLApprovalRequest) -> Optional[PipelineRunStatus]:
        """Approves or rejects a run waiting at the Human-in-the-Loop review gate."""
        r = get_pipeline_run(run_id)
        if not r or r.get("status") != "paused_for_approval":
            return None

        if req.approved:
            update_pipeline_run(run_id, {
                "status": "running",
                "current_node": "publish_youtube",
                "progress_percentage": 96
            })
            await self.broadcast_event(run_id, {
                "type": "hitl_approved",
                "run_id": run_id,
                "message": "Human-in-the-loop approved. Resuming publishing...",
                "timestamp": datetime.now().isoformat()
            })
            # Resume graph execution for remaining node
            asyncio.create_task(self._resume_graph_after_approval(run_id))
        else:
            update_pipeline_run(run_id, {
                "status": "failed",
                "error": f"Rejected by human reviewer: {req.feedback or 'No feedback provided'}",
                "completed_at": datetime.now().isoformat()
            })
            await self.broadcast_event(run_id, {
                "type": "hitl_rejected",
                "run_id": run_id,
                "message": f"Run rejected: {req.feedback}",
                "timestamp": datetime.now().isoformat()
            })

        return self.get_run(run_id)

    async def _execute_graph_async(self, run_id: str, req: PipelineRunRequest, user_id: str, channel_id: str):
        """Asynchronous worker executing LangGraph nodes and syncing to SQLite."""
        try:
            await self.broadcast_event(run_id, {
                "type": "run_started",
                "run_id": run_id,
                "progress_percentage": 5,
                "channel_name": req.channel_name,
                "timestamp": datetime.now().isoformat()
            })

            interrupt_before = ["publish_youtube"] if req.interrupt_before_publish else None
            app = build_aiautoshorts_graph(
                checkpointer=self._checkpointer,
                interrupt_before=interrupt_before
            )

            initial_state: VideoProductionState = {
                "run_id": run_id,
                "user_id": user_id,
                "channel_id": channel_id,
                "channel_name": req.channel_name,
                "auto_post_youtube": req.auto_post_youtube,
                "status": "running",
                "logs": [],
            }

            if req.custom_topic:
                initial_state["custom_topic"] = req.custom_topic
                initial_state["story"] = {
                    "title": req.custom_topic,
                    "summary": f"Custom user prompt: {req.custom_topic}",
                    "angle": "High-retention breakdown",
                    "emotion": "shock",
                    "is_custom": True
                }

            config = {"configurable": {"thread_id": run_id}}
            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()

            def _stream_worker():
                try:
                    for event in app.stream(initial_state, config=config):
                        asyncio.run_coroutine_threadsafe(queue.put(event), loop)
                except Exception as ex:
                    asyncio.run_coroutine_threadsafe(queue.put({"__error__": str(ex)}), loop)
                finally:
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)

            threading.Thread(target=_stream_worker, daemon=True).start()

            completed_nodes: List[str] = []

            while True:
                event = await queue.get()
                if event is None:
                    break
                if "__error__" in event:
                    raise RuntimeError(event["__error__"])

                for node_name, node_output in event.items():
                    if node_name not in completed_nodes:
                        completed_nodes.append(node_name)

                    updates: Dict[str, Any] = {
                        "current_node": node_name,
                        "completed_nodes": completed_nodes,
                        "progress_percentage": _calc_progress(completed_nodes, "running"),
                    }

                    if isinstance(node_output, dict):
                        if "story" in node_output:
                            updates["story"] = node_output["story"]
                        if "script" in node_output:
                            updates["script"] = node_output["script"]
                        if "scenes" in node_output:
                            updates["scenes"] = node_output["scenes"]
                        if "audio_path" in node_output:
                            updates["audio_path"] = node_output["audio_path"]
                        if "thumbnail_path" in node_output:
                            updates["thumbnail_path"] = node_output["thumbnail_path"]
                        if "final_video_path" in node_output:
                            updates["final_video_path"] = node_output["final_video_path"]
                        if "video_duration" in node_output:
                            updates["video_duration"] = node_output["video_duration"]
                        if "qc_approved" in node_output:
                            updates["qc_approved"] = 1 if node_output["qc_approved"] else 0
                            updates["qc_score"] = node_output.get("qc_score")
                            updates["qc_feedback"] = node_output.get("qc_feedback")
                        if "video_qc_approved" in node_output:
                            updates["video_qc_approved"] = 1 if node_output["video_qc_approved"] else 0
                            updates["video_qc_score"] = node_output.get("video_qc_score")
                            updates["video_qc_feedback"] = node_output.get("video_qc_feedback")
                        if "youtube_video_id" in node_output:
                            updates["youtube_video_id"] = node_output["youtube_video_id"]
                        if node_output.get("status") == "failed":
                            updates["status"] = "failed"
                            updates["error"] = node_output.get("error", "Unknown node failure")

                    update_pipeline_run(run_id, updates)

                    await self.broadcast_event(run_id, {
                        "type": "node_completed",
                        "run_id": run_id,
                        "node": node_name,
                        "progress_percentage": updates["progress_percentage"],
                        "completed_nodes": completed_nodes,
                        "timestamp": datetime.now().isoformat()
                    })

            # Check if execution paused before publish (HITL)
            final_r = get_pipeline_run(run_id)
            if req.interrupt_before_publish and "publish_youtube" not in completed_nodes:
                update_pipeline_run(run_id, {
                    "status": "paused_for_approval",
                    "progress_percentage": 92
                })
                await self.broadcast_event(run_id, {
                    "type": "paused_for_approval",
                    "run_id": run_id,
                    "message": "Production complete. Video is ready for Human Review.",
                    "progress_percentage": 92,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                update_pipeline_run(run_id, {
                    "status": "completed",
                    "progress_percentage": 100,
                    "completed_at": datetime.now().isoformat()
                })
                await self.broadcast_event(run_id, {
                    "type": "run_completed",
                    "run_id": run_id,
                    "progress_percentage": 100,
                    "timestamp": datetime.now().isoformat()
                })

        except asyncio.CancelledError:
            update_pipeline_run(run_id, {
                "status": "cancelled",
                "error": "Pipeline run was cancelled.",
                "completed_at": datetime.now().isoformat()
            })
        except Exception as ex:
            err_msg = str(ex)
            update_pipeline_run(run_id, {
                "status": "failed",
                "error": err_msg,
                "completed_at": datetime.now().isoformat()
            })
            await self.broadcast_event(run_id, {
                "type": "run_failed",
                "run_id": run_id,
                "error": err_msg,
                "timestamp": datetime.now().isoformat()
            })
        finally:
            self._running_tasks.pop(run_id, None)

    async def _resume_graph_after_approval(self, run_id: str):
        """Resumes publishing node after Human Approval."""
        try:
            app = build_aiautoshorts_graph(checkpointer=self._checkpointer)
            config = {"configurable": {"thread_id": run_id}}
            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()

            def _resume_worker():
                try:
                    for event in app.stream(None, config=config):
                        asyncio.run_coroutine_threadsafe(queue.put(event), loop)
                except Exception as ex:
                    asyncio.run_coroutine_threadsafe(queue.put({"__error__": str(ex)}), loop)
                finally:
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)

            threading.Thread(target=_resume_worker, daemon=True).start()

            final_status = "completed"
            while True:
                event = await queue.get()
                if event is None:
                    break
                if "__error__" in event:
                    raise RuntimeError(event["__error__"])

                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        updates = {}
                        if "youtube_video_id" in node_output and node_output["youtube_video_id"]:
                            updates["youtube_video_id"] = node_output["youtube_video_id"]
                            updates["status"] = "published"
                            final_status = "published"
                        elif node_output.get("status") == "upload_failed":
                            updates["status"] = "upload_failed"
                            updates["error"] = node_output.get("error", "YouTube upload failed.")
                            final_status = "upload_failed"
                        if updates:
                            update_pipeline_run(run_id, updates)

            update_pipeline_run(run_id, {
                "status": final_status,
                "progress_percentage": 100,
                "completed_at": datetime.now().isoformat()
            })
            await self.broadcast_event(run_id, {
                "type": "run_completed",
                "run_id": run_id,
                "status": final_status,
                "progress_percentage": 100,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as ex:
            update_pipeline_run(run_id, {
                "status": "failed",
                "error": f"Failed during resume: {ex}",
                "completed_at": datetime.now().isoformat()
            })


_manager_instance: Optional[PipelineRunManager] = None

def get_manager() -> PipelineRunManager:
    """Returns singleton instance of PipelineRunManager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PipelineRunManager()
    return _manager_instance
