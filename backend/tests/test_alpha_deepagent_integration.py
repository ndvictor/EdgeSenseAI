"""Integration tests for alpha_engine_agent → DeepAgents agentic recommendations."""

from __future__ import annotations

import json
from typing import Any

import pytest

import app.services.deepagents_runtime.supervisor as deepagents_supervisor
from app.services.agent_runtime.service import _attach_advisory_reasoning


STRATEGY_KEY = "relative_volume_momentum_breakout_v1"


class _FakeCompiledAgent:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def invoke(self, _state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": [{"role": "assistant", "content": json.dumps(self._payload)}]}


def _install_fake_deepagents(monkeypatch, payload: dict[str, Any]) -> None:
    def factory(*_args: Any, **_kwargs: Any) -> _FakeCompiledAgent:
        return _FakeCompiledAgent(payload)

    monkeypatch.setattr(deepagents_supervisor, "_load_create_deep_agent", lambda: factory)


def _feature_row(symbol: str = "TSLA", **overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": symbol,
        "source": "feature_store",
        "provider_name": "provider_test",
        "data_quality": "real",
        "last_price": 10.0,
        "entry": 10.0,
        "stop": 9.5,
        "target": 11.0,
        "volume": 5_000_000,
        "avg_volume": 1_000_000,
        "relative_volume": 5.0,
        "spread_bps": 8.0,
        "vwap": 9.8,
        "price_above_vwap": True,
        "trend_score": 80.0,
        "liquidity_score": 85.0,
    }
    row.update(overrides)
    return row


def _scanner_row(symbol: str = "TSLA", **overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": symbol,
        "source": "scanner",
        "candidate_source": "scanner",
        "provider_name": "provider_test",
        "data_quality": "real",
        "last_price": 10.0,
    }
    row.update(overrides)
    return row


def _safe_alpha_response(symbols: list[str] | None = None) -> dict[str, Any]:
    symbols = symbols or []
    rec = {
        "status": "no_qualified_setup",
        "symbol": None,
        "strategy_key": None,
        "setup_type": None,
        "scanner_score": None,
        "model_score": None,
        "evidence_score": None,
        "small_account_score": None,
        "strategy_fit_score": None,
        "final_score": None,
        "confidence": None,
        "entry_plan": {
            "entry": None,
            "stop": None,
            "target": None,
            "risk_per_share": None,
            "risk_dollars": None,
            "expected_r": None,
            "position_size_estimate": None,
            "plan_type": None,
            "notes": [],
        },
        "blockers": [],
        "warnings": [],
        "reason": "safe deterministic fallback",
        "non_real_data_used": False,
        "synthetic_data_used": False,
        "submitted_order": False,
        "broker_called": False,
        "llm_used_for_trade_decision": False,
    }
    return {
        "usable_symbols": list(symbols),
        "scanner_candidates": [_scanner_row(symbol) for symbol in symbols],
        "feature_rows": [_feature_row(symbol) for symbol in symbols],
        "strategy_registry": {"selected_strategy_key": STRATEGY_KEY},
        "alpha_recommendation": rec,
        "recommendation": rec,
        "alpha_status": rec["status"],
        "alpha_selected_symbol": None,
        "alpha_strategy_key": None,
        "alpha_score": None,
        "alpha_reason": rec["reason"],
        "alpha_blockers": [],
        "alpha_warnings": [],
        "submitted_order": False,
        "broker_called": False,
        "llm_used": False,
    }


def _accepted_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "agent_key": "alpha_engine_agent",
        "reasoning_status": "completed",
        "decision": "candidate_selected",
        "symbol": "TSLA",
        "strategy_key": STRATEGY_KEY,
        "setup_type": "relative_volume_momentum_breakout",
        "scanner_score": 88.0,
        "model_score": 40.0,
        "evidence_score": 70.0,
        "small_account_score": 90.0,
        "strategy_fit_score": 85.0,
        "final_score": 84.0,
        "confidence": 0.81,
        "thesis": "TSLA has real feature evidence and matches the configured strategy.",
        "bull_case": ["relative volume and VWAP alignment"],
        "bear_case": ["intraday reversal risk"],
        "missing_evidence": [],
        "risk_notes": ["small risk budget requires small size"],
        "recommended_next_action": "Proceed to strategy selection review.",
        "hard_blockers": [],
        "soft_warnings": [],
        "entry_plan": {
            "entry": 10.0,
            "stop": 9.5,
            "target": 11.0,
            "risk_per_share": 0.5,
            "risk_dollars": 5.0,
            "expected_r": 2.0,
            "position_size_estimate": 10,
            "plan_type": "paper_plan_candidate",
            "notes": ["uses feature-row prices only"],
        },
        "recommendation_id": "alpha_test_tsla",
        "predicted_return_pct": 10.0,
        "predicted_return_r": 0.8,
        "predicted_win_probability": 0.62,
        "predicted_expected_value_r": 0.86,
        "prediction_horizon_minutes": 60,
        "prediction_model_key": "heuristic_alpha_v1",
        "prediction_reason": "Heuristic score from real Alpha evidence.",
        "data_used": {"provider_chain": ["provider_test"], "symbols": ["TSLA"], "prices": {"TSLA": 10.0}},
        "submitted_order": False,
        "broker_called": False,
        "llm_used_for_trade_decision": False,
    }
    payload.update(overrides)
    return payload


