from __future__ import annotations

from dataclasses import dataclass
from math import floor

from app.core.effective_runtime import effective_bool
from app.services.execution_planner.models import (
    AccountState,
    CheckerResult,
    ExecutionPlan,
    ExecutionPlannerPlanRequest,
    ExecutionReadiness,
    MarketSnapshot,
)


@dataclass(frozen=True)
class PlanDecision:
    plan_status: str
    blockers: list[str]
    warnings: list[str]
    checkers: dict[str, CheckerResult]
    allowed_next_stages: list[str]
    next_action: str


def _master_admin_readiness(account: AccountState) -> ExecutionReadiness:
    """
    Read effective runtime gates (runtime_settings.json > env > defaults) and
    populate Stage-9 readiness flags.

    v1: we respect master-admin runtime settings even if request.account_state differs,
    because those settings represent the control plane.
    """
    workflow_enabled = effective_bool("WORKFLOW_ENABLED")
    # Combine control-plane (effective runtime) with caller-provided account gating for v1 determinism.
    # If either blocks execution, Stage 9 must not allow progression.
    execution_enabled = effective_bool("EXECUTION_ENABLED") and bool(account.execution_enabled)
    emergency_stop = effective_bool("EMERGENCY_STOP")
    force_close_requested = effective_bool("FORCE_CLOSE_REQUESTED")
    paper_trading_enabled = effective_bool("PAPER_TRADING_ENABLED") and bool(account.paper_trading_enabled)
    live_trading_enabled = effective_bool("LIVE_TRADING_ENABLED") and bool(account.live_trading_enabled)
    broker_execution_enabled = effective_bool("BROKER_EXECUTION_ENABLED")
    # If either the control-plane or the account requires approval, treat as required.
    human_approval_required = effective_bool("REQUIRE_HUMAN_APPROVAL") or bool(account.human_approval_required)

    # slippage pass is conservative placeholder in v1 (no external models here)
    return ExecutionReadiness(
        spread_pass=True,
        slippage_pass=True,
        workflow_enabled=workflow_enabled,
        execution_enabled=execution_enabled,
        paper_trading_enabled=paper_trading_enabled,
        live_trading_enabled=live_trading_enabled,
        broker_execution_enabled=broker_execution_enabled,
        human_approval_required=human_approval_required,
        emergency_stop=emergency_stop,
        force_close_requested=force_close_requested,
    )


def _compute_stop_target(snapshot: MarketSnapshot, target_rr: float, atr_mult: float) -> tuple[float, float, float, float, float]:
    # D) Stop/target (long buy v1)
    risk_per_share = float(atr_mult) * float(snapshot.atr)
    stop_loss = float(snapshot.current_price) - risk_per_share
    reward_per_share = float(target_rr) * risk_per_share
    target_price = float(snapshot.current_price) + reward_per_share
    rr = (reward_per_share / risk_per_share) if risk_per_share > 0 else 0.0
    return stop_loss, target_price, risk_per_share, reward_per_share, rr


def _compute_sizing(account: AccountState, snapshot: MarketSnapshot, risk_per_share: float) -> tuple[int, float, float, float, str, list[str]]:
    warnings: list[str] = []
    equity = float(account.account_equity)
    max_dollar_risk = equity * float(account.max_risk_per_trade_percent) / 100.0
    max_allowed_notional = equity * float(account.max_position_size_percent) / 100.0

    qty_by_risk = int(floor(max_dollar_risk / risk_per_share)) if risk_per_share > 0 else 0
    notional_by_risk = qty_by_risk * float(snapshot.current_price)

    qty_final = qty_by_risk
    sizing_status = "ok"
    if notional_by_risk > max_allowed_notional and snapshot.current_price > 0:
        qty_final = int(floor(max_allowed_notional / float(snapshot.current_price)))
        sizing_status = "capped"
        warnings.append("quantity_capped_by_max_position_size")

    planned_notional = qty_final * float(snapshot.current_price)
    pos_pct = (planned_notional / equity * 100.0) if equity > 0 else 0.0
    return qty_final, planned_notional, pos_pct, max_allowed_notional, sizing_status, warnings


