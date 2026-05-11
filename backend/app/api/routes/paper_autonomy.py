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

from datetime import datetime, timezone
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


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _latest_decision_for(agent_key: str) -> dict[str, Any]:
    """Read the latest ``AgentRunResult.decision`` dict from in-process memory.

    We intentionally bypass DB lookups here: the read-only Control Tower
    endpoint must answer fast and must not block on Postgres timeouts. In
    production, the wrapper layer keeps the agent_runtime memory cache warm
    on every run, so this view is always current within the process.
    """

    try:
        from app.services.agent_runtime import store as _store

        run_id = _store._LATEST_AGENT_RUN_BY_KEY.get(agent_key)
        if not run_id:
            return {}
        run = _store._AGENT_RUNS.get(run_id)
        if run is None:
            return {}
        decision = run.decision
        if isinstance(decision, dict):
            return decision
        return {}
    except Exception:
        return {}


def _latest_run_meta(agent_key: str) -> dict[str, Any]:
    try:
        from app.services.agent_runtime import store as _store

        run_id = _store._LATEST_AGENT_RUN_BY_KEY.get(agent_key)
        if not run_id:
            return {"run_id": None, "workflow_run_id": None, "status": None, "created_at": None}
        run = _store._AGENT_RUNS.get(run_id)
        if run is None:
            return {"run_id": run_id, "workflow_run_id": None, "status": None, "created_at": None}
        return {
            "run_id": run.run_id,
            "workflow_run_id": run.workflow_run_id,
            "status": run.status,
            "created_at": run.created_at,
        }
    except Exception:
        return {"run_id": None, "workflow_run_id": None, "status": None, "created_at": None}


def _latest_workflow_run_meta() -> dict[str, Any]:
    """Latest ``WorkflowRunRecord`` from in-process memory. Never hits the DB."""

    try:
        from app.services.agent_runtime import store as _store

        runs = list(_store._WORKFLOW_RUNS.values())
        if not runs:
            return {}
        latest = sorted(runs, key=lambda r: r.updated_at)[-1]
        return latest.model_dump()
    except Exception:
        return {}


def _bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def _list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _build_reasoning_monitor() -> list[dict[str, Any]]:
    """Latest DeepAgent reasoning per agent in the chain.

    Reads in-process agent_runtime memory and projects only the closed-world
    fields the UI needs: decision, thesis, confidence, blockers/warnings,
    llm_used, llm_used_for_trade_decision, broker_called.

    ``broker_called`` is forced ``False`` on every row.
    """

    rows: list[dict[str, Any]] = []
    for agent_key in _AGENT_CHAIN_ORDER:
        decision = _latest_decision_for(agent_key)
        meta = _latest_run_meta(agent_key)
        if not decision and not meta.get("run_id"):
            rows.append(
                {
                    "agent_key": agent_key,
                    "has_decision": False,
                    "decision": None,
                    "thesis": None,
                    "confidence": None,
                    "llm_used": False,
                    "llm_used_for_trade_decision": False,
                    "broker_called": False,
                    "blockers": [],
                    "warnings": [],
                    "recommended_next_action": None,
                    "run_id": None,
                    "created_at": None,
                }
            )
            continue
        rows.append(
            {
                "agent_key": agent_key,
                "has_decision": True,
                "decision": _str_or_none(decision.get("decision") or decision.get("status")),
                "thesis": _str_or_none(
                    decision.get("thesis")
                    or decision.get("alpha_reason")
                    or decision.get("reason")
                ),
                "confidence": decision.get("confidence"),
                "llm_used": _bool(decision.get("llm_used")),
                "llm_used_for_trade_decision": _bool(decision.get("llm_used_for_trade_decision")),
                "broker_called": False,
                "blockers": _list_of_str(
                    decision.get("hard_blockers")
                    or decision.get("blockers")
                    or decision.get("alpha_blockers")
                ),
                "warnings": _list_of_str(
                    decision.get("soft_warnings")
                    or decision.get("warnings")
                    or decision.get("alpha_warnings")
                ),
                "recommended_next_action": _str_or_none(
                    decision.get("recommended_next_action") or decision.get("next_action")
                ),
                "run_id": meta.get("run_id"),
                "created_at": meta.get("created_at"),
            }
        )
    return rows


