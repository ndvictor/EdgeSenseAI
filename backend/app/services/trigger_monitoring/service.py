from __future__ import annotations

from typing import Any

from app.services.trigger_monitoring.models import (
    TriggerEvaluation,
    TriggerMonitoringEvaluateRequest,
    TriggerMonitoringStatusResponse,
    iso_utc_now,
)
from app.services.trigger_monitoring.rules import build_trigger_evaluation, decide_trigger_state_v1


_LATEST_EVALUATION: TriggerEvaluation | None = None


def _deterministic_evaluation_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"tm_{compact}"


def get_latest_evaluation() -> TriggerEvaluation | None:
    return _LATEST_EVALUATION


def build_status() -> TriggerMonitoringStatusResponse:
    latest = get_latest_evaluation()
    updated_at = iso_utc_now()
    return TriggerMonitoringStatusResponse(
        status="ok",
        stage={"stage_number": 8, "stage_name": "Trigger Monitoring", "stage_key": "trigger_monitoring"},
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "monitor_status": "ready",
            "llm_required": False,
            "asset_scope": ["stock"],
            "horizon_scope": ["day_trading"],
            "mode_scope": ["paper_first"],
            "latest_evaluation_id": (latest.evaluation_id if latest else None),
            "next_action": "Evaluate trigger state before execution planning.",
        },
        supported_trigger_states=["not_ready", "armed", "fired", "expired", "missed", "invalidated", "blocked"],
        checkers=[
            {"key": "trigger_rule_registry", "label": "Trigger Rule Registry", "status": "ready", "uses_llm": False},
            {"key": "timing_window_checker", "label": "Timing Window Checker", "status": "ready", "uses_llm": False},
            {"key": "signal_expiration_checker", "label": "Signal Expiration Checker", "status": "ready", "uses_llm": False},
            {"key": "eligibility_dependency_checker", "label": "Eligibility Dependency Checker", "status": "ready", "uses_llm": False},
        ],
        integration_notes=[
            "Stage 8 does not replace trigger_rules or signal_scoring. It orchestrates trigger state evaluation for stock day-trading v1."
        ],
    )


def evaluate_trigger(request: TriggerMonitoringEvaluateRequest) -> dict[str, Any]:
    """
    Deterministic Stage-8 trigger monitoring.

    This is an AI-Agent *without* an LLM:
    it observes workflow/eligibility/trigger/current state, applies deterministic rules,
    outputs a trigger state, and stores the latest evaluation.
    """
    global _LATEST_EVALUATION

    created_at = iso_utc_now()
    evaluation_id = _deterministic_evaluation_id(created_at)

    decision = decide_trigger_state_v1(request)
    evaluation = build_trigger_evaluation(
        evaluation_id=evaluation_id,
        created_at=created_at,
        req=request,
        decision=decision,
    )

    _LATEST_EVALUATION = evaluation
    return {"status": "ok", "trigger_evaluation": evaluation.model_dump()}