def _run(payload: dict[str, Any], tool_response: dict[str, Any] | None = None):
    return _attach_advisory_reasoning(
        agent_key="alpha_engine_agent",
        workflow_run_id="wr_alpha_deepagent",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "alpha_engine.generate_recommendation"},
        tool_response=tool_response or _safe_alpha_response(["TSLA"]),
    )


def test_01_reasoning_enabled_real_candidate_selects_candidate(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload())

    merged, reasoning, warnings = _run(_accepted_payload())

    assert warnings == []
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "completed"
    assert merged["agentic_decision_applied"] is True
    assert merged["alpha_status"] == "candidate_selected"
    assert merged["alpha_selected_symbol"] == "TSLA"
    assert merged["alpha_strategy_key"] == STRATEGY_KEY


def test_02_no_candidates_returns_no_qualified_setup(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload(symbol="TSLA"))

    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="alpha_engine_agent",
        workflow_run_id="wr_alpha_empty",
        inputs={},
        context={},
        tool_request={"tool_name": "alpha_engine.generate_recommendation"},
        tool_response=_safe_alpha_response([]),
    )

    assert reasoning is not None
    assert reasoning["decision"] == "no_qualified_setup"
    assert merged["alpha_status"] == "no_qualified_setup"
    assert merged["alpha_recommendation"]["symbol"] is None
    assert merged["alpha_recommendation"]["strategy_key"] is None
    assert merged["alpha_recommendation"]["entry_plan"]["entry"] is None
    assert merged["alpha_reason"] == "no_real_alpha_candidates"


def test_03_unknown_symbol_in_data_used_rejected(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload(data_used={"symbols": ["NVDA"]}))

    merged, reasoning, _ = _run(_accepted_payload())

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert any(b == "hallucinated_symbol:NVDA" for b in reasoning["hard_blockers"])
    assert merged["agentic_decision_applied"] is False


def test_04_symbol_outside_allowed_symbols_rejected(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload(symbol="NVDA", data_used={"symbols": ["TSLA"]}))

    merged, reasoning, _ = _run(_accepted_payload())

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert any(b == "hallucinated_symbol:NVDA" for b in reasoning["hard_blockers"])
    assert merged["agentic_decision_applied"] is False


