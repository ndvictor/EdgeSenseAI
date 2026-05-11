"""Boundary tests for the DeepAgents advisory runtime.

These tests verify:
- Evidence pack contains only allowed symbols (never invented).
- Reasoning-disabled fallback is safe.
- No-candidate scenarios resolve to ``no_qualified_setup``.
- LLM is never marked as having driven the trade decision.
- ``submitted_order=False`` and ``broker_called=False`` always.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.deepagents_runtime import (
    DeepAgentDecision,
    DeepAgentSupervisor,
    EvidencePack,
    EvidencePackBuilder,
)


# ---------- Evidence pack ----------


def test_evidence_pack_contains_only_allowed_symbols_from_real_rows():
    state = {
        "workflow_run_id": "wr_test",
        "scanner_candidates": [
            {"symbol": "TSLA", "provider_name": "alpaca", "data_quality": "real", "last_price": 240.5},
        ],
        "feature_rows": [
            {"symbol": "TSLA", "last_price": 240.5, "volume": 1000, "provider_name": "alpaca"},
        ],
        # Request symbols alone must not become evidence unless backed by rows:
        "symbols": ["FAKE_TICKER"],
    }

    evidence = EvidencePackBuilder.build(state, "watchlist_builder_agent")

    assert evidence.allowed_symbols == ["TSLA"]
    assert "FAKE_TICKER" not in evidence.allowed_symbols
    assert evidence.provider_status["provider_chain"] == ["alpaca"]
    assert evidence.known_prices.get("TSLA") == [240.5]


def test_evidence_pack_with_zero_rows_yields_empty_allowed_symbols():
    state = {"workflow_run_id": "wr_test", "scanner_candidates": [], "feature_rows": []}

    evidence = EvidencePackBuilder.build(state, "watchlist_builder_agent")

    assert evidence.allowed_symbols == []
    assert evidence.has_candidates() is False


# ---------- Reasoning disabled fallback ----------


def test_reasoning_disabled_returns_safe_fallback(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "false")

    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="watchlist_builder_agent",
        allowed_symbols=["TSLA"],
        hard_rules=["Do not invent symbols"],
    )
    decision = DeepAgentSupervisor().reason(evidence=evidence)

    assert decision.reasoning_status == "disabled"
    assert decision.llm_used is False
    assert decision.llm_used_for_trade_decision is False
    assert decision.submitted_order is False
    assert decision.broker_called is False
    assert decision.decision == "needs_more_evidence"


# ---------- No candidates ----------


def test_zero_candidates_returns_no_qualified_setup(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")

    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="watchlist_builder_agent",
        allowed_symbols=[],
        hard_rules=["Zero candidates must propagate as no_qualified_setup"],
    )
    decision = DeepAgentSupervisor().reason(evidence=evidence)

    assert decision.decision == "no_qualified_setup"
    assert "no_scanner_candidates_passed_filters" in decision.hard_blockers
    assert decision.submitted_order is False
    assert decision.broker_called is False
    assert decision.llm_used_for_trade_decision is False


# ---------- Non-watchlist agents stay deterministic ----------


@pytest.mark.parametrize(
    "agent_key",
    [
        # These agents have NOT been upgraded to DeepAgents yet and must remain
        # deterministic. ``watchlist_builder_agent``, ``alpha_engine_agent``,
        # ``small_account_feasibility_agent``, and ``execution_planner_agent``
        # ARE intentionally routed through DeepAgents and are covered by their
        # own integration tests.
        "market_condition_agent",
        "strategy_selection_agent",
        "model_selection_agent",
    ],
)
def test_non_watchlist_agents_are_not_routed_through_deepagents(monkeypatch, agent_key):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")

    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key=agent_key,
        allowed_symbols=["TSLA"],
        hard_rules=["watchlist_only_integration"],
    )
    decision = DeepAgentSupervisor().reason(evidence=evidence)

    assert decision.reasoning_status == "disabled"
    assert decision.llm_used is False
    assert "deepagent_not_integrated_for_agent" in decision.soft_warnings


# ---------- Injected LLM still cannot break safety boundaries ----------


def _fake_agent_factory(payload: dict[str, Any]):
    """Return a fake create_deep_agent_fn that ignores tools/subagents and emits ``payload``."""

    class _Agent:
        def invoke(self, _state: dict[str, Any]) -> dict[str, Any]:
            return {"messages": [{"role": "assistant", "content": __import__("json").dumps(payload)}]}

    def factory(*_args: Any, **_kwargs: Any) -> _Agent:
        return _Agent()

    return factory


def test_llm_used_for_trade_decision_is_always_false_even_when_llm_runs(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")

    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="watchlist_builder_agent",
        allowed_symbols=["TSLA"],
        known_prices={"TSLA": [240.5]},
        hard_rules=["advisory_only"],
    )
    payload = {
        "agent_key": "watchlist_builder_agent",
        "reasoning_status": "completed",
        "decision": "candidate_selected",
        "confidence": 0.6,
        "thesis": "Real-data-only thesis on TSLA.",
        "data_used": {"provider_chain": ["alpaca"], "symbols": ["TSLA"], "prices": {"TSLA": 240.5}},
        # The model attempts to claim it submitted; the runtime must always force this to False.
        "submitted_order": True,
        "broker_called": True,
        "llm_used_for_trade_decision": True,
    }
    supervisor = DeepAgentSupervisor(create_deep_agent_fn=_fake_agent_factory(payload))
    decision = supervisor.reason(evidence=evidence)

    assert isinstance(decision, DeepAgentDecision)
    assert decision.submitted_order is False
    assert decision.broker_called is False
    assert decision.llm_used_for_trade_decision is False


def test_no_deepagents_install_returns_llm_unavailable(monkeypatch):
    """When ``deepagents`` cannot be imported, the runtime must return a safe fallback."""
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")

    import app.services.deepagents_runtime.supervisor as sup
    monkeypatch.setattr(sup, "_load_create_deep_agent", lambda: None)

    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="watchlist_builder_agent",
        allowed_symbols=["TSLA"],
        hard_rules=["advisory_only"],
    )
    decision = DeepAgentSupervisor().reason(evidence=evidence)

    assert decision.reasoning_status == "llm_unavailable"
    assert decision.llm_used is False
    assert decision.submitted_order is False
    assert decision.broker_called is False
    assert decision.llm_used_for_trade_decision is False
