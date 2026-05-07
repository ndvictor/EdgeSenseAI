from __future__ import annotations

from typing import Any

from app.services.position_monitoring.models import (
    PositionEvaluation,
    PositionMonitoringEvaluateRequest,
    PositionMonitoringStatusResponse,
    iso_utc_now,
)
from app.services.position_monitoring.rules import build_position_evaluation, decide_position_monitoring_v1


_LATEST_EVALUATION: PositionEvaluation | None = None


def _deterministic_evaluation_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"pm_{compact}"


def get_latest_evaluation() -> PositionEvaluation | None:
    return _LATEST_EVALUATION


def build_status() -> PositionMonitoringStatusResponse:
    latest = get_latest_evaluation()
    updated_at = iso_utc_now()
    return PositionMonitoringStatusResponse(
        status="ok",
        stage={"stage_number": 11, "stage_name": "Position Monitoring", "stage_key": "position_monitoring"},
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "monitor_status": "ready",
            "llm_required": False,
            "asset_scope": ["stock"],
            "horizon_scope": ["day_trading"],
            "mode_scope": ["paper_first"],
            "latest_evaluation_id": (latest.evaluation_id if latest else None),
            "next_action": "Evaluate active position health and thesis validity.",
        },
        supported_position_actions=["hold", "watch", "reduce", "exit_review", "blocked"],
        checkers=[
            {"key": "pnl_calculator", "label": "PnL Calculator", "status": "ready", "uses_llm": False},
            {"key": "thesis_validity_checker", "label": "Thesis Validity Checker", "status": "ready", "uses_llm": False},
            {"key": "position_risk_monitor", "label": "Position Risk Monitor", "status": "ready", "uses_llm": False},
            {"key": "master_admin_gate", "label": "Master Admin Gate", "status": "ready", "uses_llm": False},
        ],
    )


def evaluate_position(request: PositionMonitoringEvaluateRequest) -> dict[str, Any]:
    """
    Deterministic Stage-11 position monitoring.

    This is an AI-Agent *without* an LLM:
    it observes position + thesis + risk state, applies deterministic rules,
    returns a monitoring evaluation, and stores the latest evaluation.
    """
    global _LATEST_EVALUATION

    created_at = iso_utc_now()
    evaluation_id = _deterministic_evaluation_id(created_at)

    decision = decide_position_monitoring_v1(request)
    evaluation = build_position_evaluation(
        evaluation_id=evaluation_id,
        created_at=created_at,
        req=request,
        decision=decision,
    )

    _LATEST_EVALUATION = evaluation
    return {"status": "ok", "position_evaluation": evaluation.model_dump()}

