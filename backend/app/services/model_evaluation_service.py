from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.research_persistence_service import (
    create_model_evaluation_run,
    get_latest_passed_model_evaluation,
    list_model_evaluation_runs,
)

DEFAULT_MINIMUM_REQUIREMENTS = {
    "sample_size": 50,
    "max_drawdown_max": 0.35,
    "false_positive_rate_max": 0.45,
}


class ModelEvaluationRunRequest(BaseModel):
    model_key: str
    artifact_id: str | None = None
    evaluation_type: str = "research_backtest"
    dataset_source: str = "manual_metrics"
    metrics: dict[str, Any] = Field(default_factory=dict)
    minimum_requirements: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def evaluate_metrics(metrics: dict[str, Any], requirements: dict[str, Any]) -> tuple[str, bool, list[str], list[str]]:
    req = {**DEFAULT_MINIMUM_REQUIREMENTS, **(requirements or {})}
    failures: list[str] = []
    warnings: list[str] = []
    if not metrics:
        return "insufficient_data", False, ["No evaluation metrics provided."], warnings
    sample_size = metrics.get("sample_size")
    if sample_size is None or float(sample_size) < float(req.get("sample_size", 50)):
        failures.append("sample_size below minimum requirement.")
    max_drawdown = metrics.get("max_drawdown")
    if max_drawdown is not None and abs(float(max_drawdown)) > float(req.get("max_drawdown_max", 0.35)):
        failures.append("max_drawdown exceeds maximum allowed threshold.")
    false_positive_rate = metrics.get("false_positive_rate")
    if false_positive_rate is not None and float(false_positive_rate) > float(req.get("false_positive_rate_max", 0.45)):
        failures.append("false_positive_rate exceeds maximum allowed threshold.")
    if not any(key in metrics for key in ["win_rate", "precision", "profit_factor", "average_return", "sharpe"]):
        failures.append("No performance quality metric provided.")
    if failures:
        return "failed", False, failures, warnings
    return "passed", True, failures, warnings


def create_evaluation(request: ModelEvaluationRunRequest) -> dict[str, Any]:
    status, passed, failures, warnings = evaluate_metrics(request.metrics, request.minimum_requirements)
    payload = request.model_dump()
    payload.update({"status": status, "passed": passed, "failure_reasons": failures, "warnings": warnings})
    return create_model_evaluation_run(payload)


def list_evaluations(model_key: str | None = None) -> dict[str, Any]:
    return {"data_source": "postgres_or_empty", "evaluations": list_model_evaluation_runs(model_key)}


def latest_passed_evaluation(model_key: str) -> dict[str, Any]:
    row = get_latest_passed_model_evaluation(model_key)
    return row or {"model_key": model_key, "status": "missing", "passed": False, "next_action": "Run evaluation with explicit metrics before promotion."}
