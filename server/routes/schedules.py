"""
server/routes/schedules.py
==========================
Automated cron schedules management endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from server.schemas import ScheduleCreateRequest, ScheduleUpdateRequest, ScheduleResponse, PipelineRunRequest
from server.routes.auth import get_current_user
from server.scheduler.service import compute_next_run
from server.manager import get_manager
from core.db.repository import (
    create_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
    delete_schedule,
    list_channels
)

router = APIRouter(prefix="/api/schedules", tags=["Schedules"])


@router.get("", response_model=List[ScheduleResponse])
async def get_all_schedules(current_user: dict = Depends(get_current_user)):
    """Returns all schedules owned by the current user."""
    scheds = list_schedules(user_id=current_user["id"])
    return [ScheduleResponse(**s) for s in scheds]


@router.post("", response_model=ScheduleResponse)
async def create_new_schedule(req: ScheduleCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new automated schedule."""
    user_id = current_user["id"]
    channels = list_channels(user_id=user_id)
    match = [c for c in channels if c["name"] == req.channel_name.strip().lower()]
    if not match:
        raise HTTPException(status_code=400, detail=f"Channel '{req.channel_name}' not found for user")

    channel_id = match[0]["id"]
    next_run = compute_next_run(req.frequency, req.time_of_day)

    sched_data = {
        "user_id": user_id,
        "channel_id": channel_id,
        "channel_name": req.channel_name.strip().lower(),
        "frequency": req.frequency,
        "time_of_day": req.time_of_day,
        "auto_post_youtube": req.auto_post_youtube,
        "is_active": req.is_active,
        "next_run_at": next_run.isoformat()
    }
    created = create_schedule(sched_data)
    return ScheduleResponse(**created)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_existing_schedule(schedule_id: str, req: ScheduleUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates schedule configuration."""
    s = get_schedule(schedule_id)
    if not s or s["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Schedule not found")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if "frequency" in updates or "time_of_day" in updates:
        freq = updates.get("frequency", s["frequency"])
        tod = updates.get("time_of_day", s["time_of_day"])
        updates["next_run_at"] = compute_next_run(freq, tod).isoformat()

    updated = update_schedule(schedule_id, updates)
    return ScheduleResponse(**updated)


@router.delete("/{schedule_id}")
async def delete_existing_schedule(schedule_id: str, current_user: dict = Depends(get_current_user)):
    """Deletes an automated schedule."""
    s = get_schedule(schedule_id)
    if not s or s["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Schedule not found")

    delete_schedule(schedule_id)
    return {"message": "Schedule deleted successfully"}


@router.post("/{schedule_id}/trigger")
async def trigger_schedule_immediately(schedule_id: str, current_user: dict = Depends(get_current_user)):
    """Triggers an immediate pipeline run for this schedule."""
    s = get_schedule(schedule_id)
    if not s or s["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Schedule not found")

    manager = get_manager()
    req = PipelineRunRequest(
        channel_name=s["channel_name"],
        channel_id=s["channel_id"],
        auto_post_youtube=bool(s.get("auto_post_youtube", False)),
        interrupt_before_publish=False
    )
    run_status = await manager.start_run(req, user_id=current_user["id"])
    update_schedule(schedule_id, {"last_run_id": run_status.run_id})
    return {"message": f"Run {run_status.run_id} triggered successfully", "run_id": run_status.run_id}
