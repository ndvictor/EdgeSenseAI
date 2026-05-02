from datetime import datetime
from typing import Any

from app.services.auto_run_control_service import get_auto_run_state
from app.services.market_condition_scanner_service import MarketScannerRequest, run_market_condition_scan
from app.services.market_scan_run_service import record_scan_run

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - dependency may not be installed in local dev yet
    BackgroundScheduler = None  # type: ignore[assignment]


SCHEDULER_STATUS = "configured_not_started"
DEFAULT_SCHEDULED_SCAN_STRATEGY = "stock_day_trading"
DEFAULT_SCHEDULED_SCAN_SYMBOLS = ["AMD", "NVDA", "AAPL", "MSFT", "BTC-USD"]
_LAST_SCHEDULED_SCAN_RESULT: dict[str, Any] | None = None


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


def get_last_scheduled_scan_result() -> dict[str, Any] | None:
    return _LAST_SCHEDULED_SCAN_RESULT


def run_scheduled_market_scan() -> dict[str, Any]:
    global _LAST_SCHEDULED_SCAN_RESULT
    started_at = datetime.utcnow()
    safety_state = get_auto_run_state()
    if not safety_state.auto_run_enabled:
        next_action = "Auto-run disabled; scheduled market scan skipped."
        run = record_scan_run(
            trigger_type="scheduled",
            strategy_key=DEFAULT_SCHEDULED_SCAN_STRATEGY,
            symbols=DEFAULT_SCHEDULED_SCAN_SYMBOLS,
            data_source="placeholder",
            auto_run_enabled=False,
            matched_signals_count=0,
            skipped_signals_count=0,
            should_trigger_workflow=False,
            recommended_workflow_key="none",
            required_agents=[],
            required_models=[],
            safety_state=safety_state.model_dump(),
            next_action=next_action,
            status="skipped",
            started_at=started_at,
            warnings=["Scheduled scanner is configured but auto-run controls are off."],
        )
        _LAST_SCHEDULED_SCAN_RESULT = {
            "status": "skipped",
            "reason": "auto_run_disabled",
            "next_action": next_action,
            "recommended_workflow_key": "none",
            "scan_run": run.model_dump(),
            "data_source": "source_backed",
        }
        return _LAST_SCHEDULED_SCAN_RESULT

    scan = run_market_condition_scan(
        MarketScannerRequest(
            strategy_key=DEFAULT_SCHEDULED_SCAN_STRATEGY,
            symbols=DEFAULT_SCHEDULED_SCAN_SYMBOLS,
            data_source="auto",
            auto_run=True,
            trigger_type="scheduled",
        )
    )
    _LAST_SCHEDULED_SCAN_RESULT = {
        "status": "completed",
        "next_action": scan.next_action,
        "recommended_workflow_key": scan.recommended_workflow_key,
        "should_trigger_workflow": scan.should_trigger_workflow,
        "matched_signals_count": len(scan.matched_signals),
        "skipped_signals_count": len(scan.skipped_signals),
        "scan_run_id": scan.run_id,
        "scan": scan.model_dump(),
        "data_source": scan.data_source,
    }
    return _LAST_SCHEDULED_SCAN_RESULT
