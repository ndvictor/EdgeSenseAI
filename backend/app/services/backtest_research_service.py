from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.research_persistence_service import (
    create_model_backtest_run,
    create_research_experiment_run,
    create_strategy_backtest_run,
    get_latest_passed_model_backtest,
    list_model_backtest_runs,
    list_research_experiment_runs,
    list_strategy_backtest_runs,
)


class ModelBacktestRunRequest(BaseModel):
    model_key: str
    artifact_id: str | None = None
    run_type: str = "historical_backtest"
    dataset_source: str = "manual_request"
    symbols: list[str] = Field(default_factory=list)
    status: str | None = None
    passed: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    failure_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyBacktestRunRequest(BaseModel):
    strategy_key: str
    run_type: str = "historical_backtest"
    dataset_source: str = "manual_request"
    symbols: list[str] = Field(default_factory=list)
    status: str | None = None
    passed: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    failure_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchExperimentRequest(BaseModel):
    experiment_key: str | None = None
    experiment_type: str = "model_backtest"
    target_type: str = "model"
    target_key: str
    priority: int = 50
    status: str = "queued"
    objective: str = "Research candidate evidence before promotion."
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def create_model_backtest_request(request: ModelBacktestRunRequest) -> dict[str, Any]:
    payload = request.model_dump()
    if payload.get("passed") and not payload.get("metrics"):
        payload["passed"] = False
        payload["status"] = "failed"
        payload["failure_reasons"] = [*payload.get("failure_reasons", []), "Cannot pass backtest without explicit metrics."]
    return create_model_backtest_run(payload)


def create_strategy_backtest_request(request: StrategyBacktestRunRequest) -> dict[str, Any]:
    payload = request.model_dump()
    if payload.get("passed") and not payload.get("metrics"):
        payload["passed"] = False
        payload["status"] = "failed"
        payload["failure_reasons"] = [*payload.get("failure_reasons", []), "Cannot pass backtest without explicit metrics."]
    return create_strategy_backtest_run(payload)


def create_research_experiment(request: ResearchExperimentRequest) -> dict[str, Any]:
    return create_research_experiment_run(request.model_dump())


def get_research_summary() -> dict[str, Any]:
    experiments = list_research_experiment_runs()
    model_backtests = list_model_backtest_runs()
    strategy_backtests = list_strategy_backtest_runs()
    return {
        "data_source": "postgres_or_empty",
        "experiment_count": len(experiments),
        "model_backtest_count": len(model_backtests),
        "strategy_backtest_count": len(strategy_backtests),
        "blocked_experiments": len([row for row in experiments if row.get("status") == "blocked"]),
        "passed_model_backtests": len([row for row in model_backtests if row.get("passed") is True]),
        "passed_strategy_backtests": len([row for row in strategy_backtests if row.get("passed") is True]),
        "safety_notes": ["Backtest records require explicit symbols.", "Passed backtests require explicit metrics.", "No fake backtest results are generated."],
    }


def latest_passed_model_backtest(model_key: str) -> dict[str, Any]:
    return get_latest_passed_model_backtest(model_key) or {"model_key": model_key, "status": "missing", "passed": False, "next_action": "Run model backtest with explicit symbols and metrics."}