def _select_order_type(snapshot: MarketSnapshot, prefs_order_style: str) -> tuple[str, float | None, list[str]]:
    warnings: list[str] = []
    style = (prefs_order_style or "limit").strip().lower()
    if style not in {"limit", "market"}:
        style = "limit"
        warnings.append("order_style_unknown_defaulted_to_limit")
    if style == "market":
        return "market", None, warnings
    # limit buy: ask if provided else current_price
    limit_price = float(snapshot.ask) if snapshot.ask is not None else float(snapshot.current_price)
    return "limit", limit_price, warnings


def decide_plan_v1(request: ExecutionPlannerPlanRequest) -> tuple[PlanDecision, ExecutionReadiness, dict]:
    blockers: list[str] = []
    warnings: list[str] = []
    checkers: dict[str, CheckerResult] = {}

    # A) Scope blockers
    asset_class = (request.trigger_evaluation.asset_class or "").strip().lower()
    horizon = (request.trigger_evaluation.horizon or "").strip().lower()
    if asset_class != "stock":
        blockers.append("asset_class_not_supported")
    if horizon != "day_trading":
        blockers.append("horizon_not_supported")

    # B) Trigger dependency
    if (request.trigger_evaluation.trigger_state or "").strip().lower() != "fired":
        blockers.append("trigger_not_fired")

    # C) Data/risk blockers
    if not request.account_state.risk_budget_available:
        blockers.append("risk_budget_unavailable")
    if request.market_snapshot.current_price <= 0:
        blockers.append("invalid_current_price")
    if request.market_snapshot.atr <= 0:
        blockers.append("invalid_atr")
    if request.market_snapshot.spread_percent > request.planning_preferences.max_spread_percent:
        blockers.append("spread_too_wide")

    if not request.market_snapshot.volume_confirms:
        warnings.append("volume_not_confirmed")

    checkers["slippage_spread_calculator"] = CheckerResult(
        status="pass" if request.market_snapshot.spread_percent <= request.planning_preferences.max_spread_percent else "fail",
        message=f"Spread {request.market_snapshot.spread_percent:.2f}% (max {request.planning_preferences.max_spread_percent:.2f}%).",
    )

    # G) Master Admin / execution controls (effective runtime)
    readiness = _master_admin_readiness(request.account_state)

    # Set spread pass based on provided snapshot threshold
    readiness = readiness.model_copy(update={"spread_pass": request.market_snapshot.spread_percent <= request.planning_preferences.max_spread_percent})

    if readiness.emergency_stop:
        blockers.append("emergency_stop_active")
    if readiness.force_close_requested:
        blockers.append("force_close_requested")
    if not readiness.workflow_enabled:
        blockers.append("workflow_disabled_by_master_admin")
    if not readiness.execution_enabled:
        blockers.append("execution_disabled_by_master_admin")
    if not readiness.broker_execution_enabled:
        blockers.append("broker_execution_disabled_by_master_admin")
    if not readiness.paper_trading_enabled:
        blockers.append("paper_trading_disabled_by_master_admin")

    if readiness.live_trading_enabled and (not readiness.human_approval_required):
        blockers.append("live_trading_without_human_approval_blocked")

    checkers["master_admin_gate"] = CheckerResult(
        status="pass" if not any(b in blockers for b in ("emergency_stop_active", "execution_disabled_by_master_admin")) else "fail",
        message="Evaluated effective runtime master-admin gates (runtime_settings.json/env).",
    )

    # D) Stop/target
    stop_loss, target_price, risk_per_share, reward_per_share, rr = _compute_stop_target(
        request.market_snapshot,
        request.planning_preferences.target_reward_risk,
        request.planning_preferences.atr_stop_multiplier,
    )
    checkers["stop_target_calculator"] = CheckerResult(
        status="pass" if risk_per_share > 0 and rr > 0 else "fail",
        message=f"ATR-based stop/target computed (risk/share {risk_per_share:.2f}, RR {rr:.2f}).",
    )

    # E) Sizing
    qty, planned_notional, pos_pct, max_allowed_notional, sizing_status, sizing_warnings = _compute_sizing(
        request.account_state, request.market_snapshot, risk_per_share
    )
    warnings.extend(sizing_warnings)
    if qty <= 0:
        blockers.append("quantity_not_positive")

    checkers["position_sizing_calculator"] = CheckerResult(
        status="pass" if qty > 0 else "fail",
        message=f"Planned qty {qty} (status {sizing_status}).",
    )

    # F) Order type
    order_type, limit_price, order_warnings = _select_order_type(request.market_snapshot, request.planning_preferences.order_style)
    warnings.extend(order_warnings)
    checkers["order_type_selector"] = CheckerResult(
        status="pass",
        message=f"Selected order_type={order_type}.",
    )

    # Slippage pass: v1 placeholder — treat as pass when spread passes
    readiness = readiness.model_copy(update={"slippage_pass": readiness.spread_pass})

    plan_status = "blocked" if blockers else "planned"

    allowed_next_stages: list[str] = []
    if plan_status == "planned":
        # Never go directly to trade_execution. Stage 10 must still precheck/approval/submit.
        allowed_next_stages = ["execution_precheck"]

    next_action = (
        "Review plan blockers before sending to execution precheck."
        if blockers
        else "Send plan to Stage 10 execution precheck (paper-first)."
    )

    decision = PlanDecision(
        plan_status=plan_status,
        blockers=blockers,
        warnings=warnings,
        checkers=checkers,
        allowed_next_stages=allowed_next_stages,
        next_action=next_action,
    )

    computed = {
        "stop_loss": stop_loss,
        "target_price": target_price,
        "risk_per_share": risk_per_share,
        "reward_per_share": reward_per_share,
        "reward_risk_ratio": rr,
        "planned_quantity": qty,
        "planned_notional": planned_notional,
        "position_size_percent": pos_pct,
        "max_allowed_notional": max_allowed_notional,
        "sizing_status": sizing_status,
        "order_type": order_type,
        "limit_price": limit_price,
    }
    return decision, readiness, computed


