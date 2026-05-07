from __future__ import annotations

from typing import Any

from app.services.close_position.models import (
    ClosePositionReviewRequest,
    ClosePositionReviewResult,
    ClosePositionStatusResponse,
    iso_utc_now,
)
from app.services.close_position.rules import decide_close_review_v1


_LATEST_REVIEW: ClosePositionReviewResult | None = None


def _deterministic_review_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"cp_{compact}"


def get_latest_review() -> ClosePositionReviewResult | None:
    return _LATEST_REVIEW


def build_status() -> ClosePositionStatusResponse:
    latest = get_latest_review()
    updated_at = iso_utc_now()
    return ClosePositionStatusResponse(
        status="ok",
        stage={"stage_number": 12, "stage_name": "Close Position", "stage_key": "close_position"},
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "review_status": "ready",
            "llm_required": False,
            "asset_scope": ["stock"],
            "horizon_scope": ["day_trading"],
            "mode_scope": ["paper_first"],
            "latest_review_id": (latest.review_id if latest else None),
            "next_action": "Review close/reduce decision from Stage 11 position monitoring output.",
        },
        supported_review_actions=["hold", "reduce_review", "close_review", "blocked"],
        checkers=[
            {"key": "exit_rule_evaluator", "label": "Exit Rule Evaluator", "status": "ready", "uses_llm": False},
            {"key": "close_position_agent", "label": "Close Position Agent", "status": "ready", "uses_llm": False},
            {"key": "close_order_preview_builder", "label": "Close Order Preview Builder", "status": "ready", "uses_llm": False},
            {"key": "master_admin_gate", "label": "Master Admin Gate", "status": "ready", "uses_llm": False},
        ],
    )


def review_close_position(request: ClosePositionReviewRequest) -> dict[str, Any]:
    """
    Deterministic Stage-12 close/reduce review (preview only).

    Guarantees:
    - never submits orders
    - never calls broker APIs
    - never calls execution endpoints
    """
    global _LATEST_REVIEW

    created_at = iso_utc_now()
    review_id = _deterministic_review_id(created_at)

    decision = decide_close_review_v1(request)

    result = ClosePositionReviewResult(
        review_id=review_id,
        position_id=request.position_evaluation.position_id,
        symbol=request.position_evaluation.symbol,
        asset_class=request.position_evaluation.asset_class,
        horizon=request.position_evaluation.horizon,
        review_action=decision.review_action,
        review_status=decision.review_status,  # type: ignore[arg-type]
        submitted_order=False,
        broker_called=False,
        reason=decision.reason,
        close_order_preview=decision.close_order_preview,
        blockers=decision.blockers,
        warnings=decision.warnings,
        checkers=decision.checkers,
        allowed_next_stages=decision.allowed_next_stages,
        next_action=decision.next_action,
        created_at=created_at,
    )

    _LATEST_REVIEW = result
    return {"status": "ok", "close_review": result.model_dump()}

