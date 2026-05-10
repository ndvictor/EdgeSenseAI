from __future__ import annotations

from typing import Any


_AUTH_LEVELS = {"read_only": 0, "advise": 1, "paper_plan": 2, "paper_submit": 3, "paper_auto": 4, "live_submit": 5}


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _owner_authority(inputs: dict[str, Any]) -> dict[str, Any]:
    explicit = inputs.get("owner_authority")
    if isinstance(explicit, dict):
        return dict(explicit)

    flags = inputs.get("agent_capability_flags") if isinstance(inputs.get("agent_capability_flags"), dict) else {}
    can_live = bool(flags.get("agent_can_submit_live_orders"))
    can_paper_auto = bool(flags.get("agent_can_auto_submit_paper_orders"))
    can_paper_submit = bool(flags.get("agent_can_submit_paper_orders"))
    can_paper_plan = bool(flags.get("agent_can_create_paper_plans"))
    can_approval = bool(flags.get("agent_can_create_approval_requests"))
    can_recommend = bool(flags.get("agent_can_recommend_trades"))

    if can_live:
        level = "live_submit"
    elif can_paper_auto:
        level = "paper_auto"
    elif can_paper_submit:
        level = "paper_submit"
    elif can_paper_plan or can_approval:
        level = "paper_plan"
    elif can_recommend:
        level = "advise"
    else:
        level = "read_only"
    return {
        "level": level,
        "can_recommend_trades": can_recommend,
        "can_create_paper_plans": can_paper_plan,
        "can_create_approval_requests": can_approval,
        "can_submit_paper_orders": can_paper_submit,
        "can_paper_auto_submit": can_paper_auto,
        "can_submit_live_orders": can_live,
        "require_human_approval": True,
    }


def _auth_level(authority: dict[str, Any]) -> int:
    return _AUTH_LEVELS.get(str(authority.get("level") or "read_only"), 0)


