from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.research_persistence_service import (
    create_model_calibration_run,
    get_latest_passed_model_calibration,
    list_model_calibration_runs,
)

DEFAULT_CALIBRATION_REQUIREMENTS = {
    "sample_size": 50,
    "expected_calibration_error_max": 0.15,
    "brier_score_max": 0.25,
}


class ModelCalibrationRunRequest(BaseModel):
    model_key: str
    artifact_id: str | None = None
    calibration_type: str = "confidence_calibration"
    dataset_source: str = "manual_metrics"
    metrics: dict[str, Any] = Field(default_factory=dict)
    calibration_report: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def evaluate_calibration(metrics: dict[str, Any]) -> tuple[str, bool, list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    if not metrics:
        return "insufficient_data", False, ["No calibration metrics provided."], warnings
    sample_size = metrics.get("sample_size")
    if sample_size is None or float(sample_size) < DEFAULT_CALIBRATION_REQUIREMENTS["sample_size"]:
        failures.append("sample_size below calibration minimum requirement.")
    ece = metrics.get("expected_calibration_error")
    if ece is None:
        failures.append("expected_calibration_error is required.")
    elif float(ece) > DEFAULT_CALIBRATION_REQUIREMENTS["expected_calibration_error_max"]:
        failures.append("expected_calibration_error exceeds threshold.")
    brier = metrics.get("brier_score")
    if brier is not None and float(brier) > DEFAULT_CALIBRATION_REQUIREMENTS["brier_score_max"]:
        failures.append("brier_score exceeds threshold.")
    if failures:
        return "failed", False, failures, warnings
    return "passed", True, failures, warnings


def create_calibration(request: ModelCalibrationRunRequest) -> dict[str, Any]:
    status, passed, failures, warnings = evaluate_calibration(request.metrics)
    payload = request.model_dump()
    payload.update({"status": status, "passed": passed, "failure_reasons": failures, "warnings": warnings})
    return create_model_calibration_run(payload)


def list_calibrations(model_key: str | None = None) -> dict[str, Any]:
    return {"data_source": "postgres_or_empty", "calibrations": list_model_calibration_runs(model_key)}


def latest_passed_calibration(model_key: str) -> dict[str, Any]:
    row = get_latest_passed_model_calibration(model_key)
    return row or {"model_key": model_key, "status": "missing", "passed": False, "next_action": "Run calibration with explicit metrics before promotion."}
