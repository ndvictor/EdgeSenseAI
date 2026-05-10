"""Paper simulator service.

Consumes the audited ``execution_plan`` from ``execution_planner_agent`` and the
resolved ``OwnerAuthority`` to either:

- create a simulated paper order + paper position record (paper auto-submit),
- create an approval queue item only (approval required),
- block (live submit is disabled in this step), or
- emit a no-op record (plan_only).

This service never calls a broker. It never calls Alpaca order submit. It never
flips ``broker_called`` to ``True``. ``submitted_order=True`` is only set when
the paper auto-submit gates all pass.
"""

from __future__ import annotations

from typing import Any

from app.services.approval_queue.models import ApprovalItemCreate
from app.services.approval_queue.service import create_item as create_approval_item
from app.services.paper_autonomy import paper_order_store, paper_position_store
from app.services.paper_autonomy.models import (
    PaperOrderRecord,
    PaperPositionRecord,
    iso_utc_now,
)


_AUTH_LEVELS = {
    "read_only": 0,
    "advise": 1,
    "paper_plan": 2,
    "paper_submit": 3,
    "paper_auto": 4,
    "live_submit": 5,
}


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


def _auth_level(authority: dict[str, Any]) -> int:
    return _AUTH_LEVELS.get(str(authority.get("level") or "read_only"), 0)


def _resolve_plan(inputs: dict[str, Any]) -> dict[str, Any]:
    plan = inputs.get("execution_plan")
    if isinstance(plan, dict):
        return dict(plan)
    return {}


