"""
server/scheduler/service.py
===========================
Scheduling calculation and database operations for AIAutoShorts automation.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from core.db.repository import (
    create_schedule as db_create_schedule,
    get_schedule,
    list_schedules,
    list_due_schedules,
    update_schedule,
    delete_schedule
)


def compute_next_run(frequency: str, time_of_day: str = "09:00", from_dt: Optional[datetime] = None) -> datetime:
    """Calculates next execution timestamp based on recurrence frequency."""
    base = from_dt or datetime.now()

    if frequency == "hourly":
        return base + timedelta(hours=1)
    elif frequency == "every_6_hours":
        return base + timedelta(hours=6)
    elif frequency == "every_12_hours":
        return base + timedelta(hours=12)
    elif frequency == "daily":
        try:
            hour, minute = map(int, time_of_day.split(":"))
        except Exception:
            hour, minute = 9, 0

        target = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= base:
            target += timedelta(days=1)
        return target
    else:
        # Default: 24 hours
        return base + timedelta(days=1)


def get_due_schedules() -> List[Dict[str, Any]]:
    """Returns active schedules ready for execution."""
    return list_due_schedules()
