from __future__ import annotations

from app.services.agent_runtime.models import AgentRunResult, WorkflowRunRecord


# In-memory storage (Phase 0/1)
_WORKFLOW_RUNS: dict[str, WorkflowRunRecord] = {}
_AGENT_RUNS: dict[str, AgentRunResult] = {}
_LATEST_AGENT_RUN_BY_KEY: dict[str, str] = {}  # agent_key -> run_id
_IDEMPOTENCY_INDEX: dict[str, str] = {}  # fingerprint -> run_id


def store_workflow_run(rec: WorkflowRunRecord) -> None:
    _WORKFLOW_RUNS[rec.workflow_run_id] = rec


def get_workflow_run(workflow_run_id: str) -> WorkflowRunRecord | None:
    return _WORKFLOW_RUNS.get(workflow_run_id)


def list_workflow_runs() -> list[WorkflowRunRecord]:
    return list(_WORKFLOW_RUNS.values())


def store_agent_run(result: AgentRunResult) -> None:
    _AGENT_RUNS[result.run_id] = result
    _LATEST_AGENT_RUN_BY_KEY[result.agent_key] = result.run_id


def get_agent_run(run_id: str) -> AgentRunResult | None:
    return _AGENT_RUNS.get(run_id)


def list_agent_runs() -> list[AgentRunResult]:
    return list(_AGENT_RUNS.values())


def get_latest_agent_run_id(agent_key: str) -> str | None:
    return _LATEST_AGENT_RUN_BY_KEY.get(agent_key)


def index_idempotency(fingerprint: str, run_id: str) -> None:
    _IDEMPOTENCY_INDEX[fingerprint] = run_id


def lookup_idempotency(fingerprint: str) -> str | None:
    return _IDEMPOTENCY_INDEX.get(fingerprint)


def persistence_mode() -> str:
    # DB hooks are intentionally deferred unless explicitly required.
    return "memory"

