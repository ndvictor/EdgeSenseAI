from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.trigger_monitoring.models import (
    CheckerResult,
    TriggerEvaluation,
    TriggerMonitoringEvaluateRequest,
    TriggerState,
    TimingInfo,
)


CT_TZ = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class RuleDecision:
    trigger_state: TriggerState
    reason: str
    requirements_passed: list[str]
    requirements_failed: list[str]
    blockers: list[str]
    warnings: list[str]
    checkers: dict[str, CheckerResult]
    next_action: str
    timing: TimingInfo


def _parse_iso_to_aware(iso_str: str) -> datetime:
    """
    Parse ISO string into tz-aware datetime.

    - If input is naive, interpret as America/Chicago for deterministic v1 behavior.
    """
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CT_TZ)
    return dt


def evaluate_timing_window(*, created_at: str, expires_at: str, evaluated_at: str) -> tuple[TimingInfo, CheckerResult]:
    try:
        created = _parse_iso_to_aware(created_at)
        expires = _parse_iso_to_aware(expires_at)
        evaluated = _parse_iso_to_aware(evaluated_at)
    except Exception as e:
        timing = TimingInfo(
            created_at=created_at,
            expires_at=expires_at,
            evaluated_at=evaluated_at,
            seconds_to_expiration=0,
            is_expired=True,
            is_within_window=False,
        )
        return timing, CheckerResult(status="fail", message=f"Failed to parse timestamps: {e}")

    seconds_to_exp = int((expires - evaluated).total_seconds())
    is_expired = evaluated > expires or seconds_to_exp <= 0
    is_within = (evaluated >= created) and (evaluated <= expires) and (not is_expired)

    timing = TimingInfo(
        created_at=created.isoformat(),
        expires_at=expires.isoformat(),
        evaluated_at=evaluated.isoformat(),
        seconds_to_expiration=seconds_to_exp,
        is_expired=is_expired,
        is_within_window=is_within,
    )
    status = "pass" if is_within else ("warn" if not is_expired else "fail")
    msg = "Within trigger timing window." if is_within else ("Trigger expired." if is_expired else "Outside trigger window (not expired).")
    return timing, CheckerResult(status=status, message=msg)


def evaluate_signal_expiration(timing: TimingInfo) -> CheckerResult:
    if timing.is_expired:
        return CheckerResult(status="fail", message="Trigger is expired based on evaluated_at vs expires_at.")
    if timing.seconds_to_expiration <= 60:
        return CheckerResult(status="warn", message="Trigger is near expiration (≤ 60s).")
    return CheckerResult(status="pass", message="Trigger not expired.")


def evaluate_eligibility_dependency(req: TriggerMonitoringEvaluateRequest) -> CheckerResult:
    ctx = req.eligibility_context
    if ctx.eligible:
        return CheckerResult(status="pass", message="Eligibility passed.")

    if ctx.eligibility_status == "paper_only":
        return CheckerResult(status="warn", message="Eligibility is paper_only; trigger may arm for paper-first monitoring.")
    return CheckerResult(status="fail", message=f"Eligibility blocked by status '{ctx.eligibility_status}'.")


def evaluate_trigger_conditions(req: TriggerMonitoringEvaluateRequest) -> CheckerResult:
    s = req.current_state
    # This checker is only about condition booleans, not eligibility/timing gates.
    if s.invalidation_hit:
        return CheckerResult(status="fail", message="Invalidation condition was hit.")
    if s.price_above_trigger and s.price_above_vwap and s.volume_confirms and s.spread_pass and s.data_quality == "pass":
        return CheckerResult(status="pass", message="Trigger conditions are satisfied.")
    if s.price_above_trigger and (not s.volume_confirms or not s.price_above_vwap):
        return CheckerResult(status="warn", message="Price is above trigger but confirmations are missing.")
    return CheckerResult(status="warn", message="Trigger conditions not yet satisfied.")


