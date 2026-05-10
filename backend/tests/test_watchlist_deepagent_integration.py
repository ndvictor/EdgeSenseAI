"""Integration tests for the watchlist_builder_agent → DeepAgents agentic decision flow.

Step 2 makes ``watchlist_builder_agent`` an agentic *selector*: when
``AGENT_REASONING_ENABLED=true`` the audited DeepAgent decision becomes the
watchlist tool response. These tests cover all 14 scenarios from the spec:

1.  Reasoning enabled with real candidates lets watchlist_builder_agent select usable_symbols.
2.  Reasoning enabled with no candidates returns no_qualified_setup and cannot create symbols.
3.  Unknown symbol in DeepAgent output is rejected.
4.  Stale/default/universe symbols are excluded from evidence pack.
5.  candidate_source cannot become universe_selection.
6.  DeepAgent can rank candidates from allowed_symbols.
7.  DeepAgent can reject candidates with reasons.
8.  Rejected DeepAgent output does not update usable_symbols.
9.  selected_symbol remains null.
10. submitted_order=false.
11. broker_called=false.
12. llm_used_for_trade_decision=false.
13. No mock/synthetic data.
14. AGENT_REASONING_ENABLED=false falls back to safe non-agentic behavior.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

import app.services.deepagents_runtime.supervisor as deepagents_supervisor
from app.services.agent_runtime.service import _attach_advisory_reasoning
from app.services.deepagents_runtime import EvidencePackBuilder


# --------------------------------------------------------------------------- #
# Fake deepagents factory                                                     #
# --------------------------------------------------------------------------- #


class _FakeCompiledAgent:
    """Stand-in for a deepagents CompiledStateGraph."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def invoke(self, _state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": [{"role": "assistant", "content": json.dumps(self._payload)}]}


def _install_fake_deepagents(monkeypatch, payload: dict[str, Any]) -> None:
    def factory(*_args: Any, **_kwargs: Any) -> _FakeCompiledAgent:
        return _FakeCompiledAgent(payload)

    monkeypatch.setattr(deepagents_supervisor, "_load_create_deep_agent", lambda: factory)


def _real_scanner_row(symbol: str, *, price: float = 100.0, **overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": symbol,
        "source": "scanner",
        "source_type": "scanner",
        "candidate_source": "scanner",
        "provider_name": "provider_test",
        "last_price": price,
        "relative_volume": 3.0,
        "data_quality": "real",
    }
    row.update(overrides)
    return row


def _real_feature_row(symbol: str, *, price: float = 100.0, **overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": symbol,
        "source": "feature_store",
        "provider_name": "provider_test",
        "last_price": price,
        "data_quality": "real",
    }
    row.update(overrides)
    return row


def _baseline_tool_response(symbols: list[str]) -> dict[str, Any]:
    """A deterministic watchlist output mirroring what build_watchlist would produce."""
    return {
        "decision": "candidate_selected" if symbols else "no_trade",
        "symbols": list(symbols),
        "usable_symbols": list(symbols),
        "selected_candidate": None,
        "selected_symbol": None,
        "candidate_source": "scanner" if symbols else "none",
        "scanner_candidates": [_real_scanner_row(s) for s in symbols],
        "feature_rows": [_real_feature_row(s) for s in symbols],
        "raw_candidate_count": len(symbols),
        "filtered_candidate_count": len(symbols),
    }


# --------------------------------------------------------------------------- #
# 1. Reasoning enabled + real candidates → agent selects usable_symbols       #
# --------------------------------------------------------------------------- #


