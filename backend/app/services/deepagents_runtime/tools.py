"""Evidence-only tools exposed to DeepAgents."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.deepagents_runtime.schemas import DeepAgentToolSpec, EvidencePack


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

    def call(self, name: str, **kwargs: Any) -> Any:
        if name not in self._handlers:
            raise ValueError(f"DeepAgent tool is not registered: {name}")
        return self._handlers[name](**kwargs)

    def list_specs(self) -> list[DeepAgentToolSpec]:
        return list(self._specs.values())

    def list_handlers(self) -> list[Callable[..., Any]]:
        return list(self._handlers.values())


class EvidenceTools:
    """Tool wrappers that read only from an immutable evidence pack."""

    def __init__(self, evidence: EvidencePack) -> None:
        self.evidence = evidence

    def scanner_get_latest_candidates(self) -> dict[str, Any]:
        """Return scanner candidates already present in the evidence pack."""
        return {
            "allowed_symbols": list(self.evidence.allowed_symbols),
            "scanner_candidates": list(self.evidence.scanner_candidates),
            "candidate_count": len(self.evidence.allowed_symbols),
        }

    def features_get_enriched_rows(self, symbols: list[str] | None = None) -> dict[str, Any]:
        """Return enriched rows for evidence symbols only."""
        requested = {str(s).strip().upper() for s in symbols or self.evidence.allowed_symbols if s}
        allowed = set(self.evidence.allowed_symbols)
        rows = [
            dict(row)
            for row in self.evidence.candidate_features
            if str(row.get("symbol") or row.get("ticker") or "").strip().upper() in requested & allowed
        ]
        return {"feature_rows": rows, "symbols": sorted(requested & allowed)}

    def account_get_policy(self) -> dict[str, Any]:
        """Return account policy from workflow state; never call broker APIs."""
        return dict(self.evidence.account_policy)

    def market_session_get_state(self) -> dict[str, Any]:
        """Return market session state from workflow state."""
        return dict(self.evidence.market_session)

    def alpha_generate_recommendation(self) -> dict[str, Any]:
        """Return existing alpha recommendation evidence; do not generate new market data."""
        return dict(self.evidence.alpha_recommendation)

    def risk_evaluate_fractional_feasibility(self, symbol: str | None = None) -> dict[str, Any]:
        """Return fractional feasibility context for an allowed symbol."""
        sym = str(symbol or "").strip().upper()
        if sym and sym not in set(self.evidence.allowed_symbols):
            return {"status": "blocked", "blockers": [f"symbol_not_in_evidence:{sym}"]}
        return {"status": "ok", "symbol": sym or None, "risk_sizing_context": dict(self.evidence.risk_sizing_context)}

    def execution_planner_plan_execution(self, symbol: str | None = None) -> dict[str, Any]:
        """Return plan-only execution context. This never submits or calls a broker."""
        sym = str(symbol or "").strip().upper()
        if sym and sym not in set(self.evidence.allowed_symbols):
            return {"status": "blocked", "blockers": [f"symbol_not_in_evidence:{sym}"], "submitted_order": False, "broker_called": False}
        return {
            "status": "plan_only",
            "symbol": sym or None,
            "execution_plan": dict(self.evidence.execution_plan),
            "submitted_order": False,
            "broker_called": False,
            "allow_submit": False,
        }


def default_tool_registry(evidence: EvidencePack | None = None) -> DeepAgentToolRegistry:
    """Register the fixed evidence-only tool surface."""
    registry = DeepAgentToolRegistry()
    tools = EvidenceTools(
        evidence
        or EvidencePack(
            workflow_run_id="unknown",
            agent_key="watchlist_builder_agent",
            allowed_symbols=[],
            hard_rules=["No evidence pack supplied."],
        )
    )
    specs = (
        ("scanner.get_latest_candidates", "Read scanner candidates already included in the evidence pack.", tools.scanner_get_latest_candidates),
        ("features.get_enriched_rows", "Read enriched feature rows already included in the evidence pack.", tools.features_get_enriched_rows),
        ("account.get_policy", "Read workflow account policy without broker calls.", tools.account_get_policy),
        ("market_session.get_state", "Read market session state from the evidence pack.", tools.market_session_get_state),
        ("alpha.generate_recommendation", "Read existing alpha recommendation evidence.", tools.alpha_generate_recommendation),
        ("risk.evaluate_fractional_feasibility", "Evaluate fractional feasibility from evidence context only.", tools.risk_evaluate_fractional_feasibility),
        ("execution_planner.plan_execution", "Build plan-only execution context without broker calls.", tools.execution_planner_plan_execution),
    )
    for name, description, handler in specs:
        registry.register(DeepAgentToolSpec(name=name, description=description, json_schema={}), handler)
    return registry
