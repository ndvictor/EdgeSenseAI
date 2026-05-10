"""Integration tests for small_account_feasibility_agent DeepAgent decisions."""

from __future__ import annotations

import json
from typing import Any

import pytest

import app.services.deepagents_runtime.supervisor as deepagents_supervisor
from app.services.agent_runtime.service import _attach_advisory_reasoning
from app.services.agent_runtime.wrappers.small_account_feasibility_adapter import (
    evaluate_small_account_inputs,
    merge_small_account_feasibility_context,
)
from app.services.deepagents_runtime.evidence import EvidencePackBuilder


class _FakeCompiledAgent:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def invoke(self, _state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": [{"role": "assistant", "content": json.dumps(self._payload)}]}


def _install_fake_deepagents(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> None:
    def factory(*_args: Any, **_kwargs: Any) -> _FakeCompiledAgent:
        return _FakeCompiledAgent(payload)

    monkeypatch.setattr(deepagents_supervisor, "_load_create_deep_agent", lambda: factory)


def _alpha_recommendation(**overrides: Any) -> dict[str, Any]:
    rec = {
        "status": "candidate_selected",
        "symbol": "TSLA",
        "strategy_key": "relative_volume_momentum_breakout_v1",
        "setup_type": "relative_volume_momentum_breakout",
        "final_score": 84.0,
        "confidence": 0.8,
        "entry_plan": {
            "entry": 400.0,
            "stop": 396.0,
            "target": 410.0,
            "risk_per_share": 4.0,
            "risk_dollars": 10.0,
            "expected_r": 1.5,
            "position_size_estimate": 2.5,
            "plan_type": "paper_plan_candidate",
            "notes": [],
        },
        "predicted_return_r": 1.2,
        "predicted_expected_value_r": 0.7,
        "predicted_win_probability": 0.6,
        "submitted_order": False,
        "broker_called": False,
        "llm_used_for_trade_decision": False,
    }
    rec.update(overrides)
    return rec


def _feature_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": "TSLA",
        "source": "feature_store",
        "candidate_source": "scanner",
        "provider_name": "provider_test",
        "data_quality": "real",
        "last_price": 400.0,
        "entry": 400.0,
        "stop": 396.0,
        "target": 410.0,
        "spread_bps": 8.0,
        "volume": 5_000_000.0,
        "avg_volume": 4_000_000.0,
        "dollar_volume": 2_000_000_000.0,
        "relative_volume": 1.25,
    }
    row.update(overrides)
    return row


def _inputs(**overrides: Any) -> dict[str, Any]:
    payload = {
        "alpha_selected_symbol": "TSLA",
        "alpha_strategy_key": "relative_volume_momentum_breakout_v1",
        "alpha_recommendation": _alpha_recommendation(),
        "feature_rows": [_feature_row()],
        "scanner_candidates": [_feature_row(source="scanner")],
        "account_equity": 1000.0,
        "buying_power": 5000.0,
        "fractional_trading_enabled": True,
        "max_risk_per_trade_pct": 1.0,
        "max_position_notional_pct": 100.0,
        "max_position_notional": 1500.0,
        "min_order_notional": 1.0,
        "market_session": "regular_market",
        "execution_mode": "plan_only",
        "proof_status": "paper_passed",
        "persistence_status": "persisted",
        "paper_trading_enabled": True,
        "live_trading_enabled": False,
        "broker_execution_enabled": False,
    }
    payload.update(overrides)
    return payload


def _tool_response(inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    return evaluate_small_account_inputs(inputs or _inputs())


def _accepted_payload(tool_response: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    payload = {
        "agent_key": "small_account_feasibility_agent",
        "reasoning_status": "completed",
        "decision": "feasible",
        "symbol": "TSLA",
        "confidence": 0.82,
        "thesis": "The deterministic sizing tool shows fractional TSLA sizing fits risk, notional, buying power, and liquidity.",
        "bull_case": ["fractional sizing keeps risk bounded"],
        "bear_case": ["spread and slippage still need plan-only execution review"],
        "missing_evidence": [],
        "risk_notes": ["Use deterministic position sizing output."],
        "recommended_next_action": "Proceed to execution_planner_agent for plan-only execution.",
        "hard_blockers": [],
        "soft_warnings": [],
        "account_feasibility_decision": tool_response["account_feasibility_decision"],
        "small_account_decision": tool_response["small_account_decision"],
        "fractional_feasible": tool_response["fractional_feasible"],
        "fractional_trading_enabled": tool_response["fractional_trading_enabled"],
        "position_size_shares": tool_response["position_size_shares"],
        "position_size_notional": tool_response["position_size_notional"],
        "risk_dollars": tool_response["risk_dollars"],
        "risk_per_share": tool_response["risk_per_share"],
        "max_loss_if_stopped": tool_response["max_loss_if_stopped"],
        "expected_profit_dollars": tool_response["expected_profit_dollars"],
        "expected_value_dollars": tool_response["expected_value_dollars"],
        "notional_usage_pct": tool_response["notional_usage_pct"],
        "buying_power_usage_pct": tool_response["buying_power_usage_pct"],
        "liquidity_participation_pct": tool_response["liquidity_participation_pct"],
        "spread_cost_estimate": tool_response["spread_cost_estimate"],
        "slippage_cost_estimate": tool_response["slippage_cost_estimate"],
        "expected_r_after_costs": tool_response["expected_r_after_costs"],
        "feasible_symbols": tool_response["feasible_symbols"],
        "rejected_symbols": [],
        "entry_plan": {"entry": 400.0, "stop": 396.0, "target": 410.0},
        "data_used": {"provider_chain": ["provider_test"], "symbols": ["TSLA"], "prices": {"TSLA": 400.0}},
        "submitted_order": False,
        "broker_called": False,
        "llm_used_for_trade_decision": False,
    }
    payload.update(overrides)
    return payload


def _run(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any], inputs: dict[str, Any] | None = None):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    _install_fake_deepagents(monkeypatch, payload)
    actual_inputs = inputs or _inputs()
    return _attach_advisory_reasoning(
        agent_key="small_account_feasibility_agent",
        workflow_run_id="wr_account_feasibility",
        inputs=actual_inputs,
        context={},
        tool_request={"tool_name": "small_account_feasibility.evaluate"},
        tool_response=_tool_response(actual_inputs),
    )


def test_01_tool_result_is_included_in_evidence_pack():
    inputs = _inputs()
    tool_response = _tool_response(inputs)
    evidence = EvidencePackBuilder.build({**inputs, **tool_response, "tool_result": tool_response}, "small_account_feasibility_agent")
    assert evidence.tool_result["position_size_shares"] == pytest.approx(2.5)
    assert evidence.tool_result["account_feasibility_decision"] == "feasible"


def test_02_accepted_deepagent_feasibility_output_becomes_agent_output(monkeypatch):
    tool_response = _tool_response()
    merged, reasoning, warnings = _run(monkeypatch, _accepted_payload(tool_response))
    assert warnings == []
    assert reasoning is not None
    assert merged["agentic_decision_applied"] is True
    assert merged["account_feasibility_status"] == "feasible"
    assert merged["position_size_shares"] == pytest.approx(2.5)
    assert merged["next_agent"] == "execution_planner_agent"


def test_03_rejected_deepagent_output_does_not_overwrite_safe_tool_result(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, position_size_shares=99.0)
    merged, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert merged["agentic_decision_applied"] is False
    assert merged["position_size_shares"] == pytest.approx(tool_response["position_size_shares"])


def test_04_deepagent_inconsistent_with_deterministic_sizing_is_rejected(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, expected_r_after_costs=999.0)
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert "expected_r_after_costs_contradicts_fractional_sizing_tool" in reasoning["hard_blockers"]


def test_05_deepagent_cannot_block_solely_because_price_is_high(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(
        tool_response,
        decision="blocked",
        account_feasibility_decision="feasible",
        thesis="Block TSLA because the share price is too high.",
        hard_blockers=["share_price_too_high"],
    )
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "blocked_solely_because_share_price_high" in reasoning["hard_blockers"]


def test_06_glue_carries_alpha_entry_plan_into_feasibility_stage():
    merged = merge_small_account_feasibility_context(_inputs(entry=None, stop=None, target=None))
    assert merged["entry"] == pytest.approx(400.0)
    assert merged["stop"] == pytest.approx(396.0)
    assert merged["target"] == pytest.approx(410.0)
    assert merged["selected_symbol"] == "TSLA"


def test_07_glue_carries_spread_dollar_volume_and_volume_into_feasibility_stage():
    merged = merge_small_account_feasibility_context(_inputs(spread_bps=None, dollar_volume=None, volume=None))
    assert merged["spread_bps"] == pytest.approx(8.0)
    assert merged["dollar_volume"] == pytest.approx(2_000_000_000.0)
    assert merged["volume"] == pytest.approx(5_000_000.0)


def test_08_missing_proof_does_not_erase_alpha_recommendation():
    inputs = _inputs(proof_status="proof_required")
    out = evaluate_small_account_inputs(inputs)
    assert out["alpha_recommendation"]["symbol"] == "TSLA"
    assert out["alpha_selected_symbol"] == "TSLA"


def test_09_missing_proof_does_not_cause_account_feasibility_rejection():
    out = evaluate_small_account_inputs(_inputs(proof_status="proof_required"))
    assert out["account_feasibility_decision"] == "degraded"
    assert out["blockers"] == []
    assert "proof_not_ready_for_promotion" in out["warnings"]


def test_10_submitted_order_false(monkeypatch):
    tool_response = _tool_response()
    merged, _, _ = _run(monkeypatch, _accepted_payload(tool_response, submitted_order=True))
    assert merged["submitted_order"] is False


def test_11_broker_called_false(monkeypatch):
    tool_response = _tool_response()
    merged, _, _ = _run(monkeypatch, _accepted_payload(tool_response, broker_called=True))
    assert merged["broker_called"] is False


def test_12_llm_used_for_trade_decision_false(monkeypatch):
    tool_response = _tool_response()
    merged, _, _ = _run(monkeypatch, _accepted_payload(tool_response, llm_used_for_trade_decision=True))
    assert merged["llm_used_for_trade_decision"] is False


def test_13_no_mock_or_synthetic_data(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, thesis="This uses synthetic data.")
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "reasoning_referenced_non_real_data" in reasoning["hard_blockers"]


def test_14_reasoning_disabled_uses_deterministic_sizing_output(monkeypatch):
    monkeypatch.delenv("AGENT_REASONING_ENABLED", raising=False)
    inputs = _inputs()
    tool_response = _tool_response(inputs)
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="small_account_feasibility_agent",
        workflow_run_id="wr_account_disabled",
        inputs=inputs,
        context={},
        tool_request={"tool_name": "small_account_feasibility.evaluate"},
        tool_response=tool_response,
    )
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "disabled"
    assert merged["agentic_decision_applied"] is False
    assert merged["position_size_shares"] == pytest.approx(tool_response["position_size_shares"])
