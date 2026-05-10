"""Tool registry for deep agents: names, specs, and optional call routing hooks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.deepagents_runtime.schemas import DeepAgentToolSpec


class DeepAgentToolRegistry:
    """Registers tools by name; handlers can be attached when wiring the runtime."""

    def __init__(self) -> None:
        self._specs: dict[str, DeepAgentToolSpec] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(self, spec: DeepAgentToolSpec, handler: Callable[..., Any] | None = None) -> None:
        self._specs[spec.name] = spec
        if handler is not None:
            self._handlers[spec.name] = handler

    def get_spec(self, name: str) -> DeepAgentToolSpec | None:
        return self._specs.get(name)

    def list_specs(self) -> list[DeepAgentToolSpec]:
        return list(self._specs.values())


def default_tool_registry() -> DeepAgentToolRegistry:
    """Empty registry; callers populate with domain tools."""
    return DeepAgentToolRegistry()
