from __future__ import annotations

from dataclasses import dataclass

from app.services.learning_loop.models import (
    CheckerResult,
    CurrentStatus,
    DriftInfo,
    LearningAction,
    LearningLoopEvaluateRequest,
    LearningMetrics,
    PromotionInfo,
    DemotionInfo,
)


@dataclass(frozen=True)
class Decision:
    learning_action: LearningAction
    metrics: LearningMetrics
    drift: DriftInfo
    promotion: PromotionInfo
    demotion: DemotionInfo
    reason: str
    blockers: list[str]
    warnings: list[str]
    checkers: dict[str, CheckerResult]
    allowed_next_stages: list[str]
    next_action: str


def _safe_mean(xs: list[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else 0.0


def _metrics(req: LearningLoopEvaluateRequest) -> LearningMetrics:
    outs = req.recent_outcomes
    total = len(outs)
    wins = 0
    losses = 0
    flats = 0
    for o in outs:
        lbl = (o.outcome_label or "").strip().lower()
        st = (o.outcome_status or "").strip().lower()
        if st == "positive" or lbl in {"target_hit", "win"}:
            wins += 1
        elif st == "negative" or lbl in {"stopped_out", "loss", "fakeout", "slippage_issue"}:
            losses += 1
        elif st == "neutral" or lbl in {"flat", "time_stop"}:
            flats += 1
        else:
            # treat unknown as flat/neutral for win-rate purposes
            flats += 1

    win_rate = (wins / float(total)) if total > 0 else 0.0
    avg_r = _safe_mean([float(o.r_multiple) for o in outs])
    avg_pnl = _safe_mean([float(o.realized_pnl) for o in outs])

    rule_violation_rate = (sum(1 for o in outs if not bool(o.rule_compliant)) / float(total)) if total > 0 else 0.0
    slippage_fail_rate = (sum(1 for o in outs if str(o.slippage_status) == "fail") / float(total)) if total > 0 else 0.0

    sample_size = req.current_status.sample_size if (req.current_status.sample_size is not None and req.current_status.sample_size > 0) else total

    return LearningMetrics(
        sample_size=int(sample_size),
        wins=int(wins),
        losses=int(losses),
        flats=int(flats),
        win_rate=round(float(win_rate), 4),
        avg_r_multiple=round(float(avg_r), 3),
        avg_realized_pnl=round(float(avg_pnl), 2),
        rule_violation_rate=round(float(rule_violation_rate), 4),
        slippage_fail_rate=round(float(slippage_fail_rate), 4),
        current_drawdown_r=req.current_status.current_drawdown_r,
    )


def _drift(metrics: LearningMetrics, status: CurrentStatus, req: LearningLoopEvaluateRequest) -> DriftInfo:
    thr = req.thresholds
    if status.current_drawdown_r is not None and float(status.current_drawdown_r) <= float(thr.max_drawdown_r_before_demotion):
        return DriftInfo(drift_detected=True, drift_reason="drawdown_breach")
    if status.last_10_avg_r is not None and metrics.sample_size >= 10 and float(status.last_10_avg_r) < 0:
        return DriftInfo(drift_detected=True, drift_reason="last_10_avg_r_negative")
    if metrics.rule_violation_rate > float(thr.max_rule_violation_rate):
        return DriftInfo(drift_detected=True, drift_reason="rule_violation_rate_high")
    if metrics.slippage_fail_rate > float(thr.max_slippage_fail_rate):
        return DriftInfo(drift_detected=True, drift_reason="slippage_fail_rate_high")
    return DriftInfo(drift_detected=False, drift_reason=None)


def decide_learning_loop_v1(req: LearningLoopEvaluateRequest) -> Decision:
    blockers: list[str] = []
    warnings: list[str] = []
    checkers: dict[str, CheckerResult] = {}

    # A) Scope blockers
    if req.asset_class.strip().lower() != "stock":
        blockers.append("asset_class_not_supported")
    if req.horizon.strip().lower() != "day_trading":
        blockers.append("horizon_not_supported")

    # B) Validation
    if not req.recent_outcomes:
        blockers.append("no_recent_outcomes")

    metrics = _metrics(req)
    drift = _drift(metrics, req.current_status, req)

    checkers["learning_metrics_updater"] = CheckerResult(status="pass", message="Rolling metrics computed from recent outcomes.")
    checkers["drift_detector"] = CheckerResult(status="fail" if drift.drift_detected else "pass", message="Drift checks evaluated.")
    checkers["promotion_demotion_rules"] = CheckerResult(status="pass", message="Promotion/demotion rules evaluated.")
    checkers["learning_loop_agent"] = CheckerResult(status="pass", message="Learning-loop recommendation produced (no auto-write).")

    # If scope/validation block, return review_needed/block_strategy
    if blockers:
        action: LearningAction = "block_strategy" if "asset_class_not_supported" in blockers else "review_needed"
        reason = "Blocked by scope or missing outcome data."
        next_action = "Provide valid stock/day-trading outcomes to evaluate learning decision."
        return Decision(
            learning_action=action,
            metrics=metrics,
            drift=DriftInfo(drift_detected=True, drift_reason="blocked"),
            promotion=PromotionInfo(eligible_for_promotion=False, promotion_target=None, blocked_reasons=sorted(set(blockers))),
            demotion=DemotionInfo(demotion_required=False, demotion_target=None, reasons=[]),
            reason=reason,
            blockers=sorted(set(blockers)),
            warnings=[],
            checkers=checkers,
            allowed_next_stages=["strategy_governance_review"],
            next_action=next_action,
        )

    thr = req.thresholds

    # E) Demotion
    demotion_required = False
    demotion_target: str | None = None
    demotion_reasons: list[str] = []

    if req.current_status.current_drawdown_r is not None and float(req.current_status.current_drawdown_r) <= float(thr.max_drawdown_r_before_demotion):
        demotion_required = True
        demotion_target = "demote_to_paper"
        demotion_reasons.append("drawdown_breach")

    if metrics.rule_violation_rate > float(thr.max_rule_violation_rate):
        demotion_required = True
        demotion_target = "demote_to_research"
        demotion_reasons.append("rule_violation_rate_high")

    if metrics.slippage_fail_rate > float(thr.max_slippage_fail_rate):
        demotion_required = True
        demotion_target = "demote_to_research"
        demotion_reasons.append("slippage_fail_rate_high")

    if metrics.sample_size >= int(thr.min_sample_size_for_promotion) and float(metrics.avg_r_multiple) < 0:
        demotion_required = True
        demotion_target = "demote_to_research"
        demotion_reasons.append("avg_r_negative_with_sufficient_sample")

    # F) Promotion eligibility (never live in v1)
    promo_blocked: list[str] = []
    if metrics.sample_size < int(thr.min_sample_size_for_promotion):
        promo_blocked.append("sample_size_below_threshold")
        warnings.append("sample_size_below_threshold")
    if float(metrics.avg_r_multiple) < float(thr.min_avg_r_for_promotion):
        promo_blocked.append("avg_r_below_threshold")
    if drift.drift_detected:
        promo_blocked.append("drift_detected")
    if metrics.rule_violation_rate > float(thr.max_rule_violation_rate):
        promo_blocked.append("rule_violation_rate_high")
    if metrics.slippage_fail_rate > float(thr.max_slippage_fail_rate):
        promo_blocked.append("slippage_fail_rate_high")

    eligible_for_promotion = len(promo_blocked) == 0
    promotion_target = "production_candidate" if eligible_for_promotion else None

    promotion = PromotionInfo(
        eligible_for_promotion=eligible_for_promotion,
        promotion_target=promotion_target,
        blocked_reasons=sorted(set(promo_blocked)),
    )
    demotion = DemotionInfo(
        demotion_required=demotion_required,
        demotion_target=demotion_target,
        reasons=sorted(set(demotion_reasons)),
    )

    # G) Learning action priority
    if demotion_required:
        action = "demote_to_research" if demotion_target == "demote_to_research" else "demote_to_paper"
        reason = "Demotion required based on drift/risk/compliance thresholds."
        next_action = "Route to strategy governance for demotion decision and mitigation plan."
    elif eligible_for_promotion:
        action = "promote_candidate"
        reason = "Promotion candidate: thresholds met with no drift detected."
        next_action = "Route to strategy governance to approve promotion candidate (no auto-promotion in v1)."
    elif metrics.sample_size < int(thr.min_sample_size_for_promotion):
        action = "keep_monitoring"
        reason = "Insufficient sample size for promotion; continue monitoring."
        next_action = "Continue monitoring until sample size threshold is reached."
    else:
        action = "keep_monitoring"
        reason = "Metrics do not justify promotion or demotion; keep monitoring."
        next_action = "Continue monitoring outcomes and reassess periodically."

    allowed_next = ["strategy_governance_review"]
    return Decision(
        learning_action=action,
        metrics=metrics,
        drift=drift,
        promotion=promotion,
        demotion=demotion,
        reason=reason,
        blockers=[],
        warnings=sorted(set(warnings)),
        checkers=checkers,
        allowed_next_stages=allowed_next,
        next_action=next_action,
    )

