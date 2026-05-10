"""Safety boundaries for deep-agent orchestration (no external I/O)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeepAgentSafetyResult:
    sanitized_inputs: dict[str, Any]
    blockers: list[str]
    warnings: list[str]


def enforce_deep_agent_safety(*, inputs: dict[str, Any], context: dict[str, Any]) -> DeepAgentSafetyResult:
    """Normalize inputs and apply conservative gates before any tool or subagent dispatch."""
    blockers: list[str] = []
    warnings: list[str] = []
    sanitized = dict(inputs or {})

    if bool(sanitized.get("allow_submit")):
        sanitized["allow_submit"] = False
        warnings.append("deep_agent_allow_submit_forced_false")

    if bool(sanitized.get("submitted_order")) or bool(sanitized.get("broker_called")):
        blockers.append("deep_agent_submit_or_broker_claim_blocked")

    return DeepAgentSafetyResult(
        sanitized_inputs=sanitized,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )
