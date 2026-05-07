from __future__ import annotations

from typing import Any

from app.services.post_trade_evaluation.models import (
    PostTradeEvaluationEvaluateRequest,
    PostTradeEvaluationResult,
    PostTradeEvaluationStatusResponse,
    iso_utc_now,
)
from app.services.post_trade_evaluation.rules import decide_post_trade_evaluation_v1


_LATEST_EVALUATION: PostTradeEvaluationResult | None = None


def _deterministic_evaluation_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"pte_{compact}"


def get_latest_evaluation() -> PostTradeEvaluationResult | None:
    return _LATEST_EVALUATION


def build_status() -> PostTradeEvaluationStatusResponse:
    latest = get_latest_evaluation()
    updated_at = iso_utc_now()
    return PostTradeEvaluationStatusResponse(
        status="ok",
        stage={
            "stage_number": 13,
            "stage_name": "Post-Trade Evaluation",
            "stage_key": "post_trade_evaluation",
        },
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "evaluator_status": "ready",
            "llm_required": False,
            "asset_scope": ["stock"],
            "horizon_scope": ["day_trading"],
            "mode_scope": ["paper_first"],
            "latest_evaluation_id": (latest.evaluation_id if latest else None),
            "next_action": "Evaluate closed or simulated-closed trade outcome.",
        },
        supported_outcome_labels=[
            "win",
            "loss",
            "flat",
            "fakeout",
            "late_entry",
            "rule_violation",
            "slippage_issue",
            "stopped_out",
            "target_hit",
            "time_stop",
            "thesis_invalidated",
        ],
        checkers=[
            {"key": "outcome_labeler", "label": "Outcome Labeler", "status": "ready", "uses_llm": False},
            {"key": "pnl_calculator", "label": "Realized PnL Calculator", "status": "ready", "uses_llm": False},
            {"key": "r_multiple_calculator", "label": "R-Multiple Calculator", "status": "ready", "uses_llm": False},
            {"key": "performance_attribution", "label": "Performance Attribution", "status": "ready", "uses_llm": False},
            {"key": "rule_compliance_checker", "label": "Rule Compliance Checker", "status": "ready", "uses_llm": False},
        ],
    )


def evaluate_post_trade(request: PostTradeEvaluationEvaluateRequest) -> dict[str, Any]:
    """Deterministic Stage-13 post-trade evaluation (no LLM, no broker calls)."""
    global _LATEST_EVALUATION

    created_at = iso_utc_now()
    evaluation_id = _deterministic_evaluation_id(created_at)

    decision = decide_post_trade_evaluation_v1(request)

    result = PostTradeEvaluationResult(
        evaluation_id=evaluation_id,
        trade_id=request.trade.trade_id,
        symbol=request.trade.symbol,
        asset_class=request.trade.asset_class,
        horizon=request.trade.horizon,
        outcome_label=decision.outcome_label,
        outcome_status=decision.outcome_status,
        pnl=decision.pnl,
        risk_result=decision.risk_result,
        execution_quality_result=decision.execution_quality_result,
        rule_compliance_result=decision.rule_compliance_result,
        attribution=decision.attribution,
        blockers=decision.blockers,
        warnings=decision.warnings,
        checkers=decision.checkers,
        allowed_next_stages=decision.allowed_next_stages,
        blocked_next_stages=[],
        next_action=decision.next_action,
        created_at=created_at,
    )

    _LATEST_EVALUATION = result
    return {"status": "ok", "post_trade_evaluation": result.model_dump()}

