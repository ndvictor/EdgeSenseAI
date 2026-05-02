from datetime import datetime
from typing import Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - dependency may not be installed in local dev yet
    BackgroundScheduler = None  # type: ignore[assignment]


SCHEDULER_STATUS = "configured_not_started"


_JOB_METADATA: list[dict[str, Any]] = [
    {
        "id": "premarket_edge_scan",
        "name": "Premarket Edge Scan",
        "trigger": "cron",
        "schedule": "weekdays 08:00 America/Chicago",
        "workflow": "small_account_edge_radar",
        "status": "configured_not_started",
        "data_source": "placeholder",
    },
    {
        "id": "market_open_scan",
        "name": "Market Open Scan",
        "trigger": "cron",
        "schedule": "weekdays 08:35 America/Chicago",
        "workflow": "small_account_edge_radar",
        "status": "configured_not_started",
        "data_source": "placeholder",
    },
    {
        "id": "midday_regime_check",
        "name": "Midday Regime Check",
        "trigger": "cron",
        "schedule": "weekdays 12:00 America/Chicago",
        "workflow": "small_account_edge_radar",
        "status": "configured_not_started",
        "data_source": "placeholder",
    },
    {
        "id": "power_hour_scan",
        "name": "Power Hour Scan",
        "trigger": "cron",
        "schedule": "weekdays 14:15 America/Chicago",
        "workflow": "small_account_edge_radar",
        "status": "configured_not_started",
        "data_source": "placeholder",
    },
    {
        "id": "end_of_day_journal_review",
        "name": "End Of Day Journal Review",
        "trigger": "cron",
        "schedule": "weekdays 15:20 America/Chicago",
        "workflow": "journal_review",
        "status": "configured_not_started",
        "data_source": "placeholder",
    },
]


def get_scheduler_status() -> dict[str, Any]:
    return {
        "scheduler": "apscheduler",
        "status": SCHEDULER_STATUS,
        "apscheduler_available": BackgroundScheduler is not None,
        "auto_start_enabled": False,
        "jobs_configured": len(_JOB_METADATA),
        "updated_at": datetime.utcnow().isoformat(),
        "data_source": "placeholder",
    }


def list_scheduler_jobs() -> dict[str, Any]:
    return {
        **get_scheduler_status(),
        "jobs": _JOB_METADATA,
    }
