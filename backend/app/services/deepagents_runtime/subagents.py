"""Subagent registry and lightweight descriptors for delegated work."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SubagentDescriptor(BaseModel):
    """Metadata for a logical subagent role."""

    key: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)


class SubagentRegistry:
    """Holds registered subagents for supervisor routing."""

    def __init__(self) -> None:
        self._agents: dict[str, SubagentDescriptor] = {}

    def register(self, descriptor: SubagentDescriptor) -> None:
        self._agents[descriptor.key] = descriptor

    def get(self, key: str) -> SubagentDescriptor | None:
        return self._agents.get(key)

    def list_keys(self) -> list[str]:
        return sorted(self._agents.keys())


def default_subagent_registry() -> SubagentRegistry:
    """Empty registry; wire strategy-specific subagents at integration time."""
    return SubagentRegistry()
