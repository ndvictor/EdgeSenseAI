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
    """Register advisory subagents using existing workflow agent names."""
    registry = SubagentRegistry()
    for key, description, capabilities in (
        (
            "market_condition_agent",
            "Review market condition evidence and session context.",
            ["market_session.get_state", "scanner.get_latest_candidates"],
        ),
        (
            "watchlist_builder_agent",
            "Review provider-backed watchlist candidates without adding symbols.",
            ["scanner.get_latest_candidates", "features.get_enriched_rows"],
        ),
        (
            "alpha_engine_agent",
            "Review existing alpha recommendation evidence.",
            ["alpha.generate_recommendation", "features.get_enriched_rows"],
        ),
        (
            "strategy_selection_agent",
            "Review strategy evidence without promoting strategies.",
            ["alpha.generate_recommendation"],
        ),
        (
            "model_selection_agent",
            "Review model evidence without activating models.",
            ["features.get_enriched_rows"],
        ),
        (
            "small_account_feasibility_agent",
            "Review small-account feasibility evidence.",
            ["account.get_policy", "risk.evaluate_fractional_feasibility"],
        ),
        (
            "execution_planner_agent",
            "Review plan-only execution evidence without broker calls.",
            ["execution_planner.plan_execution", "account.get_policy"],
        ),
    ):
        registry.register(SubagentDescriptor(key=key, description=description, capabilities=capabilities))
    return registry