def simulate_paper_order_from_plan(
    inputs: dict[str, Any],
    *,
    workflow_run_id: str,
    orchestrator_run_id: str | None = None,
    agent_run_id: str | None = None,
) -> dict[str, Any]:
    """Run the simulator. Returns a structured dict with status + records.

    The dict always has:
    - status: one of plan_only, paper_simulated, approval_required,
      paper_blocked, live_blocked.
    - submitted_order: bool (only True for paper_simulated)
    - broker_called: False (always)
    - live_submit: False (always)
    - paper_order, paper_position: dicts when created, else None
    - approval_item: dict when created, else None
    - blockers / warnings lists
    """

    plan = _resolve_plan(inputs)
    authority: dict[str, Any] = inputs.get("owner_authority") if isinstance(inputs.get("owner_authority"), dict) else {}
    authority = dict(authority)

    submit_route = str(plan.get("submit_route") or inputs.get("submit_route") or "none").lower()
    if submit_route not in {"none", "paper", "live"}:
        submit_route = "none"

    flags = inputs.get("agent_capability_flags") if isinstance(inputs.get("agent_capability_flags"), dict) else {}

    paper_trading_enabled = _bool(inputs.get("paper_trading_enabled"), False)
    live_trading_enabled = _bool(inputs.get("live_trading_enabled"), False)
    broker_execution_enabled = _bool(inputs.get("broker_execution_enabled"), False)
    agent_can_paper_auto = _bool(flags.get("agent_can_auto_submit_paper_orders"), False) or _bool(
        inputs.get("agent_can_auto_submit_paper_orders"), False
    )
    agent_can_submit_live = _bool(flags.get("agent_can_submit_live_orders"), False) or _bool(
        inputs.get("agent_can_submit_live_orders"), False
    )

    can_paper_auto = bool(authority.get("can_paper_auto_submit"))
    can_live = bool(authority.get("can_submit_live_orders"))
    auth_level = _auth_level(authority)
    require_human_approval = _bool(authority.get("require_human_approval"), True)
    human_approval_confirmed = _bool(inputs.get("human_approval_confirmed"), False)

    blockers: list[str] = []
    warnings: list[str] = []

    base_response: dict[str, Any] = {
        "status": "plan_only",
        "submit_route": submit_route,
        "submitted_order": False,
        "broker_called": False,
        "live_submit": False,
        "paper_order": None,
        "paper_position": None,
        "approval_item": None,
        "owner_authority": dict(authority),
        "blockers": blockers,
        "warnings": warnings,
    }

    if submit_route == "live":
        blockers.append("live_submit_disabled_for_step_6")
        if not can_live:
            blockers.append("owner_authority_lacks_live_submit")
        if not (live_trading_enabled and broker_execution_enabled):
            blockers.append("live_flags_disabled")
        base_response["status"] = "live_blocked"
        return base_response

    if submit_route == "none":
        if require_human_approval and auth_level >= _AUTH_LEVELS["paper_plan"]:
            approval_item = _create_approval_item(
                inputs=inputs,
                plan=plan,
                workflow_run_id=workflow_run_id,
                orchestrator_run_id=orchestrator_run_id,
                agent_run_id=agent_run_id,
                approval_type="execution_plan_review",
                note="Plan-only review; no order submitted.",
            )
            base_response.update(
                {
                    "status": "approval_required",
                    "approval_item": approval_item,
                }
            )
            return base_response
        return base_response

    if not paper_trading_enabled:
        blockers.append("paper_trading_disabled")
    if not agent_can_paper_auto:
        blockers.append("agent_can_auto_submit_paper_orders_disabled")
    if not can_paper_auto:
        blockers.append("owner_authority_lacks_paper_auto")
    if auth_level < _AUTH_LEVELS["paper_auto"]:
        blockers.append("owner_authority_level_below_paper_auto")

    symbol = str(plan.get("symbol") or "").strip().upper()
    entry = _float_or_none(plan.get("entry") or plan.get("limit_price"))
    stop = _float_or_none(plan.get("stop_price") or plan.get("stop"))
    target = _float_or_none(plan.get("take_profit") or plan.get("target"))
    shares = _float_or_none(plan.get("position_size_shares"))
    notional = _float_or_none(plan.get("position_size_notional"))
    risk_dollars = _float_or_none(plan.get("risk_dollars"))
    expected_profit = _float_or_none(plan.get("expected_profit_dollars"))
    expected_r_after_costs = _float_or_none(plan.get("expected_r_after_costs"))

    if not symbol:
        blockers.append("missing_symbol")
    if entry is None or entry <= 0:
        blockers.append("missing_entry")
    if stop is None or stop <= 0:
        blockers.append("missing_stop")
    if target is None or target <= 0:
        blockers.append("missing_target")
    if shares is None or shares <= 0:
        blockers.append("missing_shares")
    if notional is None or notional <= 0:
        blockers.append("missing_notional")
    if risk_dollars is None or risk_dollars <= 0:
        blockers.append("missing_risk_dollars")

    if blockers:
        base_response.update({"status": "paper_blocked"})
        return base_response

    assert symbol and entry is not None and stop is not None and target is not None
    assert shares is not None and notional is not None and risk_dollars is not None

    order = PaperOrderRecord(
        workflow_run_id=workflow_run_id,
        orchestrator_run_id=orchestrator_run_id,
        agent_run_id=agent_run_id,
        recommendation_id=str(inputs.get("recommendation_id")) if inputs.get("recommendation_id") else None,
        symbol=symbol,
        strategy_key=str(inputs.get("strategy_key") or inputs.get("alpha_strategy_key") or "") or None,
        side="buy",
        order_type=str(plan.get("order_type") or "limit").lower() if str(plan.get("order_type") or "limit").lower() in {"limit", "market"} else "limit",
        time_in_force=str(plan.get("time_in_force") or "day").lower() if str(plan.get("time_in_force") or "day").lower() in {"day", "gtc"} else "day",
        entry=entry,
        stop=stop,
        target=target,
        shares=shares,
        notional=notional,
        risk_dollars=risk_dollars,
        expected_profit_dollars=expected_profit,
        expected_r_after_costs=expected_r_after_costs,
        submit_route="paper",
        status="paper_open",
        submitted_order=True,
    )
    paper_order_store.create(order)

    position = PaperPositionRecord(
        paper_order_id=order.paper_order_id,
        workflow_run_id=workflow_run_id,
        orchestrator_run_id=orchestrator_run_id,
        recommendation_id=order.recommendation_id,
        symbol=symbol,
        strategy_key=order.strategy_key,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        shares=shares,
        notional=notional,
        risk_dollars=risk_dollars,
        expected_profit_dollars=expected_profit,
        expected_r_after_costs=expected_r_after_costs,
        opened_at=iso_utc_now(),
        status="open",
    )
    paper_position_store.create(position)

    base_response.update(
        {
            "status": "paper_simulated",
            "submitted_order": True,
            "broker_called": False,
            "live_submit": False,
            "paper_order": order.model_dump(),
            "paper_position": position.model_dump(),
        }
    )
    return base_response


def _create_approval_item(
    *,
    inputs: dict[str, Any],
    plan: dict[str, Any],
    workflow_run_id: str,
    orchestrator_run_id: str | None,
    agent_run_id: str | None,
    approval_type: str,
    note: str,
) -> dict[str, Any]:
    body = ApprovalItemCreate(
        workflow_run_id=workflow_run_id,
        orchestrator_run_id=orchestrator_run_id,
        agent_run_id=agent_run_id,
        approval_type=approval_type,
        status="pending",
        requested_action={
            "action": "review_execution_plan",
            "submit_route": str(plan.get("submit_route") or inputs.get("submit_route") or "none"),
            "symbol": plan.get("symbol"),
            "entry": plan.get("entry") or plan.get("limit_price"),
            "stop_price": plan.get("stop_price"),
            "take_profit": plan.get("take_profit"),
            "shares": plan.get("position_size_shares"),
            "note": note,
        },
        risk_summary={
            "risk_dollars": plan.get("risk_dollars"),
            "notional": plan.get("position_size_notional"),
            "expected_r_after_costs": plan.get("expected_r_after_costs"),
            "broker_called": False,
            "submitted_order": False,
        },
        required_approver="owner",
    )
    out = create_approval_item(body)
    return out.model_dump()
