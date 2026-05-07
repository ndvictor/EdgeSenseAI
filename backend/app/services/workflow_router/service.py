from __future__ import annotations

from typing import Any

from app.services.workflow_router.models import (
    CheckerResult,
    WorkflowRouteDecision,
    WorkflowRouteRequest,
    WorkflowRouterStatusResponse,
    iso_utc_now,
)
from app.services.workflow_router.rules import (
    SUPPORTED_WORKFLOWS,
    evaluate_data_quality_checker,
    evaluate_execution_readiness_checker,
    evaluate_proof_status_checker,
    evaluate_risk_state_checker,
    evaluate_session_checker,
    evaluate_urgency_checker,
    route_rules_v1,
)

# In-memory latest decision (single-process; deterministic and test-friendly).
_LATEST_DECISION: WorkflowRouteDecision | None = None


def _deterministic_decision_id(ts_iso: str) -> str:
    # ISO-like, stable prefix; avoids randomness while still unique per second.
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"wf_{compact}"


def get_latest_decision() -> WorkflowRouteDecision | None:
    return _LATEST_DECISION


def build_status() -> WorkflowRouterStatusResponse:
    latest = get_latest_decision()
    updated_at = iso_utc_now()
    return WorkflowRouterStatusResponse(
        status="ok",
        stage={"stage_number": 5, "stage_name": "Workflow Router", "stage_key": "workflow_router"},
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "router_status": "ready",
            "llm_required": False,
            "baseline_workflow_available": True,
            "adjusted_workflow_available": True,
            "latest_decision_id": (latest.decision_id if latest else None),
            "next_action": "Run workflow route decision.",
        },
        supported_workflows=list(SUPPORTED_WORKFLOWS),
        checkers=[
            {"key": "session_checker", "label": "Session Checker", "status": "ready", "uses_llm": False},
            {"key": "urgency_checker", "label": "Urgency Checker", "status": "ready", "uses_llm": False},
            {"key": "proof_status_checker", "label": "Proof Status Checker", "status": "ready", "uses_llm": False},
            {"key": "risk_state_checker", "label": "Risk State Checker", "status": "ready", "uses_llm": False},
        ],
    )


def route_next_workflow(request: WorkflowRouteRequest) -> dict[str, Any]:
    """
    Orchestrate deterministic Stage-5 routing.

    This is an AI-Agent *without* an LLM:
    it observes state, evaluates constraints, selects a route, and stores a decision.
    """
    global _LATEST_DECISION

    created_at = iso_utc_now()
    decision_id = _deterministic_decision_id(created_at)

    session_eval = evaluate_session_checker(request.session, request.execution_state)
    urgency_eval = evaluate_urgency_checker(request.market_condition.urgency)
    proof_eval = evaluate_proof_status_checker(request.strategy_or_response_status.proof_status, request.session)
    data_eval = evaluate_data_quality_checker(request.market_condition.data_quality)
    risk_eval = evaluate_risk_state_checker(request.account_state.risk_budget_available)
    exec_eval = evaluate_execution_readiness_checker(request.session, request.execution_state)

    result = route_rules_v1(
        session=request.session,
        market_condition=request.market_condition,
        strategy_status=request.strategy_or_response_status,
        account_state=request.account_state.model_dump(),
        execution_state=request.execution_state,
    )

    decision = WorkflowRouteDecision(
        decision_id=decision_id,
        selected_workflow=result.selected_workflow,
        workflow_mode=result.workflow_mode,
        reason=result.reason,
        blocked_stages=result.blocked_stages,
        checkers={
            "session_checker": CheckerResult(status=session_eval.status, message=session_eval.message),
            "urgency_checker": CheckerResult(status=urgency_eval.status, message=urgency_eval.message),
            "proof_status_checker": CheckerResult(status=proof_eval.status, message=proof_eval.message),
            "data_quality_checker": CheckerResult(status=data_eval.status, message=data_eval.message),
            "risk_state_checker": CheckerResult(status=risk_eval.status, message=risk_eval.message),
            "execution_readiness_checker": CheckerResult(status=exec_eval.status, message=exec_eval.message),
        },
        next_action=result.next_action,
        created_at=created_at,
    )

    _LATEST_DECISION = decision
    return {"status": "ok", "decision": decision.model_dump()}

