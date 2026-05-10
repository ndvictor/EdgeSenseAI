from __future__ import annotations

from typing import Any

from app.services.agent_runtime.wrappers.safety import SafetyResult, enforce_phase2_safety
from app.services.agent_runtime.wrappers.glue_agents import GLUE_AGENT_KEYS, run_glue_agent


WRAPPED_AGENT_KEYS = frozenset(
    {
        "account_owner_policy_agent",
        "workflow_orchestrator_agent",
        # Phase 3 glue agents
        "data_readiness_agent",
        "market_condition_agent",
        "watchlist_builder_agent",
        "alpha_engine_agent",
        "strategy_selection_agent",
        "model_selection_agent",
        "backtest_validation_agent",
        "qlib_research_agent",
        "small_account_feasibility_agent",
        # Phase 2 stage wrappers
        "session_router_agent",
        "workflow_router_agent",
        "strategy_eligibility_agent",
        "trigger_monitor_agent",
        "execution_planner_agent",
        "execution_approval_agent",
        "narrative_review_agent",
        "position_monitor_agent",
        "close_review_agent",
        "post_trade_evaluator_agent",
        "learning_loop_agent",
    }
)


def _is_orchestrator_context(context: dict[str, Any]) -> bool:
    return context.get("source") == "workflow_orchestrator"


def _first_symbol(inputs: dict[str, Any], *, fallback: str = "") -> str:
    if inputs.get("symbol"):
        return str(inputs["symbol"]).strip().upper()
    if inputs.get("selected_symbol"):
        return str(inputs["selected_symbol"]).strip().upper()
    if isinstance(inputs.get("symbols"), list) and inputs["symbols"]:
        return str(inputs["symbols"][0]).strip().upper()
    return fallback


def _orchestrator_account_equity(inputs: dict[str, Any]) -> float:
    try:
        return float(inputs.get("account_equity") or 1000.0)
    except (TypeError, ValueError):
        return 1000.0


def _proof_status_for_eligibility(value: Any, *, orchestrator_context: bool) -> str:
    raw = str(value or ("unknown" if orchestrator_context else "proven"))
    if raw == "proof_required":
        return "backtest_required"
    allowed = {"proven", "paper_passed", "backtest_required", "research_only", "unknown", "blocked"}
    return raw if raw in allowed else "unknown"


def _wrap_result(
    *,
    agent_key: str,
    tool_name: str,
    tool_request: dict[str, Any],
    tool_response: dict[str, Any],
    safety: SafetyResult,
    next_agent: str | None,
) -> tuple[dict[str, Any], list[str], list[str], str, str | None, dict[str, Any]]:
    # Decide output fields consistently across wrappers
    blockers: list[str] = []
    warnings: list[str] = []
    next_action = "Review tool output."

    # Try to infer blockers/warnings/next_action from tool response
    payload = None
    for k in (
        "session",
        "decision",
        "eligibility",
        "trigger_evaluation",
        "execution_plan",
        "position_evaluation",
        "close_review",
        "post_trade_evaluation",
        "learning_decision",
    ):
        if isinstance(tool_response, dict) and k in tool_response:
            payload = tool_response.get(k)
            break
    if isinstance(payload, dict):
        blockers = list(payload.get("blockers") or [])
        warnings = list(payload.get("warnings") or [])
        if payload.get("next_action"):
            next_action = str(payload.get("next_action"))
    if isinstance(tool_response, dict):
        blockers.extend(str(x) for x in (tool_response.get("blockers") or []) if x)
        warnings.extend(str(x) for x in (tool_response.get("warnings") or []) if x)
        if tool_response.get("next_action"):
            next_action = str(tool_response.get("next_action"))

    # Merge safety warnings/blockers
    blockers = sorted(set(blockers + safety.blockers))
    warnings = sorted(set(warnings + safety.warnings))

    artifacts = {
        "tool_name": tool_name,
        "tool_request": tool_request,
        "tool_response": tool_response,
        "llm_used": False,
        "broker_called": False,
        "submitted_order": False,
    }
    return tool_response, blockers, warnings, next_action, next_agent, artifacts


