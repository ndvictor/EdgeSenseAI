from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.effective_runtime import effective_bool
from app.services.position_monitoring.models import (
    CheckerResult,
    PositionEvaluation,
    PositionMonitoringEvaluateRequest,
    PositionStatus,
    BlockedStage,
    ThesisValidity,
)


CT_TZ = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class EvalDecision:
    position_status: PositionStatus
    recommended_action: str
    pnl: dict
    risk: dict
    thesis_validity: ThesisValidity
    blockers: list[str]
    warnings: list[str]
    checkers: dict[str, CheckerResult]
    next_action: str
    blocked_next_stages: list[BlockedStage]


def _parse_iso_to_aware(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CT_TZ)
    return dt


def _pnl_long(quantity: float, entry: float, current: float, stop_loss: float | None) -> tuple[dict, CheckerResult]:
    unreal = (current - entry) * quantity
    unreal_pct = ((current - entry) / entry * 100.0) if entry > 0 else 0.0
    risk_per_share = (entry - stop_loss) if (stop_loss is not None and stop_loss > 0) else None
    r_mult = ((current - entry) / risk_per_share) if (risk_per_share and risk_per_share > 0) else 0.0
    pnl = {
        "unrealized_pnl": round(unreal, 2),
        "unrealized_pnl_percent": round(unreal_pct, 2),
        "r_multiple": round(float(r_mult), 2),
    }
    status = "pass" if entry > 0 and current > 0 and quantity > 0 else "fail"
    msg = "PnL computed." if status == "pass" else "Invalid position inputs for PnL."
    return pnl, CheckerResult(status=status, message=msg)


def _thesis_validity(req: PositionMonitoringEvaluateRequest) -> tuple[ThesisValidity, CheckerResult]:
    t = req.thesis
    failed: list[str] = []
    passed: list[str] = []

    if t.invalidation_hit:
        failed.append("invalidation_hit")
    else:
        passed.append("invalidation_clear")
    if t.price_above_vwap:
        passed.append("price_above_vwap")
    else:
        failed.append("price_below_vwap")
    if t.volume_confirms:
        passed.append("volume_confirms")
    else:
        failed.append("volume_not_confirmed")
    if t.relative_strength_positive:
        passed.append("relative_strength_positive")
    else:
        failed.append("relative_strength_negative")

    score = 1.0
    for _ in failed:
        score -= 0.25
    if t.invalidation_hit:
        score = min(score, 0.25)
    score = max(0.0, min(1.0, score))

    valid = (not t.invalidation_hit) and t.price_above_vwap and t.volume_confirms and t.relative_strength_positive
    tv = ThesisValidity(valid=valid, score=round(score, 2), failed_reasons=failed, passed_reasons=passed)

    if t.invalidation_hit:
        return tv, CheckerResult(status="fail", message="Thesis invalidated.")
    if len(failed) >= 2:
        return tv, CheckerResult(status="warn", message="Multiple thesis signals failed.")
    return tv, CheckerResult(status="pass" if valid else "warn", message="Thesis evaluated.")


def _risk_monitor(req: PositionMonitoringEvaluateRequest, pnl: dict) -> tuple[dict, CheckerResult, list[str], list[str], str]:
    p = req.position
    r = req.risk_state
    prefs = req.monitoring_preferences

    blockers: list[str] = []
    warnings: list[str] = []
    recommended_action = "hold"

    # Master admin + risk state gates (no broker calls)
    emergency = bool(r.emergency_stop) or effective_bool("EMERGENCY_STOP")
    force_close = bool(r.force_close_requested) or effective_bool("FORCE_CLOSE_REQUESTED")

    position_notional = float(p.current_price) * float(p.quantity)
    pos_pct = (position_notional / float(r.account_equity) * 100.0) if r.account_equity > 0 else 0.0

    risk_per_share = (float(p.entry_price) - float(p.stop_loss)) if p.stop_loss and p.stop_loss > 0 else 0.0
    dist_to_stop = (float(p.current_price) - float(p.stop_loss)) if p.stop_loss and p.stop_loss > 0 else None
    dist_to_target = (float(p.target_price) - float(p.current_price)) if p.target_price and p.target_price > 0 else None

    risk_info = {
        "risk_per_share": round(float(risk_per_share), 2),
        "current_distance_to_stop": round(dist_to_stop, 2) if dist_to_stop is not None else None,
        "distance_to_target": round(dist_to_target, 2) if dist_to_target is not None else None,
        "position_notional": round(position_notional, 2),
        "position_size_percent": round(pos_pct, 2),
        "daily_loss_percent": float(r.current_daily_loss_percent),
    }

    if emergency:
        blockers.append("emergency_stop_active")
        recommended_action = "blocked"
    if force_close:
        warnings.append("force_close_requested")
        recommended_action = "exit_review"
    if r.current_daily_loss_percent >= r.max_daily_loss_percent:
        warnings.append("daily_loss_limit_reached")
        recommended_action = "exit_review"
    if pos_pct > r.max_position_size_percent:
        warnings.append("position_size_exceeds_max")
        recommended_action = "reduce"
    if p.stop_loss is not None and p.current_price <= p.stop_loss:
        warnings.append("stop_loss_touched")
        recommended_action = "exit_review"
    if p.target_price is not None and p.current_price >= p.target_price:
        warnings.append("target_reached")
        recommended_action = "reduce"
    if float(pnl.get("r_multiple", 0.0)) >= float(prefs.reduce_at_r_multiple):
        warnings.append("r_multiple_reduce_threshold")
        recommended_action = "reduce"

    status = "pass" if not blockers else "fail"
    msg = "Risk evaluated." if status == "pass" else "Blocked by master-admin or risk state."
    return risk_info, CheckerResult(status=status, message=msg), blockers, warnings, recommended_action


