from __future__ import annotations

from typing import Any

from app.services.learning_loop.models import (
    LearningLoopDecision,
    LearningLoopEvaluateRequest,
    LearningLoopStatusResponse,
    iso_utc_now,
)
from app.services.learning_loop.rules import decide_learning_loop_v1


_LATEST_DECISION: LearningLoopDecision | None = None


def _deterministic_decision_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"ll_{compact}"


def get_latest_decision() -> LearningLoopDecision | None:
    return _LATEST_DECISION


def build_status() -> LearningLoopStatusResponse:
    latest = get_latest_decision()
    updated_at = iso_utc_now()
    return LearningLoopStatusResponse(
        status="ok",
        stage={"stage_number": 14, "stage_name": "Learning Loop", "stage_key": "learning_loop"},
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "learning_status": "ready",
            "llm_required": False,
            "asset_scope": ["stock"],
            "horizon_scope": ["day_trading"],
            "mode_scope": ["paper_first"],
            "latest_decision_id": (latest.decision_id if latest else None),
            "next_action": "Evaluate outcome metrics and recommend promotion or demotion.",
        },
        supported_learning_actions=[
            "promote_candidate",
            "keep_monitoring",
            "demote_to_paper",
            "demote_to_research",
            "block_strategy",
            "review_needed",
        ],
        checkers=[
            {"key": "learning_metrics_updater", "label": "Learning Metrics Updater", "status": "ready", "uses_llm": False},
            {"key": "drift_detector", "label": "Drift Detector", "status": "ready", "uses_llm": False},
            {"key": "promotion_demotion_rules", "label": "Promotion/Demotion Rules", "status": "ready", "uses_llm": False},
            {"key": "learning_loop_agent", "label": "Learning Loop Agent", "status": "ready", "uses_llm": False},
        ],
    )


def evaluate_learning_loop(request: LearningLoopEvaluateRequest) -> dict[str, Any]:
    """Deterministic Stage-14 learning loop evaluate (recommendation only)."""
    global _LATEST_DECISION

    created_at = iso_utc_now()
    decision_id = _deterministic_decision_id(created_at)

    decision = decide_learning_loop_v1(request)

    out = LearningLoopDecision(
        decision_id=decision_id,
        strategy_key=request.strategy_key,
        strategy_group=request.strategy_group,
        asset_class=request.asset_class,
        horizon=request.horizon,
        learning_action=decision.learning_action,
        metrics=decision.metrics,
        drift=decision.drift,
        promotion=decision.promotion,
        demotion=decision.demotion,
        reason=decision.reason,
        blockers=decision.blockers,
        warnings=decision.warnings,
        checkers=decision.checkers,
        allowed_next_stages=decision.allowed_next_stages,
        blocked_next_stages=[],
        next_action=decision.next_action,
        created_at=created_at,
    )

    _LATEST_DECISION = out
    return {"status": "ok", "learning_decision": out.model_dump()}

