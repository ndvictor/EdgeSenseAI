"""Agent Runtime Foundation v1 (Phase 0/1 only; deterministic; no LLM).

Provides shared agent contracts, registry, run recording, trace persistence (in-memory),
and idempotency protection. Does NOT execute real tools or call stage services until Phase 2.
"""

from .models import (
    AgentDescriptor,
    AgentRunRequest,
    AgentRunResult,
    AgentRuntimeStatusResponse,
    WorkflowRunCreateRequest,
    WorkflowRunRecord,
)
from .registry import list_agents, require_agent
from .service import (
    build_status,
    create_agent_run,
    create_workflow_run,
    get_agent_run,
    get_latest_snapshot,
    get_workflow_run,
)

__all__ = [
    "AgentDescriptor",
    "AgentRunRequest",
    "AgentRunResult",
    "WorkflowRunCreateRequest",
    "WorkflowRunRecord",
    "AgentRuntimeStatusResponse",
    "list_agents",
    "require_agent",
    "build_status",
    "create_workflow_run",
    "get_workflow_run",
    "create_agent_run",
    "get_agent_run",
    "get_latest_snapshot",
]