def test_05_invented_entry_price_rejected(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    payload = _accepted_payload(entry_plan={**_accepted_payload()["entry_plan"], "entry": 999.99})
    _install_fake_deepagents(monkeypatch, payload)

    merged, reasoning, _ = _run(payload)

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert any(b.startswith("invented_price:TSLA:999.99") for b in reasoning["hard_blockers"])
    assert merged["agentic_decision_applied"] is False


def test_06_strategy_key_not_in_registry_rejected(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload(strategy_key="unknown_strategy_v1"))

    merged, reasoning, _ = _run(_accepted_payload())

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert any(b == "unknown_strategy_key:unknown_strategy_v1" for b in reasoning["hard_blockers"])
    assert merged["agentic_decision_applied"] is False


def test_07_trained_model_claim_without_evidence_rejected(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    payload = _accepted_payload(prediction_model_key="trained_xgboost_v1", prediction_reason="Trained model inference selected this setup.")
    _install_fake_deepagents(monkeypatch, payload)

    merged, reasoning, _ = _run(payload)

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "trained_model_claim_without_evidence" in reasoning["hard_blockers"]
    assert merged["agentic_decision_applied"] is False


def test_08_accepted_alpha_decision_populates_alpha_recommendation(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload())

    merged, reasoning, _ = _run(_accepted_payload())

    assert reasoning is not None
    rec = merged["alpha_recommendation"]
    assert rec["status"] == "candidate_selected"
    assert rec["symbol"] == "TSLA"
    assert rec["strategy_key"] == STRATEGY_KEY
    assert rec["entry_plan"]["entry"] == pytest.approx(10.0)
    assert rec["reason"] == reasoning["thesis"]


def test_09_accepted_alpha_decision_carries_expected_return_fields(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload())

    merged, _reasoning, _ = _run(_accepted_payload())
    rec = merged["alpha_recommendation"]

    assert rec["recommendation_id"] == "alpha_test_tsla"
    assert rec["predicted_return_pct"] == pytest.approx(10.0)
    assert rec["predicted_return_r"] == pytest.approx(0.8)
    assert rec["predicted_win_probability"] == pytest.approx(0.62)
    assert rec["predicted_expected_value_r"] == pytest.approx(0.86)
    assert rec["prediction_horizon_minutes"] == 60
    assert rec["prediction_model_key"] == "heuristic_alpha_v1"


def test_10_rejected_alpha_decision_does_not_overwrite_safe_no_qualified_setup(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload(symbol="NVDA", data_used={"symbols": ["TSLA"]}))

    merged, reasoning, _ = _run(_accepted_payload())

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert merged["agentic_decision_applied"] is False
    assert merged["alpha_status"] == "no_qualified_setup"
    assert merged["alpha_recommendation"]["symbol"] is None
    assert merged["alpha_selected_symbol"] is None


def _run_hostile_execution_claim(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(
        monkeypatch,
        _accepted_payload(submitted_order=True, broker_called=True, llm_used_for_trade_decision=True),
    )

    return _run(_accepted_payload())


def test_11_submitted_order_false(monkeypatch):
    merged, reasoning, _ = _run_hostile_execution_claim(monkeypatch)

    assert reasoning is not None
    assert reasoning["submitted_order"] is False
    assert merged["submitted_order"] is False


def test_12_broker_called_false(monkeypatch):
    merged, reasoning, _ = _run_hostile_execution_claim(monkeypatch)

    assert reasoning is not None
    assert reasoning["broker_called"] is False
    assert merged["broker_called"] is False


def test_13_llm_used_for_trade_decision_false(monkeypatch):
    merged, reasoning, _ = _run_hostile_execution_claim(monkeypatch)

    assert reasoning is not None
    assert reasoning["llm_used_for_trade_decision"] is False
    assert merged["llm_used_for_trade_decision"] is False


def test_14_no_mock_or_synthetic_data(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, _accepted_payload(thesis="Synthetic feature data supports TSLA."))

    merged, reasoning, _ = _run(_accepted_payload())

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "reasoning_referenced_non_real_data" in reasoning["hard_blockers"]
    assert merged["agentic_decision_applied"] is False


def test_15_reasoning_disabled_falls_back_to_existing_alpha_behavior(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "false")
    _install_fake_deepagents(monkeypatch, _accepted_payload(symbol="NVDA"))

    tool_response = _safe_alpha_response(["TSLA"])
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="alpha_engine_agent",
        workflow_run_id="wr_alpha_disabled",
        inputs={"workflow_request_symbols": ["TSLA"]},
        context={},
        tool_request={"tool_name": "alpha_engine.generate_recommendation"},
        tool_response=tool_response,
    )

    assert reasoning is not None
    assert reasoning["reasoning_status"] == "disabled"
    assert reasoning["llm_used"] is False
    assert merged["agentic_decision_applied"] is False
    assert merged["alpha_recommendation"] == tool_response["alpha_recommendation"]
    assert merged["submitted_order"] is False
    assert merged["broker_called"] is False
    assert merged["llm_used_for_trade_decision"] is False
