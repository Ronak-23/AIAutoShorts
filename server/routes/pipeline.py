"""
server/routes/pipeline.py
=========================
Pipeline execution, real-time SSE streaming, cancellation, and HITL review endpoints.
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional

from server.schemas import PipelineRunRequest, PipelineRunStatus, HITLApprovalRequest
from server.routes.auth import get_current_user
from server.manager import get_manager

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


@router.get("/runs", response_model=List[PipelineRunStatus])
async def list_runs(current_user: dict = Depends(get_current_user)):
    """Lists recent pipeline executions for the authenticated user."""
    manager = get_manager()
    return manager.list_runs(user_id=current_user["id"])


@router.post("/runs", response_model=PipelineRunStatus)
async def start_run(req: PipelineRunRequest, current_user: dict = Depends(get_current_user)):
    """Kicks off an autonomous video production run."""
    manager = get_manager()
    status = await manager.start_run(req, user_id=current_user["id"])
    return status


@router.get("/runs/{run_id}", response_model=PipelineRunStatus)
async def get_run_status(run_id: str, current_user: dict = Depends(get_current_user)):
    """Returns the current state and progress of a run."""
    manager = get_manager()
    run = manager.get_run(run_id, user_id=current_user["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str):
    """Server-Sent Events (SSE) stream emitting real-time node transitions and console logs."""
    manager = get_manager()

    async def event_generator():
        async for event in manager.subscribe(run_id):
            yield {
                "event": "message",
                "data": json.dumps(event)
            }

    return EventSourceResponse(event_generator())


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, current_user: dict = Depends(get_current_user)):
    """Cancels an active pipeline run."""
    manager = get_manager()
    run = manager.get_run(run_id, user_id=current_user["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    success = await manager.cancel_run(run_id)
    return {"message": "Run cancelled successfully", "cancelled": success}


@router.post("/runs/{run_id}/approve", response_model=PipelineRunStatus)
async def review_hitl(run_id: str, req: HITLApprovalRequest, current_user: dict = Depends(get_current_user)):
    """Human-in-the-Loop review endpoint: approve video for publishing or reject with feedback."""
    manager = get_manager()
    run = manager.get_run(run_id, user_id=current_user["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    updated = await manager.approve_hitl(run_id, req)
    if not updated:
        raise HTTPException(status_code=400, detail="Run is not waiting for review or could not be updated")
    return updated


@router.post("/runs/clean-stale")
async def clean_stale_runs(current_user: dict = Depends(get_current_user)):
    """Reconciles and cancels any orphaned pipeline runs."""
    manager = get_manager()
    manager.reconcile_stale_runs()
    return {"message": "Stale runs reconciled successfully"}