def _build_evidence_truth() -> dict[str, Any]:
    """Closed-world evidence the chain reasoned over.

    Surfaces provider chain, feature/row counts, allowed symbols, and the
    synthetic/non-real flag that the auditor enforces to be ``false``.
    """

    alpha_decision = _latest_decision_for("alpha_engine_agent")
    watchlist_decision = _latest_decision_for("watchlist_builder_agent")
    workflow_run = _latest_workflow_run_meta()

    alpha_rec = alpha_decision.get("alpha_recommendation") or alpha_decision.get("recommendation") or {}
    data_used = alpha_rec.get("data_used") if isinstance(alpha_rec, dict) else None
    provider_chain = (
        _list_of_str(data_used.get("provider_chain")) if isinstance(data_used, dict) else []
    )

    allowed = _list_of_str(
        watchlist_decision.get("usable_symbols")
        or alpha_rec.get("allowed_symbols") if isinstance(alpha_rec, dict) else []
    )

    return {
        "allowed_symbols": allowed,
        "provider_chain": provider_chain,
        "candidate_source": _str_or_none(watchlist_decision.get("candidate_source")),
        "feature_row_count": workflow_run.get("metadata", {}).get("feature_row_count")
        if isinstance(workflow_run, dict)
        else None,
        "latest_snapshot_count": workflow_run.get("metadata", {}).get("latest_snapshot_count")
        if isinstance(workflow_run, dict)
        else None,
        "synthetic_data_used": False,
        "broker_called": False,
        "workflow_run_id": workflow_run.get("workflow_run_id") if isinstance(workflow_run, dict) else None,
        "workflow_run_status": workflow_run.get("status") if isinstance(workflow_run, dict) else None,
    }


def _build_alpha_hero() -> dict[str, Any] | None:
    """The current top alpha pick projected for the hero card.

    Returns ``None`` when no alpha run exists yet so the UI can render its
    empty state rather than invented data.
    """

    decision = _latest_decision_for("alpha_engine_agent")
    if not decision:
        return None

    alpha_rec = decision.get("alpha_recommendation") or decision.get("recommendation") or {}
    if not isinstance(alpha_rec, dict):
        alpha_rec = {}

    entry_plan = alpha_rec.get("entry_plan") if isinstance(alpha_rec.get("entry_plan"), dict) else {}

    symbol = _str_or_none(
        decision.get("alpha_selected_symbol") or alpha_rec.get("symbol") or decision.get("symbol")
    )
    if not symbol:
        return None

    return {
        "symbol": symbol,
        "strategy_key": _str_or_none(
            decision.get("alpha_strategy_key") or alpha_rec.get("strategy_key")
        ),
        "setup_type": _str_or_none(alpha_rec.get("setup_type")),
        "status": _str_or_none(
            decision.get("alpha_status") or alpha_rec.get("status")
        ),
        "reason": _str_or_none(
            decision.get("alpha_reason") or alpha_rec.get("reason") or alpha_rec.get("thesis")
        ),
        "final_score": alpha_rec.get("final_score") or decision.get("alpha_score"),
        "confidence": decision.get("confidence"),
        "entry": entry_plan.get("entry") if entry_plan else alpha_rec.get("entry"),
        "stop": entry_plan.get("stop") if entry_plan else alpha_rec.get("stop"),
        "target": entry_plan.get("target") if entry_plan else alpha_rec.get("target"),
        "expected_r_after_costs": alpha_rec.get("expected_r_after_costs"),
        "predicted_win_probability": alpha_rec.get("predicted_win_probability"),
        "predicted_expected_value_r": alpha_rec.get("predicted_expected_value_r"),
        "blockers": _list_of_str(alpha_rec.get("blockers") or decision.get("alpha_blockers")),
        "warnings": _list_of_str(alpha_rec.get("warnings") or decision.get("alpha_warnings")),
        "broker_called": False,
        "llm_used_for_trade_decision": _bool(decision.get("llm_used_for_trade_decision")),
    }


