from __future__ import annotations

from dataclasses import dataclass

from app.core.effective_runtime import effective_bool
from app.services.close_position.models import (
    CheckerResult,
    CloseOrderPreview,
    ClosePositionReviewRequest,
    ReviewAction,
    reduced_qty,
)


@dataclass(frozen=True)
class ReviewDecision:
    review_action: ReviewAction
    review_status: str
    reason: str
    close_order_preview: CloseOrderPreview | None
    blockers: list[str]
    warnings: list[str]
    checkers: dict[str, CheckerResult]
    allowed_next_stages: list[str]
    next_action: str


def _effective_master_admin(req: ClosePositionReviewRequest) -> dict[str, bool]:
    """
    Combine caller-provided master_admin snapshot with effective runtime gates.

    v1 behavior: if either indicates a hard block (e.g. emergency stop), we treat it as blocked.
    """
    provided = req.master_admin
    eff = {
        "workflow_enabled": effective_bool("WORKFLOW_ENABLED") and bool(provided.workflow_enabled),
        "execution_enabled": effective_bool("EXECUTION_ENABLED") and bool(provided.execution_enabled),
        "paper_trading_enabled": effective_bool("PAPER_TRADING_ENABLED") and bool(provided.paper_trading_enabled),
        "live_trading_enabled": effective_bool("LIVE_TRADING_ENABLED") or bool(provided.live_trading_enabled),
        "broker_execution_enabled": effective_bool("BROKER_EXECUTION_ENABLED") and bool(provided.broker_execution_enabled),
        "human_approval_required": effective_bool("REQUIRE_HUMAN_APPROVAL") or bool(provided.human_approval_required),
        "emergency_stop": effective_bool("EMERGENCY_STOP") or bool(provided.emergency_stop),
        "force_close_requested": effective_bool("FORCE_CLOSE_REQUESTED") or bool(provided.force_close_requested),
    }
    return eff


def decide_close_review_v1(req: ClosePositionReviewRequest) -> ReviewDecision:
    blockers: list[str] = []
    warnings: list[str] = []
    checkers: dict[str, CheckerResult] = {}

    # A) No submit (forced)
    allow_submit = False

    # B) Scope blockers
    if req.position_evaluation.asset_class.strip().lower() != "stock":
        blockers.append("asset_class_not_supported")
    if req.position_evaluation.horizon.strip().lower() != "day_trading":
        blockers.append("horizon_not_supported")

    # C) Position blockers
    if req.position.quantity <= 0:
        blockers.append("quantity_not_positive")
    if req.position.side != "long":
        blockers.append("side_not_supported_v1")
    if req.position.current_price <= 0:
        blockers.append("current_price_invalid")

    # D) Master Admin blockers
    ma = _effective_master_admin(req)
    if ma["live_trading_enabled"]:
        blockers.append("live_trading_enabled_blocked_in_v1")

    if ma["emergency_stop"] and not ma["force_close_requested"]:
        blockers.append("emergency_stop_active")

    if not ma["workflow_enabled"]:
        blockers.append("workflow_disabled_by_master_admin")

    if not ma["paper_trading_enabled"]:
        blockers.append("paper_trading_disabled_by_master_admin")

    if not ma["execution_enabled"]:
        blockers.append("execution_disabled_by_master_admin")

    if not ma["broker_execution_enabled"]:
        blockers.append("broker_execution_disabled")

    checkers["master_admin_gate"] = CheckerResult(
        status="fail" if any(b in blockers for b in ("emergency_stop_active", "workflow_disabled_by_master_admin")) else "pass",
        message="Master admin gates evaluated (no execution/broker calls).",
    )

    # If scope/position validation blockers exist, do not proceed with close/reduce preview.
    scope_or_validation_block = any(
        b in blockers
        for b in (
            "asset_class_not_supported",
            "horizon_not_supported",
            "quantity_not_positive",
            "side_not_supported_v1",
            "current_price_invalid",
        )
    )

    # E) Force close overrides action selection (still no submission) unless scope/validation blocks prevent it.
    if scope_or_validation_block:
        action = "blocked"
        reason = "Blocked by scope or invalid position inputs."
    elif ma["force_close_requested"]:
        action = "close_review"
        reason = "Master Admin force close requested."
    else:
        # F) Stage 11 action mapping
        ra = (req.position_evaluation.recommended_action or "").strip().lower()
        if ra in {"hold", "watch"}:
            action = "hold"
            reason = "Stage 11 recommends holding/monitoring."
        elif ra == "reduce":
            action = "reduce_review"
            reason = "Stage 11 recommends reducing position."
        elif ra == "exit_review":
            action = "close_review"
            reason = "Stage 11 recommends exit review."
        elif ra == "blocked":
            action = "blocked"
            reason = "Stage 11 output is blocked."
        else:
            action = "blocked"
            reason = f"Unsupported Stage 11 recommended_action '{ra}'."
            blockers.append("unsupported_recommended_action")

    # Build preview when needed
    preview: CloseOrderPreview | None = None
    if action == "hold":
        allowed_next: list[str] = []
        next_action = "Continue monitoring position."
    else:
        qty = req.position.quantity
        if action == "reduce_review":
            q = reduced_qty(qty, req.review_preferences.reduce_percent)
            if q <= 0:
                blockers.append("reduce_quantity_not_positive")
                action = "blocked"
                reason = "Reduce quantity computed to <= 0."
            else:
                qty = q

        if action in {"reduce_review", "close_review"}:
            order_style = req.review_preferences.order_style
            order_type = "limit" if order_style == "limit" else "market"
            limit_price = float(req.position.current_price) if order_type == "limit" else None

            preview = CloseOrderPreview(
                symbol=req.position_evaluation.symbol,
                quantity=int(qty),
                order_type=order_type,  # type: ignore[arg-type]
                limit_price=limit_price,
                reason=req.review_preferences.close_reason,
                human_approval_confirmed=False,
            )

        allowed_next = []
        if not blockers and ma["human_approval_required"]:
            allowed_next = ["human_approval_queue"]
        next_action = "Review close order preview and Master Admin gates before any execution workflow."

    # Review status is blocked when any blocker exists or action is blocked
    review_status = "blocked" if blockers or action == "blocked" else "ready"

    checkers["exit_rule_evaluator"] = CheckerResult(
        status="pass" if req.position_evaluation.recommended_action in {"reduce", "exit_review", "hold", "watch"} else "warn",
        message="Mapped Stage 11 recommendation to Stage 12 review action.",
    )
    checkers["close_position_agent"] = CheckerResult(
        status="pass" if action in {"hold", "reduce_review", "close_review"} else "fail",
        message="Close/reduce review decision produced (no order submission).",
    )
    checkers["close_order_preview_builder"] = CheckerResult(
        status="pass" if (action in {"reduce_review", "close_review"} and preview is not None) or action == "hold" else "fail",
        message="Order preview built (or not required).",
    )

    if allow_submit:
        warnings.append("allow_submit_ignored_forced_false_v1")

    return ReviewDecision(
        review_action=action,
        review_status=review_status,
        reason=reason,
        close_order_preview=preview,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
        checkers=checkers,
        allowed_next_stages=allowed_next,
        next_action=next_action,
    )