def _alpha_entry_plan(inputs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    alpha = inputs.get("alpha_recommendation") if isinstance(inputs.get("alpha_recommendation"), dict) else {}
    entry_plan = alpha.get("entry_plan") if isinstance(alpha.get("entry_plan"), dict) else {}
    return alpha, entry_plan


def evaluate_execution_planner_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic execution plan from audited Alpha + feasibility output.

    This adapter does not call a broker. ``submit_route`` is ``none`` unless the
    resolved owner authority permits paper auto-submit or live submit *and* the
    corresponding global flags are also enabled.
    """
    m = dict(inputs or {})
    alpha, entry_plan = _alpha_entry_plan(m)
    authority = _owner_authority(m)

    symbol = str(
        m.get("alpha_selected_symbol")
        or alpha.get("symbol")
        or m.get("selected_symbol")
        or m.get("symbol")
        or ""
    ).strip().upper()

    entry = _float_or_none(m.get("entry"))
    stop = _float_or_none(m.get("stop"))
    target = _float_or_none(m.get("target"))
    if entry is None:
        entry = _float_or_none(entry_plan.get("entry"))
    if stop is None:
        stop = _float_or_none(entry_plan.get("stop"))
    if target is None:
        target = _float_or_none(entry_plan.get("target"))

    shares = _float_or_none(m.get("position_size_shares"))
    notional = _float_or_none(m.get("position_size_notional"))
    risk_dollars = _float_or_none(m.get("risk_dollars"))
    expected_profit = _float_or_none(m.get("expected_profit_dollars"))
    expected_r_after_costs = _float_or_none(m.get("expected_r_after_costs"))

    blockers: list[str] = []
    warnings: list[str] = []
    if not symbol:
        blockers.append("missing_alpha_symbol")
    if not isinstance(alpha, dict) or not alpha:
        blockers.append("missing_alpha_recommendation")
    if str(m.get("account_feasibility_decision") or "").lower() not in {"feasible", "degraded"}:
        blockers.append("account_feasibility_not_passed")
    if entry is None or entry <= 0:
        blockers.append("missing_entry")
    if stop is None or stop <= 0:
        blockers.append("missing_stop")
    if target is None or target <= 0:
        blockers.append("missing_target")
    if shares is None or shares <= 0:
        blockers.append("missing_position_size_shares")
    if notional is None or notional <= 0:
        blockers.append("missing_position_size_notional")
    if risk_dollars is None or risk_dollars <= 0:
        blockers.append("missing_risk_dollars")

    order_type = str(m.get("order_type") or "limit").lower()
    if order_type not in {"limit", "market"}:
        warnings.append("order_type_defaulted_to_limit")
        order_type = "limit"

    time_in_force = str(m.get("time_in_force") or "day").lower()
    if time_in_force not in {"day", "gtc"}:
        warnings.append("time_in_force_defaulted_to_day")
        time_in_force = "day"

    live_flags_enabled = (
        _bool(m.get("live_trading_enabled"), False)
        and _bool(m.get("broker_execution_enabled"), False)
        and _bool(m.get("live_execution_enabled"), _bool(m.get("live_trading_enabled"), False))
    )
    paper_enabled = _bool(m.get("paper_trading_enabled"), True)
    approval_passed = not _bool(authority.get("require_human_approval"), True) or _bool(m.get("human_approval_confirmed"), False)

    requested_route = str(m.get("requested_submit_route") or m.get("submit_route") or "none").lower()
    submit_route = "none"
    submitted_order = False
    requires_human_approval = bool(authority.get("require_human_approval", True))

    if not blockers and requested_route == "paper":
        if paper_enabled and bool(authority.get("can_paper_auto_submit")) and _auth_level(authority) >= _AUTH_LEVELS["paper_auto"]:
            submit_route = "paper"
            submitted_order = True
            requires_human_approval = False
        else:
            warnings.append("paper_submit_route_not_authorized")
    elif not blockers and requested_route == "live":
        if bool(authority.get("can_submit_live_orders")) and live_flags_enabled and approval_passed:
            submit_route = "live"
            submitted_order = False
            requires_human_approval = bool(authority.get("require_human_approval", True))
        else:
            warnings.append("live_submit_route_not_authorized")

    if blockers:
        decision = "no_plan"
    elif submit_route == "live":
        decision = "live_plan"
    elif submit_route == "paper":
        decision = "paper_plan"
    elif requires_human_approval and _auth_level(authority) >= _AUTH_LEVELS["paper_plan"]:
        decision = "approval_required"
    else:
        decision = "paper_plan"

    execution_plan = {
        "symbol": symbol or None,
        "side": "buy",
        "order_type": order_type,
        "time_in_force": time_in_force,
        "entry": entry,
        "limit_price": entry if order_type == "limit" else None,
        "stop_price": stop,
        "take_profit": target,
        "position_size_shares": shares,
        "position_size_notional": notional,
        "risk_dollars": risk_dollars,
        "expected_profit_dollars": expected_profit,
        "expected_r_after_costs": expected_r_after_costs,
        "submit_route": submit_route,
        "requires_human_approval": requires_human_approval,
        "submitted_order": submitted_order,
        "broker_called": False,
        "bracket_legs": {
            "stop_loss": {"price": stop},
            "take_profit": {"price": target},
        },
    }
    return {
        "status": "blocked" if blockers else "ok",
        "execution_plan_decision": decision,
        "execution_plan": execution_plan,
        "symbol": symbol or None,
        "order_type": order_type,
        "time_in_force": time_in_force,
        "limit_price": execution_plan["limit_price"],
        "stop_price": stop,
        "take_profit": target,
        "position_size_shares": shares,
        "position_size_notional": notional,
        "risk_dollars": risk_dollars,
        "expected_profit_dollars": expected_profit,
        "expected_r_after_costs": expected_r_after_costs,
        "submit_route": submit_route,
        "requires_human_approval": requires_human_approval,
        "owner_authority": authority,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_agent": "execution_approval_agent" if not blockers and submit_route == "none" else None,
        "allow_submit": submit_route != "none",
        "submitted_order": submitted_order,
        "broker_called": False,
        "llm_used": False,
        "llm_used_for_trade_decision": False,
    }
