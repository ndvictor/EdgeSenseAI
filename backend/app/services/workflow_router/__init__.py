"""Stage 5 — Workflow Router (deterministic AI-Agent, no LLM).

This package implements a rules-based router that:
- observes workflow-relevant state (session, market condition, proofs, account/risk, execution readiness)
- evaluates deterministic constraints and safety checks
- selects the next workflow route
- stores the latest decision in memory for retrieval

No external calls. No LLM. No live trading actions.
"""

from .models import WorkflowRouteRequest, WorkflowRouteDecision, WorkflowRouterStatusResponse
from .service import get_latest_decision, route_next_workflow, build_status

__all__ = [
    "WorkflowRouteRequest",
    "WorkflowRouteDecision",
    "WorkflowRouterStatusResponse",
    "get_latest_decision",
    "route_next_workflow",
    "build_status",
]