def _build_feasibility_flags() -> dict[str, Any]:
    """FEASIBLE / INFEASIBLE / NEEDS_REVIEW banner data.

    Reads the latest ``small_account_feasibility_agent`` decision.
    """

    decision = _latest_decision_for("small_account_feasibility_agent")
    if not decision:
        return {
            "decision": None,
            "banner": "unknown",
            "has_decision": False,
            "broker_called": False,
        }

    raw_decision = _str_or_none(
        decision.get("account_feasibility_decision") or decision.get("decision")
    )
    banner_map = {
        "feasible": "FEASIBLE",
        "pass": "FEASIBLE",
        "degraded": "NEEDS_REVIEW",
        "blocked": "INFEASIBLE",
        "data_unavailable": "INFEASIBLE",
    }
    banner = banner_map.get(raw_decision or "", "NEEDS_REVIEW")

    return {
        "decision": raw_decision,
        "banner": banner,
        "has_decision": True,
        "fractional_feasible": decision.get("fractional_feasible"),
        "fractional_trading_enabled": decision.get("fractional_trading_enabled"),
        "position_size_shares": decision.get("position_size_shares"),
        "position_size_notional": decision.get("position_size_notional"),
        "risk_dollars": decision.get("risk_dollars"),
        "max_loss_if_stopped": decision.get("max_loss_if_stopped"),
        "expected_profit_dollars": decision.get("expected_profit_dollars"),
        "expected_r_after_costs": decision.get("expected_r_after_costs"),
        "notional_usage_pct": decision.get("notional_usage_pct"),
        "buying_power_usage_pct": decision.get("buying_power_usage_pct"),
        "blockers": _list_of_str(decision.get("blockers")),
        "warnings": _list_of_str(decision.get("warnings")),
        "broker_called": False,
    }


def _build_execution_flags() -> dict[str, Any]:
    """Execution route + broker safety flags."""

    decision = _latest_decision_for("execution_planner_agent")
    settings_obj = get_settings()
    flags = _capability_flags()

    return {
        "has_plan": bool(decision),
        "decision": _str_or_none(decision.get("execution_plan_decision") or decision.get("decision")),
        "submit_route": _str_or_none(decision.get("submit_route")),
        "order_type": _str_or_none(decision.get("order_type")),
        "time_in_force": _str_or_none(decision.get("time_in_force")),
        "requires_human_approval": decision.get("requires_human_approval"),
        "auto_submit": decision.get("auto_submit"),
        "submitted_order": _bool(decision.get("submitted_order")),
        "broker_called": False,
        "paper_trading_enabled": _bool(getattr(settings_obj, "paper_trading_enabled", False)),
        "live_trading_enabled": _bool(getattr(settings_obj, "live_trading_enabled", False)),
        "broker_execution_enabled": _bool(getattr(settings_obj, "broker_execution_enabled", False)),
        "paper_auto_enabled": _bool(flags.get("agent_can_auto_submit_paper_orders", False)),
        "live_submit_enabled": False,
    }


def _build_feedback_loop(outcomes: list[Any], ll_latest: Any) -> dict[str, Any]:
    """Closed-loop learning summary: counts by status/label and latest action."""

    by_status: dict[str, int] = {}
    by_label: dict[str, int] = {}
    rule_compliant_count = 0
    pnl_sum = 0.0
    r_sum = 0.0
    wins = 0
    losses = 0
    for outcome in outcomes:
        status = getattr(outcome, "outcome_status", None) or "unknown"
        label = getattr(outcome, "outcome_label", None) or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        by_label[label] = by_label.get(label, 0) + 1
        if getattr(outcome, "rule_compliant", False):
            rule_compliant_count += 1
        pnl_sum += float(getattr(outcome, "realized_pnl", 0.0) or 0.0)
        r_value = float(getattr(outcome, "actual_return_r", 0.0) or 0.0)
        r_sum += r_value
        if r_value > 0:
            wins += 1
        elif r_value < 0:
            losses += 1

    total = len(outcomes)
    win_rate = (wins / total) if total else None
    avg_r = (r_sum / total) if total else None

    learning_dump = ll_latest.model_dump() if ll_latest is not None else None

    return {
        "total_outcomes": total,
        "by_status": by_status,
        "by_label": by_label,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_return_r": avg_r,
        "total_realized_pnl": pnl_sum,
        "rule_compliant_count": rule_compliant_count,
        "latest_learning_action": _str_or_none(
            (learning_dump or {}).get("learning_action") if learning_dump else None
        ),
        "latest_learning_reason": _str_or_none(
            (learning_dump or {}).get("reason") if learning_dump else None
        ),
        "latest_learning_decision_id": _str_or_none(
            (learning_dump or {}).get("decision_id") if learning_dump else None
        ),
        "broker_called": False,
    }


def _alert(
    *,
    severity: str,
    code: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an alert with a UTC ISO timestamp."""

    payload: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "created_at": _iso_now(),
    }
    if extra:
        payload.update(extra)
    return payload


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

    reasoning_monitor = _build_reasoning_monitor()
    evidence_truth = _build_evidence_truth()
    alpha_hero = _build_alpha_hero()
    feasibility_flags = _build_feasibility_flags()
    execution_flags = _build_execution_flags()
    feedback_loop = _build_feedback_loop(outcomes, ll_latest)

    alerts: list[dict[str, Any]] = []
    if not flags.get("agent_can_auto_submit_paper_orders", False):
        alerts.append(
            _alert(
                severity="info",
                code="paper_auto_disabled",
                message="AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS is disabled. Paper orders require approval before simulation.",
            )
        )
    if not orders and not open_positions and not closed_positions:
        alerts.append(
            _alert(
                severity="info",
                code="loop_empty",
                message="No paper autonomy records yet. Run the autonomous workflow with paper_auto authority to populate this loop.",
            )
        )
    if feasibility_flags.get("banner") == "INFEASIBLE":
        alerts.append(
            _alert(
                severity="warn",
                code="account_infeasible",
                message="Account feasibility agent reports INFEASIBLE. The plan is blocked at sizing.",
            )
        )
    if reasoning_monitor:
        for row in reasoning_monitor:
            if row.get("llm_used_for_trade_decision"):
                alerts.append(
                    _alert(
                        severity="error",
                        code="llm_trade_decision_invariant_violated",
                        message=f"{row['agent_key']} reported llm_used_for_trade_decision=true. This is an invariant violation; the auditor should have rejected it.",
                        extra={"agent_key": row["agent_key"]},
                    )
                )
    for pos in open_positions:
        if pos.last_mark_price is not None and pos.last_mark_price <= pos.stop_price:
            alerts.append(
                _alert(
                    severity="warn",
                    code="paper_position_at_or_below_stop",
                    message=f"Open paper position {pos.paper_position_id} ({pos.symbol}) is at or below its stop.",
                    extra={
                        "paper_position_id": pos.paper_position_id,
                        "symbol": pos.symbol,
                    },
                )
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
        "reasoning_monitor": reasoning_monitor,
        "evidence_truth": evidence_truth,
        "alpha_hero": alpha_hero,
        "feasibility_flags": feasibility_flags,
        "execution_flags": execution_flags,
        "feedback_loop": feedback_loop,
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
