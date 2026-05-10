"""Supervisor loop for deep multi-agent turns (plan → delegate → merge)."""

from __future__ import annotations

from typing import Any

from app.services.deepagents_runtime.schemas import DeepAgentRunContext
from app.services.deepagents_runtime.subagents import SubagentRegistry, default_subagent_registry
from app.services.deepagents_runtime.tools import DeepAgentToolRegistry, default_tool_registry


class DeepAgentSupervisor:
    """Coordinates subagents and tools for one high-level objective."""

    def __init__(
        self,
        *,
        tools: DeepAgentToolRegistry | None = None,
        subagents: SubagentRegistry | None = None,
    ) -> None:
        self.tools = tools or default_tool_registry()
        self.subagents = subagents or default_subagent_registry()

    def turn(self, *, objective: str, context: DeepAgentRunContext, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute a single supervisor turn; extend with real planning/delegation logic."""
        return {
            "status": "noop",
            "objective": objective,
            "context": context.model_dump(),
            "inputs": dict(inputs),
            "tools_registered": [s.name for s in self.tools.list_specs()],
            "subagents": self.subagents.list_keys(),
        }


def run_supervisor_turn(
    *,
    objective: str,
    context: DeepAgentRunContext,
    inputs: dict[str, Any],
    supervisor: DeepAgentSupervisor | None = None,
) -> dict[str, Any]:
    svc = supervisor or DeepAgentSupervisor()
    return svc.turn(objective=objective, context=context, inputs=inputs)