def decide_position_monitoring_v1(req: PositionMonitoringEvaluateRequest) -> EvalDecision:
    blockers: list[str] = []
    warnings: list[str] = []
    checkers: dict[str, CheckerResult] = {}

    p = req.position

    # A) Scope blockers
    if p.asset_class.strip().lower() != "stock":
        blockers.append("asset_class_not_supported")
    if p.horizon.strip().lower() != "day_trading":
        blockers.append("horizon_not_supported")

    # B) Position validation blockers
    if p.quantity <= 0:
        blockers.append("quantity_not_positive")
    if p.entry_price <= 0:
        blockers.append("entry_price_invalid")
    if p.current_price <= 0:
        blockers.append("current_price_invalid")
    if p.side != "long":
        blockers.append("side_not_supported_v1")

    if p.stop_loss is None or p.stop_loss <= 0:
        warnings.append("stop_loss_missing_or_invalid")

    pnl, pnl_eval = _pnl_long(p.quantity, p.entry_price, p.current_price, p.stop_loss)
    checkers["pnl_calculator"] = pnl_eval

    thesis_validity, thesis_eval = _thesis_validity(req)
    checkers["thesis_validity_checker"] = thesis_eval

    risk_info, risk_eval, risk_blockers, risk_warnings, risk_action = _risk_monitor(req, pnl)
    checkers["position_risk_monitor"] = risk_eval
    blockers.extend(risk_blockers)
    warnings.extend(risk_warnings)

    # F) Time stop
    minutes_open = None
    try:
        opened = _parse_iso_to_aware(p.opened_at)
        evaluated = _parse_iso_to_aware(req.evaluated_at)
        minutes_open = int((evaluated - opened).total_seconds() / 60)
    except Exception:
        warnings.append("time_parse_failed")

    if minutes_open is not None:
        if minutes_open >= req.monitoring_preferences.time_stop_minutes and float(pnl["r_multiple"]) < 0.5:
            warnings.append("time_stop_triggered")
            risk_action = "exit_review"
        elif minutes_open >= max(0, req.monitoring_preferences.time_stop_minutes - 5) and thesis_validity.valid:
            warnings.append("near_time_stop_watch")
            if risk_action == "hold":
                risk_action = "watch"

    # Thesis invalid -> exit_review (if configured)
    if req.monitoring_preferences.exit_at_thesis_invalid and (not thesis_validity.valid):
        if req.thesis.invalidation_hit:
            warnings.append("thesis_invalidated")
            risk_action = "exit_review"
        elif len(thesis_validity.failed_reasons) >= 2:
            warnings.append("thesis_weak")
            if risk_action == "hold":
                risk_action = "watch"

    # G) Output mapping
    if blockers:
        position_status: PositionStatus = "blocked" if "emergency_stop_active" in blockers else "exit_review"
        if "asset_class_not_supported" in blockers or "horizon_not_supported" in blockers or "quantity_not_positive" in blockers:
            position_status = "blocked"
            risk_action = "blocked"
        next_action = "Fix blockers before monitoring position."
        blocked_next = [BlockedStage(stage="close_position", reason="Position monitoring is blocked.")]
    elif risk_action == "exit_review":
        position_status = "exit_review"
        next_action = "Review position for exit. Stage 12 close position is not automated in v1."
        blocked_next = []
    elif risk_action == "reduce":
        position_status = "warning"
        next_action = "Consider reducing position size; continue monitoring."
        blocked_next = [BlockedStage(stage="close_position", reason="No close-position review required.")]
    elif risk_action == "watch":
        position_status = "warning"
        next_action = "Watch position closely; continue monitoring."
        blocked_next = [BlockedStage(stage="close_position", reason="No close-position review required.")]
    else:
        position_status = "healthy"
        next_action = "Continue monitoring position."
        blocked_next = [BlockedStage(stage="close_position", reason="No close-position review required.")]

    # Master admin checker (visibility only)
    checkers["master_admin_gate"] = CheckerResult(
        status="fail" if effective_bool("EMERGENCY_STOP") else "pass",
        message="Runtime master-admin gates checked (no broker calls).",
    )

    return EvalDecision(
        position_status=position_status,
        recommended_action=risk_action,
        pnl=pnl,
        risk=risk_info,
        thesis_validity=thesis_validity,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
        checkers=checkers,
        next_action=next_action,
        blocked_next_stages=blocked_next,
    )


def build_position_evaluation(
    *,
    evaluation_id: str,
    created_at: str,
    req: PositionMonitoringEvaluateRequest,
    decision: EvalDecision,
) -> PositionEvaluation:
    return PositionEvaluation(
        evaluation_id=evaluation_id,
        position_id=req.position.position_id,
        symbol=req.position.symbol,
        asset_class=req.position.asset_class,
        horizon=req.position.horizon,
        position_status=decision.position_status,
        recommended_action=decision.recommended_action,  # type: ignore[arg-type]
        pnl=decision.pnl,
        risk=decision.risk,
        thesis_validity=decision.thesis_validity,
        blockers=decision.blockers,
        warnings=decision.warnings,
        checkers=decision.checkers,
        blocked_next_stages=decision.blocked_next_stages,
        next_action=decision.next_action,
        created_at=created_at,
    )

