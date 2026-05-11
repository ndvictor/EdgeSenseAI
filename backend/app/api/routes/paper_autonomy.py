"""Paper Autonomy Control Tower — read-only HTTP surface.

Hard guarantees:

- Every endpoint is a ``GET`` and never mutates broker state.
- ``broker_called`` is ``False`` in every record returned.
- ``live_submit_enabled`` is ``False`` in every status payload.
- No order-submit endpoint is registered here. Callers cannot create paper
  orders or positions through this surface; those records come exclusively
  from the audited ``execution_approval_agent`` / paper simulator path.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.settings import get_settings
from app.services.approval_queue.service import list_items as list_approval_items
from app.services.close_position.service import get_latest_review as get_close_review_latest
from app.services.learning_loop.service import get_latest_decision as get_learning_loop_latest
from app.services.paper_autonomy import (
    learning_outcomes_store,
    paper_order_store,
    paper_position_store,
)
from app.services.position_monitoring.service import (
    get_latest_evaluation as get_position_monitoring_latest,
)
from app.services.post_trade_evaluation.service import (
    get_latest_evaluation as get_post_trade_latest,
)


router = APIRouter(prefix="/daytrading/paper-autonomy", tags=["paper-autonomy"])


_AGENT_CHAIN_ORDER: tuple[str, ...] = (
    "watchlist_builder_agent",
    "alpha_engine_agent",
    "small_account_feasibility_agent",
    "execution_planner_agent",
    "execution_approval_agent",
    "position_monitor_agent",
    "close_review_agent",
    "post_trade_evaluator_agent",
    "learning_loop_agent",
)


def _capability_flags() -> dict[str, bool]:
    try:
        return dict(get_settings().agent_capability_flags)
    except Exception:
        return {}


def _safe_dump(record: Any) -> dict[str, Any]:
    if record is None:
        return {}
    data = record.model_dump() if hasattr(record, "model_dump") else dict(record)
    data["broker_called"] = False
    return data


def _approval_count() -> int:
    try:
        return len(list_approval_items(limit=50))
    except Exception:
        return 0


def _agent_chain_status(
    *,
    open_positions_count: int,
    closed_positions_count: int,
    orders_count: int,
    approval_count: int,
    pm_latest: Any,
    close_latest: Any,
    pt_latest: Any,
    ll_latest: Any,
) -> list[dict[str, Any]]:
    has_orders = orders_count > 0
    has_open = open_positions_count > 0
    has_closed = closed_positions_count > 0
    chain: list[dict[str, Any]] = []
    for agent in _AGENT_CHAIN_ORDER:
        entry: dict[str, Any] = {"agent": agent, "status": "idle"}
        if agent == "execution_approval_agent":
            entry["status"] = "active" if has_orders or approval_count else "idle"
        elif agent == "position_monitor_agent":
            entry["status"] = "active" if has_open or pm_latest is not None else "idle"
            entry["latest_id"] = getattr(pm_latest, "evaluation_id", None) if pm_latest else None
        elif agent == "close_review_agent":
            entry["status"] = "active" if close_latest is not None else "idle"
            entry["latest_id"] = getattr(close_latest, "review_id", None) if close_latest else None
        elif agent == "post_trade_evaluator_agent":
            entry["status"] = "active" if has_closed or pt_latest is not None else "idle"
            entry["latest_id"] = getattr(pt_latest, "evaluation_id", None) if pt_latest else None
        elif agent == "learning_loop_agent":
            entry["status"] = "active" if ll_latest is not None else "idle"
            entry["latest_id"] = getattr(ll_latest, "decision_id", None) if ll_latest else None
        else:
            entry["status"] = "ready"
        chain.append(entry)
    return chain


@router.get("/status")
def get_paper_autonomy_status() -> dict[str, Any]:
    flags = _capability_flags()
    settings_obj = get_settings()
    return {
        "status": "ok",
        "mode": "paper_autonomy",
        "broker_called": False,
        "live_submit_enabled": False,
        "paper_auto_enabled": bool(flags.get("agent_can_auto_submit_paper_orders", False)),
        "paper_trading_enabled": bool(getattr(settings_obj, "paper_trading_enabled", False)),
        "live_trading_enabled": bool(getattr(settings_obj, "live_trading_enabled", False)),
        "broker_execution_enabled": bool(getattr(settings_obj, "broker_execution_enabled", False)),
        "agent_capability_flags": flags,
    }


@router.get("/orders")
def get_paper_orders(workflow_run_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    items = paper_order_store.list_orders(workflow_run_id=workflow_run_id)
    items.sort(key=lambda o: o.created_at, reverse=True)
    if limit and limit > 0:
        items = items[: int(limit)]
    sanitized = [_safe_dump(o) for o in items]
    return {
        "status": "ok",
        "broker_called": False,
        "live_submit_enabled": False,
        "count": len(sanitized),
        "items": sanitized,
    }


@router.get("/positions/open")
def get_open_paper_positions(workflow_run_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    items = paper_position_store.list_open(workflow_run_id=workflow_run_id)
    items.sort(key=lambda p: p.opened_at, reverse=True)
    if limit and limit > 0:
        items = items[: int(limit)]
    sanitized = [_safe_dump(p) for p in items]
    return {
        "status": "ok",
        "broker_called": False,
        "live_submit_enabled": False,
        "count": len(sanitized),
        "items": sanitized,
    }


@router.get("/positions/closed")
def get_closed_paper_positions(workflow_run_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    items = paper_position_store.list_closed(workflow_run_id=workflow_run_id)
    items.sort(key=lambda p: (p.closed_at or "", p.opened_at), reverse=True)
    if limit and limit > 0:
        items = items[: int(limit)]
    sanitized = [_safe_dump(p) for p in items]
    return {
        "status": "ok",
        "broker_called": False,
        "live_submit_enabled": False,
        "count": len(sanitized),
        "items": sanitized,
    }


@router.get("/learning/outcomes")
def get_learning_outcomes(strategy_key: str | None = None, limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 50), 200))
    if strategy_key:
        outcomes = learning_outcomes_store.list_for_strategy(strategy_key, limit=safe_limit)
    else:
        outcomes = learning_outcomes_store.list_recent(limit=safe_limit)
    items = [o.model_dump() for o in outcomes]
    return {
        "status": "ok",
        "broker_called": False,
        "live_submit_enabled": False,
        "strategy_key": strategy_key,
        "count": len(items),
        "items": items,
    }


@router.get("/control-tower")
def get_control_tower(
    workflow_run_id: str | None = None,
    strategy_key: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    flags = _capability_flags()
    safe_limit = max(1, min(int(limit or 50), 200))

    orders = paper_order_store.list_orders(workflow_run_id=workflow_run_id)
    orders.sort(key=lambda o: o.created_at, reverse=True)
    open_positions = paper_position_store.list_open(workflow_run_id=workflow_run_id)
    open_positions.sort(key=lambda p: p.opened_at, reverse=True)
    closed_positions = paper_position_store.list_closed(workflow_run_id=workflow_run_id)
    closed_positions.sort(key=lambda p: (p.closed_at or "", p.opened_at), reverse=True)

    if strategy_key:
        outcomes = learning_outcomes_store.list_for_strategy(strategy_key, limit=safe_limit)
    else:
        outcomes = learning_outcomes_store.list_recent(limit=safe_limit)

    approval_count = _approval_count()

    pm_latest = get_position_monitoring_latest()
    close_latest = get_close_review_latest()
    pt_latest = get_post_trade_latest()
    ll_latest = get_learning_loop_latest()

    agent_chain = _agent_chain_status(
        open_positions_count=len(open_positions),
        closed_positions_count=len(closed_positions),
        orders_count=len(orders),
        approval_count=approval_count,
        pm_latest=pm_latest,
        close_latest=close_latest,
        pt_latest=pt_latest,
        ll_latest=ll_latest,
    )

    alerts: list[dict[str, Any]] = []
    if not flags.get("agent_can_auto_submit_paper_orders", False):
        alerts.append(
            {
                "severity": "info",
                "code": "paper_auto_disabled",
                "message": "AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS is disabled. Paper orders require approval before simulation.",
            }
        )
    if not orders and not open_positions and not closed_positions:
        alerts.append(
            {
                "severity": "info",
                "code": "loop_empty",
                "message": "No paper autonomy records yet. Run the autonomous workflow with paper_auto authority to populate this loop.",
            }
        )
    for pos in open_positions:
        if pos.last_mark_price is not None and pos.last_mark_price <= pos.stop_price:
            alerts.append(
                {
                    "severity": "warn",
                    "code": "paper_position_at_or_below_stop",
                    "message": f"Open paper position {pos.paper_position_id} ({pos.symbol}) is at or below its stop.",
                    "paper_position_id": pos.paper_position_id,
                    "symbol": pos.symbol,
                }
            )

    return {
        "status": "ok",
        "mode": "paper_autonomy",
        "broker_called": False,
        "live_submit_enabled": False,
        "paper_auto_enabled": bool(flags.get("agent_can_auto_submit_paper_orders", False)),
        "agent_capability_flags": flags,
        "summary": {
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "paper_orders": len(orders),
            "approval_items": approval_count,
            "learning_outcomes": len(outcomes),
        },
        "agent_chain": agent_chain,
        "orders": [_safe_dump(o) for o in orders],
        "open_positions": [_safe_dump(p) for p in open_positions],
        "closed_positions": [_safe_dump(p) for p in closed_positions],
        "learning_outcomes": [o.model_dump() for o in outcomes],
        "latest_reviews": {
            "position_monitoring": pm_latest.model_dump() if pm_latest else None,
            "close_review": close_latest.model_dump() if close_latest else None,
            "post_trade_evaluation": pt_latest.model_dump() if pt_latest else None,
            "learning_loop": ll_latest.model_dump() if ll_latest else None,
        },
        "alerts": alerts,
    }
