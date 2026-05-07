from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.post_trade_evaluation.models import (
    AttributionResult,
    CheckerResult,
    ExecutionQualityResult,
    OutcomeLabel,
    OutcomeStatus,
    PnlResult,
    PostTradeEvaluationEvaluateRequest,
    RiskResult,
    RuleComplianceResult,
)


@dataclass(frozen=True)
class EvalDecision:
    outcome_label: OutcomeLabel
    outcome_status: OutcomeStatus
    pnl: PnlResult
    risk_result: RiskResult
    execution_quality_result: ExecutionQualityResult
    rule_compliance_result: RuleComplianceResult
    attribution: AttributionResult
    blockers: list[str]
    warnings: list[str]
    checkers: dict[str, CheckerResult]
    allowed_next_stages: list[str]
    next_action: str


def _parse_iso(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str)


def _scope_and_validation(req: PostTradeEvaluationEvaluateRequest) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    t = req.trade

    if t.asset_class.strip().lower() != "stock":
        blockers.append("asset_class_not_supported")
    if t.horizon.strip().lower() != "day_trading":
        blockers.append("horizon_not_supported")
    if t.side != "long":
        blockers.append("side_not_supported_v1")

    if t.quantity <= 0:
        blockers.append("quantity_not_positive")
    if t.actual_entry_price <= 0:
        blockers.append("actual_entry_price_invalid")
    if t.actual_exit_price <= 0:
        blockers.append("actual_exit_price_invalid")
    if t.stop_loss <= 0:
        blockers.append("stop_loss_invalid")

    try:
        opened = _parse_iso(t.opened_at)
        closed = _parse_iso(t.closed_at)
        if closed < opened:
            blockers.append("closed_before_opened")
    except Exception:
        blockers.append("invalid_timestamp")

    return blockers, warnings


def _pnl(req: PostTradeEvaluationEvaluateRequest) -> tuple[PnlResult, CheckerResult]:
    t = req.trade
    gross_entry = float(t.actual_entry_price) * float(t.quantity)
    gross_exit = float(t.actual_exit_price) * float(t.quantity)
    realized = gross_exit - gross_entry
    realized_pct = (realized / gross_entry * 100.0) if gross_entry > 0 else 0.0
    pnl = PnlResult(
        realized_pnl=round(realized, 2),
        realized_pnl_percent=round(realized_pct, 2),
        gross_entry_notional=round(gross_entry, 2),
        gross_exit_notional=round(gross_exit, 2),
    )
    status = "pass" if gross_entry > 0 else "fail"
    return pnl, CheckerResult(status=status, message="Realized PnL computed.")


def _risk(req: PostTradeEvaluationEvaluateRequest) -> tuple[RiskResult, CheckerResult, list[str]]:
    t = req.trade
    blockers: list[str] = []
    risk_per_share = float(t.actual_entry_price) - float(t.stop_loss)
    if risk_per_share <= 0:
        blockers.append("risk_per_share_non_positive")
        rr = RiskResult(risk_per_share=round(risk_per_share, 4), r_multiple=0.0, planned_reward_risk=0.0)
        return rr, CheckerResult(status="fail", message="Invalid risk per share (entry - stop <= 0)."), blockers

    r_multiple = (float(t.actual_exit_price) - float(t.actual_entry_price)) / risk_per_share
    planned_rr = (float(t.target_price) - float(t.actual_entry_price)) / risk_per_share
    rr = RiskResult(
        risk_per_share=round(risk_per_share, 4),
        r_multiple=round(float(r_multiple), 2),
        planned_reward_risk=round(float(planned_rr), 2),
    )
    return rr, CheckerResult(status="pass", message="R-multiple computed."), blockers


def _slippage(req: PostTradeEvaluationEvaluateRequest) -> tuple[ExecutionQualityResult, CheckerResult]:
    eq = req.execution_quality
    max_slip = float(eq.max_allowed_slippage_percent)

    entry_slip = ((float(eq.actual_entry_price) - float(eq.planned_entry_price)) / float(eq.planned_entry_price) * 100.0) if eq.planned_entry_price > 0 else 0.0
    exit_slip = ((float(eq.actual_exit_price) - float(eq.planned_exit_price)) / float(eq.planned_exit_price) * 100.0) if eq.planned_exit_price > 0 else 0.0

    abs_worst = max(abs(entry_slip), abs(exit_slip))
    if abs_worst > 2.0 * max_slip:
        status: str = "fail"
    elif abs_worst > max_slip:
        status = "warn"
    else:
        status = "pass"

    res = ExecutionQualityResult(
        entry_slippage_percent=round(float(entry_slip), 2),
        exit_slippage_percent=round(float(exit_slip), 2),
        slippage_status=status,  # type: ignore[arg-type]
    )
    msg = "Execution slippage within bounds." if status == "pass" else "Execution slippage exceeded threshold."
    return res, CheckerResult(status="pass" if status == "pass" else ("warn" if status == "warn" else "fail"), message=msg)