def test_01_reasoning_enabled_lets_watchlist_agent_select_usable_symbols(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.72,
            "thesis": "Provider-backed real candidates ranked by relative volume.",
            "usable_symbols": ["TSLA"],
            "rejected_symbols": [{"symbol": "F", "reason": "low_relative_volume"}],
            "candidate_rankings": [
                {"symbol": "TSLA", "score": 0.9, "reason": "rvol_5x"},
                {"symbol": "F", "score": 0.3, "reason": "rvol_1.1x"},
            ],
            "candidate_source": "scanner",
            "data_used": {"provider_chain": ["provider_test"], "symbols": ["TSLA", "F"]},
        },
    )

    tool_response = _baseline_tool_response(["TSLA", "F"])
    merged, reasoning, warnings = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_01",
        inputs={"workflow_request_symbols": ["TSLA", "F"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert warnings == []
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "completed"
    assert reasoning["decision"] == "candidates_selected"
    assert merged["agentic_decision_applied"] is True
    assert merged["usable_symbols"] == ["TSLA"]
    assert merged["symbols"] == ["TSLA"]
    # Alpha selects later — selected_symbol stays null at watchlist stage.
    assert merged["selected_candidate"] is None
    assert merged["selected_symbol"] is None
    assert merged["candidate_source"] == "scanner"
    assert merged["watchlist_agent_decision"]["usable_symbols"] == ["TSLA"]
    assert merged["llm_used"] is True
    assert merged["agent_reasoning_enabled"] is True


# --------------------------------------------------------------------------- #
# 2. Reasoning enabled + no candidates → no_qualified_setup, no symbol invent #
# --------------------------------------------------------------------------- #


def test_02_no_candidates_returns_no_qualified_setup(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    # Even if the LLM tries to invent ones, there are no allowed_symbols, so the
    # supervisor short-circuits to ``blocked``/``no_qualified_setup``.
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.99,
            "thesis": "TSLA looks strong (hostile invented).",
            "usable_symbols": ["TSLA"],
            "candidate_rankings": [{"symbol": "TSLA", "score": 1.0}],
            "candidate_source": "scanner",
        },
    )

    tool_response = _baseline_tool_response([])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_02",
        inputs={},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["decision"] == "no_qualified_setup"
    assert merged["agentic_decision_applied"] is True
    assert merged["usable_symbols"] == []
    assert merged["symbols"] == []
    assert merged["candidate_source"] == "none"
    assert merged["selected_symbol"] is None
    assert merged["selected_candidate"] is None
    assert merged["recommendation"]["status"] == "no_qualified_setup"
    assert merged["recommendation"]["symbol"] is None
    assert merged["recommendation"]["reason"] == "no_real_scanner_candidates"


# --------------------------------------------------------------------------- #
# 3. Unknown symbol in DeepAgent output is rejected                           #
# --------------------------------------------------------------------------- #


def test_03_unknown_symbol_in_agent_output_rejected(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.8,
            "thesis": "Provider-backed thesis on real candidate only.",
            "usable_symbols": ["NVDA"],  # NVDA is NOT in evidence
            "candidate_rankings": [{"symbol": "NVDA", "score": 0.95}],
            "candidate_source": "scanner",
            "data_used": {"provider_chain": ["provider_test"], "symbols": ["NVDA"]},
        },
    )

    tool_response = _baseline_tool_response(["TSLA"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_03",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert any(b == "hallucinated_symbol:NVDA" for b in reasoning["hard_blockers"])
    assert merged["agentic_decision_applied"] is False
    # Test 8: deterministic usable_symbols preserved on rejection.
    assert merged["usable_symbols"] == ["TSLA"]


# --------------------------------------------------------------------------- #
# 4. Stale/default/universe rows are excluded from evidence pack              #
# --------------------------------------------------------------------------- #


def test_04_stale_default_universe_symbols_excluded_from_evidence():
    workflow_state = {
        "workflow_run_id": "wr_test_04",
        "scanner_candidates": [
            _real_scanner_row("TSLA"),
            _real_scanner_row("UNI", source="universe_selection", source_type="universe_selection"),
            _real_scanner_row("CUNI", source="candidate_universe", candidate_source="candidate_universe"),
            _real_scanner_row("DEF", source="default", candidate_source="default"),
            _real_scanner_row("FB", source="fallback", candidate_source="fallback"),
            _real_scanner_row("OLD", stale=True),
            _real_scanner_row("FAILX", data_quality="fail"),
        ],
        "feature_rows": [
            _real_feature_row("TSLA"),
            _real_feature_row("OLD2", is_stale=True),
            _real_feature_row("UNIV2", source="universe_selection"),
        ],
    }
    pack = EvidencePackBuilder.build(workflow_state, "watchlist_builder_agent")
    assert pack.allowed_symbols == ["TSLA"]
    pack_symbols = {r.get("symbol") for r in pack.scanner_candidates}
    assert pack_symbols == {"TSLA"}
    feat_symbols = {r.get("symbol") for r in pack.candidate_features}
    assert feat_symbols == {"TSLA"}


# --------------------------------------------------------------------------- #
# 5. candidate_source cannot become universe_selection                        #
# --------------------------------------------------------------------------- #


def test_05_candidate_source_cannot_become_universe_selection(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.7,
            "thesis": "Tries to claim universe_selection source.",
            "usable_symbols": ["TSLA"],
            "candidate_source": "universe_selection",  # forbidden
        },
    )

    tool_response = _baseline_tool_response(["TSLA"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_05",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert any(b.startswith("forbidden_candidate_source") for b in reasoning["hard_blockers"])
    # Wrapper kept the deterministic, valid source rather than promoting universe_selection.
    assert merged["candidate_source"] == "scanner"
    assert merged["agentic_decision_applied"] is False


# --------------------------------------------------------------------------- #
# 6. Agent can rank candidates from allowed_symbols                           #
# --------------------------------------------------------------------------- #


def test_06_agent_can_rank_candidates_from_allowed_symbols(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.65,
            "thesis": "TSLA leads on rvol; F trails.",
            "usable_symbols": ["TSLA", "F"],
            "candidate_rankings": [
                {"symbol": "TSLA", "score": 0.91, "reason": "rvol_5.0x"},
                {"symbol": "F", "score": 0.42, "reason": "rvol_1.6x"},
            ],
            "candidate_source": "scanner",
        },
    )

    tool_response = _baseline_tool_response(["TSLA", "F"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_06",
        inputs={"workflow_request_symbols": ["TSLA", "F"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "completed"
    rankings = merged["candidate_rankings"]
    assert [r["symbol"] for r in rankings] == ["TSLA", "F"]
    assert rankings[0]["score"] == pytest.approx(0.91)
    assert rankings[1]["score"] == pytest.approx(0.42)


# --------------------------------------------------------------------------- #
# 7. Agent can reject candidates with reasons                                 #
# --------------------------------------------------------------------------- #


def test_07_agent_can_reject_candidates_with_reasons(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.6,
            "thesis": "Selecting TSLA only; F failed liquidity gate.",
            "usable_symbols": ["TSLA"],
            "rejected_symbols": [
                {"symbol": "F", "reason": "spread_too_wide"},
            ],
            "candidate_rankings": [{"symbol": "TSLA", "score": 0.8}],
            "candidate_source": "scanner",
        },
    )

    tool_response = _baseline_tool_response(["TSLA", "F"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_07",
        inputs={"workflow_request_symbols": ["TSLA", "F"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "completed"
    assert merged["rejected_symbols"] == [{"symbol": "F", "reason": "spread_too_wide"}]
    assert merged["usable_symbols"] == ["TSLA"]


# --------------------------------------------------------------------------- #
# 8. Rejected DeepAgent output does not update usable_symbols                 #
# --------------------------------------------------------------------------- #


def test_08_rejected_output_does_not_update_usable_symbols(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.9,
            "thesis": "Tries to push hallucinated AMZN.",
            "usable_symbols": ["AMZN"],  # not in allowed
            "candidate_source": "scanner",
        },
    )

    tool_response = _baseline_tool_response(["TSLA"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_08",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert merged["agentic_decision_applied"] is False
    # Deterministic value preserved.
    assert merged["usable_symbols"] == ["TSLA"]
    assert merged["symbols"] == ["TSLA"]


# --------------------------------------------------------------------------- #
# 9. selected_symbol remains null                                             #
# --------------------------------------------------------------------------- #


def test_09_selected_symbol_remains_null_in_watchlist_stage(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.6,
            "thesis": "Real candidate.",
            "usable_symbols": ["TSLA"],
            "candidate_source": "scanner",
        },
    )

    tool_response = _baseline_tool_response(["TSLA"])
    # Even if the deterministic stage suggested a selected_candidate, watchlist
    # stage must clear it — Alpha selects later.
    tool_response["selected_candidate"] = "TSLA"
    tool_response["selected_symbol"] = "TSLA"

    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_09",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "completed"
    assert merged["agentic_decision_applied"] is True
    assert merged["selected_symbol"] is None
    assert merged["selected_candidate"] is None
    assert merged["recommendation"]["symbol"] is None


# --------------------------------------------------------------------------- #
# 10/11/12. Submit / broker / trade-decision flags stay false                 #
# --------------------------------------------------------------------------- #


def test_10_11_12_submit_broker_trade_flags_remain_false(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    # Hostile output that tries to claim broker/submit succeeded.
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.9,
            "thesis": "Real TSLA candidate.",
            "usable_symbols": ["TSLA"],
            "candidate_source": "scanner",
            "submitted_order": True,
            "broker_called": True,
            "llm_used_for_trade_decision": True,
        },
    )

    tool_response = _baseline_tool_response(["TSLA"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_10",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    # Reasoning payload stripped clean.
    assert reasoning["submitted_order"] is False
    assert reasoning["broker_called"] is False
    assert reasoning["llm_used_for_trade_decision"] is False
    # Merged output also clean.
    assert merged["submitted_order"] is False
    assert merged["broker_called"] is False
    assert merged["llm_used_for_trade_decision"] is False


# --------------------------------------------------------------------------- #
# 13. No mock/synthetic data                                                  #
# --------------------------------------------------------------------------- #


def test_13_mock_or_synthetic_claims_are_rejected(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "confidence": 0.5,
            "thesis": "Synthetic backfill suggests TSLA is favorable.",
            "usable_symbols": ["TSLA"],
            "candidate_source": "scanner",
        },
    )

    tool_response = _baseline_tool_response(["TSLA"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_13",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert any(b == "reasoning_referenced_non_real_data" for b in reasoning["hard_blockers"])
    assert merged["agentic_decision_applied"] is False
    assert merged["usable_symbols"] == ["TSLA"]


# --------------------------------------------------------------------------- #
# 14. AGENT_REASONING_ENABLED=false → safe non-agentic behavior               #
# --------------------------------------------------------------------------- #


def test_14_reasoning_disabled_falls_back_to_safe_non_agentic_behavior(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "false")
    # Even if a fake LLM is wired, it must not be called when reasoning is off.
    _install_fake_deepagents(
        monkeypatch,
        {
            "agent_key": "watchlist_builder_agent",
            "reasoning_status": "completed",
            "decision": "candidates_selected",
            "thesis": "Should never be reached.",
            "usable_symbols": ["AMZN"],
        },
    )

    tool_response = _baseline_tool_response(["TSLA", "F"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="watchlist_builder_agent",
        workflow_run_id="wr_test_14",
        inputs={"workflow_request_symbols": ["TSLA", "F"]},
        context={},
        tool_request={"tool_name": "watchlist_builder.discovery"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "disabled"
    assert reasoning["llm_used"] is False
    # Deterministic output preserved exactly.
    assert merged["usable_symbols"] == ["TSLA", "F"]
    assert merged["symbols"] == ["TSLA", "F"]
    assert merged["candidate_source"] == "scanner"
    assert merged["agentic_decision_applied"] is False
    assert merged["agent_reasoning_enabled"] is False
    # Safety flags still forced false.
    assert merged["submitted_order"] is False
    assert merged["broker_called"] is False
    assert merged["llm_used_for_trade_decision"] is False