def build_execution_plan(
    *,
    plan_id: str,
    created_at: str,
    request: ExecutionPlannerPlanRequest,
) -> ExecutionPlan:
    decision, readiness, computed = decide_plan_v1(request)

    max_dollar_risk = float(request.account_state.account_equity) * float(request.account_state.max_risk_per_trade_percent) / 100.0

    return ExecutionPlan(
        plan_id=plan_id,
        symbol=request.trigger_evaluation.symbol,
        asset_class=request.trigger_evaluation.asset_class,
        horizon=request.trigger_evaluation.horizon,
        plan_status=decision.plan_status,  # type: ignore[arg-type]
        entry={
            "order_type": computed["order_type"],
            "side": "buy",
            "limit_price": computed["limit_price"],
            "reference_price": float(request.market_snapshot.current_price),
        },
        risk={
            "stop_loss": computed["stop_loss"],
            "target_price": computed["target_price"],
            "risk_per_share": computed["risk_per_share"],
            "reward_per_share": computed["reward_per_share"],
            "reward_risk_ratio": float(request.planning_preferences.target_reward_risk),
            "max_dollar_risk": max_dollar_risk,
        },
        sizing={
            "planned_quantity": computed["planned_quantity"],
            "planned_notional": round(float(computed["planned_notional"]), 2),
            "position_size_percent": round(float(computed["position_size_percent"]), 2),
            "max_allowed_notional": round(float(computed["max_allowed_notional"]), 2),
            "sizing_status": computed["sizing_status"],
        },
        execution_readiness=readiness,
        blockers=decision.blockers,
        warnings=decision.warnings,
        checkers=decision.checkers,
        allowed_next_stages=decision.allowed_next_stages,
        next_action=decision.next_action,
        created_at=created_at,
    )