def _rule_compliance(req: PostTradeEvaluationEvaluateRequest) -> tuple[RuleComplianceResult, CheckerResult, list[str], bool]:
    rc = req.rule_compliance
    fields = {
        "entered_after_trigger": rc.entered_after_trigger,
        "used_approved_strategy": rc.used_approved_strategy,
        "respected_position_size": rc.respected_position_size,
        "respected_stop_loss": rc.respected_stop_loss,
        "respected_master_admin_gates": rc.respected_master_admin_gates,
        "human_approval_obtained": rc.human_approval_obtained,
    }
    failed = [k for k, v in fields.items() if not bool(v)]
    passed = [k for k, v in fields.items() if bool(v)]
    compliant = len(failed) == 0

    critical_failed = any(
        k in failed
        for k in ("used_approved_strategy", "respected_stop_loss", "respected_master_admin_gates")
    )

    res = RuleComplianceResult(compliant=compliant, failed_rules=failed, passed_rules=passed)
    status = "pass" if compliant else ("fail" if critical_failed else "warn")
    msg = "Rules complied." if compliant else "Rule compliance issues detected."
    return res, CheckerResult(status=status, message=msg), failed, critical_failed


def _outcome_label_priority(
    *,
    blocked: bool,
    exit_reason: str,
    thesis_invalid: bool,
    realized_pnl: float,
    r_multiple: float,
    late_entry: bool,
    slippage_status: str,
    critical_rule_fail: bool,
) -> OutcomeLabel:
    if blocked:
        return "rule_violation"

    # Never hide critical compliance failures behind price-based labels.
    if critical_rule_fail:
        return "rule_violation"

    # Slippage failures are also priority issues (execution quality).
    if slippage_status == "fail":
        return "slippage_issue"

    er = (exit_reason or "").strip().lower()
    if er == "target_hit":
        return "target_hit"
    if er == "stopped_out":
        return "stopped_out"
    if er == "time_stop":
        return "time_stop"

    if thesis_invalid:
        return "thesis_invalidated"

    if late_entry:
        return "late_entry"

    if realized_pnl > 0 and r_multiple >= 0.25:
        return "win"
    if realized_pnl < 0 and r_multiple <= -0.25:
        return "loss"
    if abs(r_multiple) < 0.25:
        return "flat"

    # default fallbacks
    return "flat"


def _outcome_status(label: OutcomeLabel) -> OutcomeStatus:
    if label in {"target_hit", "win"}:
        return "positive"
    if label in {"stopped_out", "loss", "fakeout", "slippage_issue"}:
        return "negative"
    if label in {"flat", "time_stop"}:
        return "neutral"
    if label in {"rule_violation", "late_entry", "thesis_invalidated"}:
        return "review_needed"
    return "blocked"


def decide_post_trade_evaluation_v1(req: PostTradeEvaluationEvaluateRequest) -> EvalDecision:
    blockers, warnings = _scope_and_validation(req)
    checkers: dict[str, CheckerResult] = {}

    pnl, pnl_chk = _pnl(req)
    risk, risk_chk, risk_blockers = _risk(req)
    blockers.extend(risk_blockers)

    eqr, eq_chk = _slippage(req)
    rc_res, rc_chk, failed_rules, critical_failed = _rule_compliance(req)

    checkers["pnl_calculator"] = pnl_chk
    checkers["r_multiple_calculator"] = risk_chk
    checkers["performance_attribution"] = CheckerResult(status="pass", message="Attribution assembled from workflow context.")
    checkers["rule_compliance_checker"] = rc_chk
    checkers["outcome_labeler"] = CheckerResult(status="pass", message="Outcome label selected by deterministic priority rules.")

    blocked = len(blockers) > 0
    thesis_invalid = bool(req.thesis_outcome.invalidation_hit) or (not bool(req.thesis_outcome.thesis_valid_at_exit))
    late_entry = not bool(req.rule_compliance.entered_after_trigger)

    label = _outcome_label_priority(
        blocked=blocked,
        exit_reason=req.trade.exit_reason,
        thesis_invalid=thesis_invalid,
        realized_pnl=float(pnl.realized_pnl),
        r_multiple=float(risk.r_multiple),
        late_entry=late_entry,
        slippage_status=str(eqr.slippage_status),
        critical_rule_fail=critical_failed,
    )

    # Special case: if slippage was fail, prefer slippage_issue unless a hard stop/target/time label already applied
    if eqr.slippage_status == "fail" and label not in {"target_hit", "stopped_out", "time_stop"} and not critical_failed:
        label = "slippage_issue"

    # crude fakeout heuristic for v1 (no tick data): stop-out + thesis invalidation suggests fakeout
    if label == "stopped_out" and thesis_invalid and late_entry:
        label = "fakeout"

    status = "blocked" if blocked else _outcome_status(label)
    if blocked:
        status = "blocked"

    # Attribution is a simple structured mapping in v1
    attribution = AttributionResult(
        primary_driver=label,
        secondary_driver="thesis_valid_at_exit" if req.thesis_outcome.thesis_valid_at_exit else "thesis_invalidated",
        session=req.workflow_context.session,
        strategy_key=req.workflow_context.strategy_key,
        trigger_key=req.workflow_context.trigger_key,
    )

    if blocked:
        allowed_next = []
        next_action = "Fix blockers before using post-trade outcome in learning workflows."
    else:
        allowed_next = ["learning_loop"]
        next_action = "Send outcome metrics to Stage 14 Learning Loop."

    # Include an execution-quality warning when slippage is warn/fail
    if eqr.slippage_status in {"warn", "fail"}:
        warnings.append("slippage_exceeded_threshold")

    return EvalDecision(
        outcome_label=label,
        outcome_status=status,  # type: ignore[arg-type]
        pnl=pnl,
        risk_result=risk,
        execution_quality_result=eqr,
        rule_compliance_result=rc_res,
        attribution=attribution,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
        checkers=checkers,
        allowed_next_stages=allowed_next,
        next_action=next_action,
    )

