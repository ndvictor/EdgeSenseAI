"""Deep multi-agent runtime: supervisor, subagents, tools, evidence, and safety boundaries."""

from __future__ import annotations

from app.services.deepagents_runtime.evidence import EvidenceBundle, build_evidence_bundle
from app.services.deepagents_runtime.safety import DeepAgentSafetyResult, enforce_deep_agent_safety
from app.services.deepagents_runtime.schemas import DeepAgentRunContext, DeepAgentToolSpec
from app.services.deepagents_runtime.subagents import SubagentRegistry, default_subagent_registry
from app.services.deepagents_runtime.supervisor import DeepAgentSupervisor, run_supervisor_turn
from app.services.deepagents_runtime.tools import DeepAgentToolRegistry, default_tool_registry

__all__ = [
    "DeepAgentRunContext",
    "DeepAgentSafetyResult",
    "DeepAgentSupervisor",
    "DeepAgentToolRegistry",
    "DeepAgentToolSpec",
    "EvidenceBundle",
    "SubagentRegistry",
    "build_evidence_bundle",
    "default_subagent_registry",
    "default_tool_registry",
    "enforce_deep_agent_safety",
    "run_supervisor_turn",
]