def run_wrapped_agent(*, agent_key: str, inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the appropriate deterministic stage service.

    Returns a dict with keys:
    - tool_name, tool_request, tool_response, next_agent
    """
    safety = enforce_phase2_safety(agent_key=agent_key, inputs=inputs, context=context)
    if safety.blockers:
        return {
            "tool_name": "safety_boundary",
            "tool_request": inputs,
            "tool_response": {"status": "blocked", "blockers": safety.blockers, "warnings": safety.warnings},
            "next_agent": None,
            "safety": safety,
        }

    s = safety.sanitized_inputs
    orchestrator_context = _is_orchestrator_context(context)

    if agent_key in GLUE_AGENT_KEYS:
        return run_glue_agent(agent_key=agent_key, inputs=inputs, context=context, safety=safety)

    if agent_key == "workflow_orchestrator_agent":
        # Registered for discovery/tests; multi-step execution is the HTTP orchestrator entrypoint.
        return {
            "tool_name": "workflow_orchestrator.documentation",
            "tool_request": {"entrypoint": "POST /api/workflow-orchestrator/run"},
            "tool_response": {
                "status": "ok",
                "decision": {
                    "blockers": [],
                    "warnings": [],
                    "next_action": "Run the staged plan via POST /api/workflow-orchestrator/run (or Workflow Runbook). Single agent-runs do not recurse into the full plan.",
                },
            },
            "next_agent": None,
            "safety": safety,
        }

    if agent_key == "account_owner_policy_agent":
        from app.services.account_owner_policy.models import AccountOwnerPolicyRequest
        from app.services.account_owner_policy.service import evaluate_owner_policy

        req = AccountOwnerPolicyRequest.model_validate(
            {
                "workflow_run_id": context.get("workflow_run_id"),
                "mode": s.get("mode"),
                "actor": s.get("actor"),
            }
        )
        resp = evaluate_owner_policy(req)
        return {
            "tool_name": "account_owner_policy.evaluate_owner_policy",
            "tool_request": req.model_dump(),
            "tool_response": resp.model_dump(),
            "next_agent": "data_readiness_agent" if resp.decision == "allow" else None,
            "safety": safety,
        }

    if agent_key == "session_router_agent":
        from app.services.session_router.models import SessionEvaluateRequest
        from app.services.session_router.service import evaluate_session

        req = SessionEvaluateRequest.model_validate(
            {
                "market": s.get("market", "us_equities"),
                "timestamp": s.get("timestamp", "2026-05-07T09:35:00-05:00"),
                "timezone": s.get("timezone", "America/Chicago"),
                "use_current_time": bool(s.get("use_current_time", False)),
            }
        )
        resp = evaluate_session(req)
        return {
            "tool_name": "session_router.evaluate_session",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": "workflow_router_agent",
            "safety": safety,
        }

    if agent_key == "workflow_router_agent":
        from app.services.workflow_router.models import WorkflowRouteRequest
        from app.services.workflow_router.service import route_next_workflow

        proof_status = _proof_status_for_eligibility(s.get("proof_status"), orchestrator_context=orchestrator_context)
        default_req = {
            "session": "market_open",
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "pass",
                "urgency": "high",
            },
            "strategy_or_response_status": {
                "proof_status": proof_status,
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": bool(s.get("proof_status")) if orchestrator_context else True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
            "execution_state": {"broker_ready": False if orchestrator_context else True, "spread_pass": True, "slippage_pass": True},
        }
        req = WorkflowRouteRequest.model_validate(s.get("request", default_req) if isinstance(s.get("request"), dict) else default_req)
        resp = route_next_workflow(req)
        return {
            "tool_name": "workflow_router.route_next_workflow",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": "strategy_eligibility_agent",
            "safety": safety,
        }

    if agent_key == "strategy_eligibility_agent":
        from app.services.strategy_eligibility.models import StrategyEligibilityCheckRequest
        from app.services.strategy_eligibility.service import check_strategy_eligibility

        strategy_key = str(s.get("strategy_key") or ("pending_strategy_selection" if orchestrator_context else "regime_aware_momentum_catalyst"))
        proof_status = _proof_status_for_eligibility(s.get("proof_status"), orchestrator_context=orchestrator_context)
        default_req = {
            "workflow_context": {
                "selected_workflow": "baseline_fast_path",
                "workflow_mode": "baseline",
                "session": "market_open",
            },
            "strategy_candidate": {
                "strategy_key": strategy_key,
                "strategy_group": "regime_aware_momentum",
                "proof_status": proof_status,
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": bool(s.get("proof_status")) if orchestrator_context else True,
            },
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "pass",
                "urgency": "high",
            },
            "account_state": {"risk_budget_available": True, "paper_trading_enabled": True, "live_trading_enabled": False, "human_approval_required": True},
            "features": {
                "rvol_elevated": True,
                "price_above_vwap": True,
                "vwap_reclaiming": False,
                "relative_strength_positive": True,
                "catalyst_confirmed": True,
                "volume_confirms": False,
                "spread_pass": True,
                "risk_reward_pass": True,
            },
        }
        raw = s.get("request") if isinstance(s.get("request"), dict) else None
        if raw:
            merged = {**default_req, **raw}
            dwc = dict(default_req.get("workflow_context") or {})
            rwc = raw.get("workflow_context") if isinstance(raw.get("workflow_context"), dict) else {}
            merged["workflow_context"] = {**dwc, **rwc}
            df = dict(default_req.get("features") or {})
            rf = raw.get("features") if isinstance(raw.get("features"), dict) else {}
            merged["features"] = {**df, **rf}
            req_payload = merged
        else:
            req_payload = default_req
        req = StrategyEligibilityCheckRequest.model_validate(req_payload)
        resp = check_strategy_eligibility(req)
        return {
            "tool_name": "strategy_eligibility.check_strategy_eligibility",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": "trigger_monitor_agent",
            "safety": safety,
        }

    if agent_key == "trigger_monitor_agent":
        from app.services.trigger_monitoring.models import TriggerMonitoringEvaluateRequest
        from app.services.trigger_monitoring.service import evaluate_trigger

        sym = _first_symbol(s)
        strategy_key = str(s.get("strategy_key") or ("pending_strategy_selection" if orchestrator_context else "regime_aware_momentum_catalyst"))

        default_req = {
            "workflow_context": {
                "selected_workflow": "baseline_fast_path",
                "workflow_mode": "baseline",
                "session": "market_open",
            },
            "eligibility_context": {
                "eligible": True,
                "eligibility_status": "eligible",
                "strategy_key": strategy_key,
                "strategy_group": "regime_aware_momentum",
            },
            "trigger_candidate": {
                "symbol": sym,
                "asset_class": "stock",
                "horizon": "day_trading",
                "trigger_key": "rvol_vwap_breakout_confirm",
                "created_at": "2026-05-07T09:55:00-05:00",
                "expires_at": "2026-05-07T10:30:00-05:00",
                "trigger_price": 150.0,
                "current_price": 151.20,
                "vwap": 150.5,
            },
            "current_state": {
                "evaluated_at": "2026-05-07T10:00:00-05:00",
                "data_quality": "pass",
                "spread_pass": True,
                "volume_confirms": True,
                "price_above_trigger": True,
                "price_above_vwap": True,
                "invalidation_hit": False,
            },
        }
        raw = s.get("request") if isinstance(s.get("request"), dict) else None
        if raw:
            merged = {**default_req, **raw}
            for key in ("workflow_context", "eligibility_context", "trigger_candidate", "current_state"):
                d = dict(default_req.get(key) or {})
                r = raw.get(key) if isinstance(raw.get(key), dict) else {}
                merged[key] = {**d, **r}
            req_payload = merged
        else:
            req_payload = default_req
        req = TriggerMonitoringEvaluateRequest.model_validate(req_payload)
        resp = evaluate_trigger(req)
        # If fired, proceed to execution planner
        fired = False
        te = resp.get("trigger_evaluation") if isinstance(resp, dict) else None
        if isinstance(te, dict) and str(te.get("trigger_state")) == "fired":
            fired = True
        return {
            "tool_name": "trigger_monitoring.evaluate_trigger",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": "execution_planner_agent" if fired else None,
            "safety": safety,
        }

    if agent_key == "execution_planner_agent":
        from app.services.execution_planner.models import ExecutionPlannerPlanRequest
        from app.services.execution_planner.service import plan_execution

        sym = _first_symbol(s)
        account_equity = _orchestrator_account_equity(s) if orchestrator_context else 10000.0
        if orchestrator_context and s.get("max_risk_dollars") is not None:
            max_risk = round((float(s.get("max_risk_dollars") or 0.0) / account_equity) * 100.0, 4) if account_equity > 0 else 0.5
        else:
            max_risk = float(s.get("max_risk_per_trade_percent") or (0.5 if orchestrator_context else 1.0))
        max_position = 5.0 if orchestrator_context else 20.0

        default_req = {
            "trigger_evaluation": {
                "trigger_state": "fired",
                "symbol": sym,
                "asset_class": "stock",
                "horizon": "day_trading",
                "trigger_key": "rvol_vwap_breakout_confirm",
            },
            "market_snapshot": {
                "current_price": 151.20,
                "vwap": 150.5,
                "atr": 2.3,
                "bid": 151.15,
                "ask": 151.25,
                "spread_percent": 0.02,
                "volume_confirms": True,
            },
            "account_state": {
                "account_equity": account_equity,
                "cash": account_equity,
                "risk_budget_available": True,
                "max_risk_per_trade_percent": max_risk,
                "max_position_size_percent": max_position,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
                "execution_enabled": False if orchestrator_context else True,
            },
            "planning_preferences": {
                "order_style": "limit",
                "stop_method": "atr",
                "target_reward_risk": 2.0,
                "atr_stop_multiplier": 1.0,
                "max_spread_percent": 0.15,
                "allow_submit": False,
            },
        }
        raw = s.get("request") if isinstance(s.get("request"), dict) else None
        if raw:
            merged = {**default_req, **raw}
            for key in ("trigger_evaluation", "market_snapshot", "account_state", "planning_preferences"):
                d = dict(default_req.get(key) or {})
                r = raw.get(key) if isinstance(raw.get(key), dict) else {}
                merged[key] = {**d, **r}
            req_payload = merged
        else:
            req_payload = default_req
        req = ExecutionPlannerPlanRequest.model_validate(req_payload)
        resp = plan_execution(req)
        return {
            "tool_name": "execution_planner.plan_execution",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": "execution_approval_agent",
            "safety": safety,
        }

    if agent_key == "execution_approval_agent":
        from app.services.approval_queue.models import ApprovalItemCreate
        from app.services.approval_queue.service import create_item

        workflow_run_id = context.get("workflow_run_id") or inputs.get("workflow_run_id") or ""
        orchestrator_run_id = context.get("orchestrator_run_id") or inputs.get("orchestrator_run_id")
        agent_run_id = context.get("agent_run_id")

        if not isinstance(workflow_run_id, str) or not workflow_run_id.strip():
            return {
                "tool_name": "approval_queue.create_item",
                "tool_request": {"workflow_run_id": workflow_run_id, "orchestrator_run_id": orchestrator_run_id},
                "tool_response": {"status": "blocked", "blockers": ["missing_workflow_run_id"], "warnings": [], "next_action": "Run via orchestrator so workflow_run_id is set."},
                "next_agent": None,
                "safety": safety,
            }

        body = ApprovalItemCreate(
            workflow_run_id=workflow_run_id,
            orchestrator_run_id=str(orchestrator_run_id) if orchestrator_run_id else None,
            agent_run_id=str(agent_run_id) if agent_run_id else None,
            approval_type="execution_boundary",
            status="pending",
            requested_action={"action": "approve_execution_handoff", "note": "paper-first; no submit performed"},
            risk_summary={"note": "Stage 10 approval boundary. Orders are never submitted by this agent."},
            required_approver="owner",
        )
        out = create_item(body)
        return {
            "tool_name": "approval_queue.create_item",
            "tool_request": body.model_dump(),
            "tool_response": {"status": "ok", "approval": out.model_dump()},
            "next_agent": None,
            "safety": safety,
        }

    if agent_key == "narrative_review_agent":
        # v1 policy: narrative review is optional/deferred and must not call LLMs by default.
        return {
            "tool_name": "narrative_review.skipped_by_policy",
            "tool_request": {"policy": "deferred_v1_no_llm"},
            "tool_response": {
                "status": "ok",
                "narrative": None,
                "blockers": [],
                "warnings": ["narrative_review_deferred_by_policy"],
                "next_action": "Narrative review is optional; enable LLM policy later if desired.",
            },
            "next_agent": None,
            "safety": safety,
        }

    if agent_key == "position_monitor_agent":
        from app.services.position_monitoring.models import PositionMonitoringEvaluateRequest
        from app.services.position_monitoring.service import evaluate_position

        sym = _first_symbol(s)
        account_equity = _orchestrator_account_equity(s) if orchestrator_context else 10000.0
        strategy_key = str(s.get("strategy_key") or ("pending_strategy_selection" if orchestrator_context else "regime_aware_momentum_catalyst"))
        default_req = {
            "position": {
                "position_id": "pos_sample",
                "symbol": sym,
                "asset_class": "stock",
                "horizon": "day_trading",
                "side": "long",
                "quantity": 13,
                "entry_price": 151.15,
                "current_price": 152.20,
                "stop_loss": 148.85,
                "target_price": 155.60,
                "opened_at": "2026-05-07T09:40:00-05:00",
            },
            "thesis": {
                "strategy_key": strategy_key,
                "trigger_key": "rvol_vwap_breakout_confirm",
                "vwap": 149.80,
                "price_above_vwap": True,
                "volume_confirms": True,
                "relative_strength_positive": True,
                "invalidation_hit": False,
            },
            "risk_state": {
                "account_equity": account_equity,
                "max_daily_loss_percent": float(s.get("max_daily_loss_percent") or (1.5 if orchestrator_context else 3.0)),
                "current_daily_loss_percent": 0.4,
                "max_position_size_percent": 5.0 if orchestrator_context else 20.0,
                "force_close_requested": False,
                "emergency_stop": False,
            },
            "monitoring_preferences": {"time_stop_minutes": 45, "reduce_at_r_multiple": 1.5, "exit_at_thesis_invalid": True},
            "evaluated_at": "2026-05-07T10:00:00-05:00",
        }
        req = PositionMonitoringEvaluateRequest.model_validate(s.get("request", default_req) if isinstance(s.get("request"), dict) else default_req)
        resp = evaluate_position(req)
        pe = resp.get("position_evaluation") if isinstance(resp, dict) else None
        ra = pe.get("recommended_action") if isinstance(pe, dict) else None
        next_agent = "close_review_agent" if ra in {"reduce", "exit_review"} else "position_monitor_agent"
        return {
            "tool_name": "position_monitoring.evaluate_position",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": next_agent,
            "safety": safety,
        }

    if agent_key == "close_review_agent":
        from app.services.close_position.models import ClosePositionReviewRequest
        from app.services.close_position.service import review_close_position

        sym = _first_symbol(s)
        default_req = {
            "position_evaluation": {
                "evaluation_id": "pm_sample",
                "position_id": "pos_sample",
                "symbol": sym,
                "asset_class": "stock",
                "horizon": "day_trading",
                "position_status": "exit_review",
                "recommended_action": "exit_review",
                "pnl": {"unrealized_pnl": -29.90, "unrealized_pnl_percent": -1.52, "r_multiple": -1.0},
                "risk": {"risk_per_share": 2.30, "current_distance_to_stop": 0.0, "distance_to_target": 6.75, "position_notional": 1935.70, "position_size_percent": 19.36, "daily_loss_percent": 0.7},
                "thesis_validity": {"valid": False, "score": 0.25, "failed_reasons": ["invalidation_hit"], "passed_reasons": []},
                "blockers": [],
                "warnings": ["thesis_invalidated"],
            },
            "position": {"quantity": 13, "side": "long", "current_price": 148.90, "entry_price": 151.15},
            "master_admin": {
                "workflow_enabled": True,
                "execution_enabled": False,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "broker_execution_enabled": False,
                "human_approval_required": True,
                "emergency_stop": False,
                "force_close_requested": False,
            },
            "review_preferences": {"reduce_percent": 50, "close_reason": "stage_11_exit_review", "order_style": "market", "allow_submit": False},
        }
        req = ClosePositionReviewRequest.model_validate(s.get("request", default_req) if isinstance(s.get("request"), dict) else default_req)
        # Force allow_submit false
        req.review_preferences.allow_submit = False
        resp = review_close_position(req)
        return {
            "tool_name": "close_position.review_close_position",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": "post_trade_evaluator_agent",
            "safety": safety,
        }

    if agent_key == "post_trade_evaluator_agent":
        from app.services.post_trade_evaluation.models import PostTradeEvaluationEvaluateRequest
        from app.services.post_trade_evaluation.service import evaluate_post_trade

        sym = _first_symbol(s)
        strategy_key = str(s.get("strategy_key") or ("pending_strategy_selection" if orchestrator_context else "regime_aware_momentum_catalyst"))
        default_req = {
            "trade": {
                "trade_id": "trade_sample",
                "symbol": sym,
                "asset_class": "stock",
                "horizon": "day_trading",
                "side": "long",
                "quantity": 13,
                "planned_entry_price": 151.15,
                "actual_entry_price": 151.20,
                "planned_exit_price": 155.60,
                "actual_exit_price": 155.50,
                "stop_loss": 148.85,
                "target_price": 155.60,
                "opened_at": "2026-05-07T09:40:00-05:00",
                "closed_at": "2026-05-07T10:25:00-05:00",
                "exit_reason": "target_hit",
            },
            "workflow_context": {"selected_workflow": "baseline_fast_path", "strategy_key": strategy_key, "trigger_key": "rvol_vwap_breakout_confirm", "session": "market_open"},
            "thesis_outcome": {"thesis_valid_at_exit": True, "invalidation_hit": False, "price_above_vwap_at_exit": True, "volume_confirmed_at_exit": True, "relative_strength_positive_at_exit": True},
            "execution_quality": {"planned_entry_price": 151.15, "actual_entry_price": 151.20, "planned_exit_price": 155.60, "actual_exit_price": 155.50, "max_allowed_slippage_percent": 0.15},
            "rule_compliance": {"entered_after_trigger": True, "used_approved_strategy": True, "respected_position_size": True, "respected_stop_loss": True, "respected_master_admin_gates": True, "human_approval_obtained": True},
        }
        req = PostTradeEvaluationEvaluateRequest.model_validate(s.get("request", default_req) if isinstance(s.get("request"), dict) else default_req)
        resp = evaluate_post_trade(req)
        return {
            "tool_name": "post_trade_evaluation.evaluate_post_trade",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": "learning_loop_agent",
            "safety": safety,
        }

    if agent_key == "learning_loop_agent":
        from app.services.learning_loop.models import LearningLoopEvaluateRequest
        from app.services.learning_loop.service import evaluate_learning_loop

        strategy_key = str(s.get("strategy_key") or ("pending_strategy_selection" if orchestrator_context else "regime_aware_momentum_catalyst"))
        proof_status = str(s.get("proof_status") or ("unknown" if orchestrator_context else "paper_passed"))
        default_req = {
            "strategy_key": strategy_key,
            "strategy_group": "regime_aware_momentum",
            "asset_class": "stock",
            "horizon": "day_trading",
            "workflow_key": "baseline_fast_path",
            "recent_outcomes": [
                {"trade_id": "trade_1", "outcome_label": "target_hit", "outcome_status": "positive", "realized_pnl": 55.90, "r_multiple": 1.83, "slippage_status": "pass", "rule_compliant": True},
                {"trade_id": "trade_2", "outcome_label": "stopped_out", "outcome_status": "negative", "realized_pnl": -29.90, "r_multiple": -1.0, "slippage_status": "pass", "rule_compliant": True},
            ],
            "current_status": {"promotion_status": "paper_ready", "proof_status": proof_status, "sample_size": 12, "current_drawdown_r": -1.5, "last_10_avg_r": 0.42},
            "thresholds": {"min_sample_size_for_promotion": 20, "min_avg_r_for_promotion": 0.35, "max_drawdown_r_before_demotion": -3.0, "max_rule_violation_rate": 0.10, "max_slippage_fail_rate": 0.15},
        }
        req = LearningLoopEvaluateRequest.model_validate(s.get("request", default_req) if isinstance(s.get("request"), dict) else default_req)
        resp = evaluate_learning_loop(req)
        return {
            "tool_name": "learning_loop.evaluate_learning_loop",
            "tool_request": req.model_dump(),
            "tool_response": resp,
            "next_agent": None,
            "safety": safety,
        }

    # Fallback
    return {
        "tool_name": "not_implemented",
        "tool_request": s,
        "tool_response": {"status": "not_implemented", "message": "No wrapper implemented for this agent in Phase 2."},
        "next_agent": None,
        "safety": safety,
    }

