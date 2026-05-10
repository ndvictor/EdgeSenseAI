"""Evidence aggregation for deep-agent runs (structured summaries for audits and downstream stages)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceBundle(BaseModel):
    """Serialized evidence produced or referenced during a deep-agent turn."""

    workflow_run_id: str | None = None
    agent_keys: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    citations: list[str] = Field(default_factory=list)


def build_evidence_bundle(
    *,
    workflow_run_id: str | None,
    agent_keys: list[str],
    artifacts: dict[str, Any] | None = None,
    citations: list[str] | None = None,
) -> EvidenceBundle:
    return EvidenceBundle(
        workflow_run_id=workflow_run_id,
        agent_keys=list(agent_keys),
        artifacts=dict(artifacts or {}),
        citations=list(citations or []),
    )
