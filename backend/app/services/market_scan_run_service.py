from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


MarketScanTrigger = Literal["manual", "scheduled"]


class MarketScanRun(BaseModel):
    run_id: str
    trigger_type: MarketScanTrigger
    strategy_key: str
    symbols: list[str]
    data_source: str
    auto_run_enabled: bool
    matched_signals_count: int
    skipped_signals_count: int
    should_trigger_workflow: bool
    recommended_workflow_key: str
    workflow_trigger_status: str = "not_triggered"
    workflow_run_id: str | None = None
    cooldown_remaining_seconds: int | None = None
    required_agents: list[str]
    required_models: list[str]
    safety_state: dict[str, Any] = Field(default_factory=dict)
    next_action: str
    status: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MarketScanRunSummary(BaseModel):
    total_runs: int
    scan_runs_today: int
    latest_run: MarketScanRun | None = None
    runs: list[MarketScanRun] = Field(default_factory=list)


_SCAN_RUNS: list[MarketScanRun] = []


def record_scan_run(
    *,
    trigger_type: MarketScanTrigger,
    strategy_key: str,
    symbols: list[str],
    data_source: str,
    auto_run_enabled: bool,
    matched_signals_count: int,
    skipped_signals_count: int,
    should_trigger_workflow: bool,
    recommended_workflow_key: str,
    workflow_trigger_status: str = "not_triggered",
    workflow_run_id: str | None = None,
    cooldown_remaining_seconds: int | None = None,
    required_agents: list[str],
    required_models: list[str],
    safety_state: dict[str, Any],
    next_action: str,
    status: str,
    started_at: datetime,
    completed_at: datetime | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> MarketScanRun:
    completed = completed_at or datetime.utcnow()
    duration_ms = max(0, int((completed - started_at).total_seconds() * 1000))
    run = MarketScanRun(
        run_id=str(uuid4()),
        trigger_type=trigger_type,
        strategy_key=strategy_key,
        symbols=[symbol.upper() for symbol in symbols],
        data_source=data_source,
        auto_run_enabled=auto_run_enabled,
        matched_signals_count=matched_signals_count,
        skipped_signals_count=skipped_signals_count,
        should_trigger_workflow=should_trigger_workflow,
        recommended_workflow_key=recommended_workflow_key,
        workflow_trigger_status=workflow_trigger_status,
        workflow_run_id=workflow_run_id,
        cooldown_remaining_seconds=cooldown_remaining_seconds,
        required_agents=required_agents,
        required_models=required_models,
        safety_state=safety_state,
        next_action=next_action,
        status=status,
        started_at=started_at,
        completed_at=completed,
        duration_ms=duration_ms,
        errors=errors or [],
        warnings=warnings or [],
    )
    _SCAN_RUNS.insert(0, run)
    del _SCAN_RUNS[250:]
    return run


def list_scan_runs(limit: int = 25) -> list[MarketScanRun]:
    return _SCAN_RUNS[: max(1, min(limit, 100))]


def get_latest_scan_run() -> MarketScanRun | None:
    return _SCAN_RUNS[0] if _SCAN_RUNS else None


def get_scan_run(run_id: str) -> MarketScanRun | None:
    return next((run for run in _SCAN_RUNS if run.run_id == run_id), None)


def update_scan_run_workflow_result(run_id: str, workflow_trigger_status: str, workflow_run_id: str | None = None, cooldown_remaining_seconds: int | None = None) -> MarketScanRun | None:
    run = get_scan_run(run_id)
    if run is None:
        return None
    run.workflow_trigger_status = workflow_trigger_status
    run.workflow_run_id = workflow_run_id
    run.cooldown_remaining_seconds = cooldown_remaining_seconds
    return run


def get_scan_run_summary(limit: int = 25) -> MarketScanRunSummary:
    today = datetime.utcnow().date()
    runs = list_scan_runs(limit)
    return MarketScanRunSummary(
        total_runs=len(_SCAN_RUNS),
        scan_runs_today=sum(1 for run in _SCAN_RUNS if run.started_at.date() == today),
        latest_run=get_latest_scan_run(),
        runs=runs,
    )
