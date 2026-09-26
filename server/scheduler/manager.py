"""
server/scheduler/manager.py
===========================
Background scheduler worker continuously polling SQLite and triggering due runs.
"""

import asyncio
from datetime import datetime
from typing import Optional

from server.scheduler.service import get_due_schedules, update_schedule, compute_next_run
from server.schemas import PipelineRunRequest


class AutomationScheduler:
    """Async background worker executing automated short production."""

    def __init__(self, pipeline_manager=None, check_interval_seconds: int = 30):
        self.pipeline_manager = pipeline_manager
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self, pipeline_manager=None):
        """Starts the background schedule polling task."""
        if pipeline_manager:
            self.pipeline_manager = pipeline_manager
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        print(f"[Scheduler] AIAutoShorts automation worker started (interval: {self.check_interval_seconds}s).")

    def stop(self):
        """Stops the background schedule worker."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        print("[Scheduler] AIAutoShorts automation worker stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self._check_and_trigger_due_schedules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Scheduler] Error during schedule cycle: {e}")

            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

    async def _check_and_trigger_due_schedules(self):
        due_list = get_due_schedules()
        if not due_list:
            return

        for sched in due_list:
            schedule_id = sched["id"]
            user_id = sched["user_id"]
            channel_name = sched["channel_name"]
            auto_post = bool(sched.get("auto_post_youtube", 0))

            now = datetime.now()
            next_run = compute_next_run(
                sched.get("frequency", "daily"),
                sched.get("time_of_day", "09:00")
            )
            update_schedule(schedule_id, {
                "last_run_at": now.isoformat(),
                "next_run_at": next_run.isoformat()
            })

            if self.pipeline_manager:
                try:
                    req = PipelineRunRequest(
                        channel_name=channel_name,
                        channel_id=sched.get("channel_id"),
                        auto_post_youtube=auto_post,
                        interrupt_before_publish=False
                    )
                    run_status = await self.pipeline_manager.start_run(req, user_id=user_id)
                    update_schedule(schedule_id, {"last_run_id": run_status.run_id})
                    print(f"[Scheduler] Triggered automated run: {run_status.run_id} for channel '{channel_name}'")
                except Exception as ex:
                    print(f"[Scheduler] Failed to trigger run for schedule {schedule_id}: {ex}")


_scheduler_instance: Optional[AutomationScheduler] = None

def get_scheduler(pipeline_manager=None) -> AutomationScheduler:
    """Returns singleton AutomationScheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AutomationScheduler(pipeline_manager=pipeline_manager)
    return _scheduler_instance