def decide_trigger_state_v1(req: TriggerMonitoringEvaluateRequest) -> RuleDecision:
    passed: list[str] = []
    failed: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    # A) Scope blockers
    if req.trigger_candidate.asset_class != "stock":
        timing, time_eval = evaluate_timing_window(
            created_at=req.trigger_candidate.created_at,
            expires_at=req.trigger_candidate.expires_at,
            evaluated_at=req.current_state.evaluated_at,
        )
        checkers = {
            "eligibility_dependency_checker": CheckerResult(status="fail", message="Scope blocked."),
            "timing_window_checker": time_eval,
            "signal_expiration_checker": evaluate_signal_expiration(timing),
            "trigger_condition_checker": CheckerResult(status="warn", message="Not evaluated (scope blocked)."),
        }
        blockers.append("asset_class_not_supported")
        return RuleDecision(
            trigger_state="blocked",
            reason="Stage 8 v1 supports US stocks only.",
            requirements_passed=[],
            requirements_failed=["asset_scope_stock_only"],
            blockers=blockers,
            warnings=warnings,
            checkers=checkers,
            next_action="Use stock asset_class or extend trigger monitoring scope.",
            timing=timing,
        )

    if req.trigger_candidate.horizon != "day_trading":
        timing, time_eval = evaluate_timing_window(
            created_at=req.trigger_candidate.created_at,
            expires_at=req.trigger_candidate.expires_at,
            evaluated_at=req.current_state.evaluated_at,
        )
        checkers = {
            "eligibility_dependency_checker": CheckerResult(status="fail", message="Scope blocked."),
            "timing_window_checker": time_eval,
            "signal_expiration_checker": evaluate_signal_expiration(timing),
            "trigger_condition_checker": CheckerResult(status="warn", message="Not evaluated (scope blocked)."),
        }
        blockers.append("horizon_not_supported")
        return RuleDecision(
            trigger_state="blocked",
            reason="Stage 8 v1 supports day trading only.",
            requirements_passed=[],
            requirements_failed=["horizon_scope_day_trading_only"],
            blockers=blockers,
            warnings=warnings,
            checkers=checkers,
            next_action="Use day_trading horizon or extend trigger monitoring scope.",
            timing=timing,
        )

    # D) Timing + expiration
    timing, timing_eval = evaluate_timing_window(
        created_at=req.trigger_candidate.created_at,
        expires_at=req.trigger_candidate.expires_at,
        evaluated_at=req.current_state.evaluated_at,
    )
    expiration_eval = evaluate_signal_expiration(timing)

    # B) Eligibility dependency
    elig_eval = evaluate_eligibility_dependency(req)

    # C) Data and spread blockers
    if req.current_state.data_quality == "fail":
        blockers.append("data_quality_fail")
        failed.append("data_quality_pass")
    else:
        passed.append("data_quality_pass")
        if req.current_state.data_quality == "warn":
            warnings.append("data_quality_warn")

    if not req.current_state.spread_pass:
        blockers.append("spread_fail")
        failed.append("spread_pass")
    else:
        passed.append("spread_pass")

    # E) Invalidation
    if req.current_state.invalidation_hit:
        failed.append("invalidation_clear")
        return RuleDecision(
            trigger_state="invalidated",
            reason="Invalidation condition hit; do not proceed.",
            requirements_passed=passed,
            requirements_failed=failed + ["invalidation_clear"],
            blockers=blockers,
            warnings=warnings,
            checkers={
                "eligibility_dependency_checker": elig_eval,
                "timing_window_checker": timing_eval,
                "signal_expiration_checker": expiration_eval,
                "trigger_condition_checker": CheckerResult(status="fail", message="Invalidation hit."),
            },
            next_action="Wait for a new valid trigger candidate or rebuild trigger rules.",
            timing=timing,
        )

    # Expired
    if timing.is_expired:
        failed.append("not_expired")
        return RuleDecision(
            trigger_state="expired",
            reason="Trigger expired before it could fire.",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=blockers,
            warnings=warnings,
            checkers={
                "eligibility_dependency_checker": elig_eval,
                "timing_window_checker": timing_eval,
                "signal_expiration_checker": expiration_eval,
                "trigger_condition_checker": CheckerResult(status="warn", message="Not evaluated (expired)."),
            },
            next_action="Build/refresh trigger rules and continue monitoring.",
            timing=timing,
        )

    # Eligibility blocked
    if not req.eligibility_context.eligible:
        if req.eligibility_context.eligibility_status == "paper_only":
            warnings.append("paper_only_eligibility")
        else:
            blockers.append("eligibility_blocked")
        return RuleDecision(
            trigger_state="blocked" if req.eligibility_context.eligibility_status in {"research_only", "blocked"} else "armed",
            reason=(
                "Eligibility blocked; do not proceed."
                if req.eligibility_context.eligibility_status in {"research_only", "blocked"}
                else "Eligibility is paper_only; keeping trigger armed for paper-first monitoring."
            ),
            requirements_passed=passed,
            requirements_failed=failed + (["eligibility_passed"] if req.eligibility_context.eligibility_status in {"research_only", "blocked"} else []),
            blockers=blockers,
            warnings=warnings,
            checkers={
                "eligibility_dependency_checker": elig_eval,
                "timing_window_checker": timing_eval,
                "signal_expiration_checker": expiration_eval,
                "trigger_condition_checker": evaluate_trigger_conditions(req),
            },
            next_action=(
                "Resolve eligibility blockers before execution planning."
                if req.eligibility_context.eligibility_status in {"research_only", "blocked"}
                else "Continue monitoring in paper-first mode."
            ),
            timing=timing,
        )

    passed.append("eligibility_passed")

    # F) Fired trigger
    s = req.current_state
    conds = [
        ("volume_confirms", s.volume_confirms),
        ("price_above_trigger", s.price_above_trigger),
        ("price_above_vwap", s.price_above_vwap),
    ]
    for key, ok in conds:
        if ok:
            passed.append(key)
        else:
            failed.append(key)

    if (
        req.eligibility_context.eligible
        and (not timing.is_expired)
        and s.data_quality == "pass"
        and s.spread_pass
        and s.volume_confirms
        and s.price_above_trigger
        and s.price_above_vwap
        and (not s.invalidation_hit)
    ):
        return RuleDecision(
            trigger_state="fired",
            reason="Trigger conditions satisfied and gates pass.",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=blockers,
            warnings=warnings,
            checkers={
                "eligibility_dependency_checker": elig_eval,
                "timing_window_checker": timing_eval,
                "signal_expiration_checker": expiration_eval,
                "trigger_condition_checker": CheckerResult(status="pass", message="Trigger fired."),
            },
            next_action="Send fired trigger to Stage 9 Execution Planner.",
            timing=timing,
        )

    # H) Missed trigger (v1 special case)
    if s.price_above_trigger and (not s.price_above_vwap) and (not s.volume_confirms):
        warnings.append("missed_confirmations")
        return RuleDecision(
            trigger_state="missed",
            reason="Price moved above trigger but confirmations failed (vwap + volume).",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=blockers,
            warnings=warnings,
            checkers={
                "eligibility_dependency_checker": elig_eval,
                "timing_window_checker": timing_eval,
                "signal_expiration_checker": expiration_eval,
                "trigger_condition_checker": CheckerResult(status="warn", message="Missed confirmation requirements."),
            },
            next_action="Wait for a cleaner setup or rebuild trigger rules.",
            timing=timing,
        )

    # G) Armed trigger
    if s.data_quality in {"pass", "warn"} and s.spread_pass:
        return RuleDecision(
            trigger_state="armed",
            reason="Trigger is valid and within window, but conditions have not fully fired yet.",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=blockers,
            warnings=warnings,
            checkers={
                "eligibility_dependency_checker": elig_eval,
                "timing_window_checker": timing_eval,
                "signal_expiration_checker": expiration_eval,
                "trigger_condition_checker": evaluate_trigger_conditions(req),
            },
            next_action="Continue monitoring trigger until it fires, expires, or invalidates.",
            timing=timing,
        )

    # I) Not ready (default)
    return RuleDecision(
        trigger_state="not_ready",
        reason="Trigger is not ready for execution planning.",
        requirements_passed=passed,
        requirements_failed=failed,
        blockers=blockers,
        warnings=warnings,
        checkers={
            "eligibility_dependency_checker": elig_eval,
            "timing_window_checker": timing_eval,
            "signal_expiration_checker": expiration_eval,
            "trigger_condition_checker": evaluate_trigger_conditions(req),
        },
        next_action="Continue monitoring or adjust trigger inputs.",
        timing=timing,
    )


def build_trigger_evaluation(
    *,
    evaluation_id: str,
    created_at: str,
    req: TriggerMonitoringEvaluateRequest,
    decision: RuleDecision,
) -> TriggerEvaluation:
    return TriggerEvaluation(
        evaluation_id=evaluation_id,
        symbol=req.trigger_candidate.symbol,
        asset_class=req.trigger_candidate.asset_class,
        horizon=req.trigger_candidate.horizon,
        trigger_key=req.trigger_candidate.trigger_key,
        trigger_state=decision.trigger_state,
        reason=decision.reason,
        timing=decision.timing,
        requirements_passed=decision.requirements_passed,
        requirements_failed=decision.requirements_failed,
        blockers=decision.blockers,
        warnings=decision.warnings,
        checkers=decision.checkers,
        next_action=decision.next_action,
        created_at=created_at,
    )

