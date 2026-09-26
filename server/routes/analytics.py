"""
server/routes/analytics.py
==========================
Performance metrics, quality scores, A/B testing, and self-learning analytics.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from server.routes.auth import get_current_user
from core.db.repository import list_pipeline_runs, list_experiments, get_pending_ab_tests

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_analytics_overview(current_user: dict = Depends(get_current_user)):
    """Computes high-level production metrics."""
    runs = list_pipeline_runs(user_id=current_user["id"], limit=200)

    total_runs = len(runs)
    completed = [r for r in runs if r.get("status") == "completed"]
    failed = [r for r in runs if r.get("status") == "failed"]

    qc_scores = []
    for r in runs:
        s = r.get("qc_score")
        vs = r.get("video_qc_score")

        # Normalize legacy 10-point scale (<= 10.0) to 100-point scale
        if s is not None and s <= 10.0:
            s = s * 10.0

        if vs is not None and s is not None:
            qc_scores.append(round((s + vs) / 2.0, 1))
        elif vs is not None:
            qc_scores.append(vs)
        elif s is not None:
            qc_scores.append(s)

    avg_qc = round(sum(qc_scores) / len(qc_scores), 1) if qc_scores else 0.0

    durations = [r["video_duration"] for r in runs if r.get("video_duration") is not None]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 55.0

    return {
        "total_runs": total_runs,
        "completed_count": len(completed),
        "failed_count": len(failed),
        "success_rate_percent": round((len(completed) / total_runs * 100), 1) if total_runs > 0 else 100.0,
        "average_qc_score": avg_qc,
        "average_duration_seconds": avg_duration,
        "active_ab_tests_count": len(get_pending_ab_tests(min_age_hours=0))
    }


@router.get("/experiments")
async def get_experiments(current_user: dict = Depends(get_current_user)):
    """Returns past video experiments and performance logs."""
    return list_experiments(user_id=current_user["id"])
