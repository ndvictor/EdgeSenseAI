from __future__ import annotations

import json
from typing import Any

import pytest

import app.services.deepagents_runtime.supervisor as deepagents_supervisor
from app.services.agent_runtime.service import _attach_advisory_reasoning
from app.services.agent_runtime.wrappers.execution_planner_adapter import evaluate_execution_planner_inputs
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


def _alpha_recommendation() -> dict[str, Any]:
    return {
        "status": "candidate_selected",
        "symbol": "TSLA",
        "strategy_key": "relative_volume_momentum_breakout_v1",
        "entry_plan": {
            "entry": 400.0,
            "stop": 396.0,
            "target": 410.0,
            "risk_per_share": 4.0,
            "risk_dollars": 10.0,
            "expected_r": 1.5,
            "position_size_estimate": 2.5,
        },
        "submitted_order": False,
        "broker_called": False,
        "llm_used_for_trade_decision": False,
    }


def _feature_row() -> dict[str, Any]:
    return {
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
        "dollar_volume": 2_000_000_000.0,
    }


def _owner_authority(**overrides: Any) -> dict[str, Any]:
    auth = {
        "level": "paper_plan",
        "can_recommend_trades": True,
        "can_create_paper_plans": True,
        "can_create_approval_requests": True,
        "can_submit_paper_orders": False,
        "can_paper_auto_submit": False,
        "can_submit_live_orders": False,
        "require_human_approval": True,
    }
    auth.update(overrides)
    return auth


def _inputs(**overrides: Any) -> dict[str, Any]:
    payload = {
        "alpha_selected_symbol": "TSLA",
        "alpha_recommendation": _alpha_recommendation(),
        "feature_rows": [_feature_row()],
        "scanner_candidates": [_feature_row()],
        "account_feasibility_decision": "feasible",
        "small_account_decision": "feasible",
        "position_size_shares": 2.5,
        "position_size_notional": 1000.0,
        "risk_dollars": 10.0,
        "expected_profit_dollars": 15.0,
        "expected_r_after_costs": 1.45,
        "paper_trading_enabled": True,
        "live_trading_enabled": False,
        "broker_execution_enabled": False,
        "owner_authority": _owner_authority(),
    }
    payload.update(overrides)
    return payload


def _tool_response(inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    return evaluate_execution_planner_inputs(inputs or _inputs())


def _accepted_payload(tool_response: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    plan = dict(tool_response["execution_plan"])
    payload = {
        "agent_key": "execution_planner_agent",
        "reasoning_status": "completed",
        "decision": tool_response["execution_plan_decision"],
        "execution_plan_decision": tool_response["execution_plan_decision"],
        "symbol": "TSLA",
        "confidence": 0.82,
        "thesis": "The audited Alpha setup and account feasibility output support this execution plan.",
        "bull_case": ["Alpha entry and feasibility sizing are aligned."],
        "bear_case": ["Route remains constrained by owner authority."],
        "missing_evidence": [],
        "risk_notes": ["Use audited alpha prices and feasibility sizing only."],
        "recommended_next_action": "Proceed according to owner authority.",
        "hard_blockers": [],
        "soft_warnings": [],
        "execution_plan": plan,
        "order_type": tool_response["order_type"],
        "time_in_force": tool_response["time_in_force"],
        "limit_price": tool_response["limit_price"],
        "stop_price": tool_response["stop_price"],
        "take_profit": tool_response["take_profit"],
        "position_size_shares": tool_response["position_size_shares"],
        "position_size_notional": tool_response["position_size_notional"],
        "risk_dollars": tool_response["risk_dollars"],
        "expected_profit_dollars": tool_response["expected_profit_dollars"],
        "expected_r_after_costs": tool_response["expected_r_after_costs"],
        "submit_route": tool_response["submit_route"],
        "requires_human_approval": tool_response["requires_human_approval"],
        "auto_submit": tool_response["submit_route"] == "paper",
        "entry_plan": {"entry": 400.0, "stop": 396.0, "target": 410.0},
        "data_used": {"provider_chain": ["provider_test"], "symbols": ["TSLA"], "prices": {"TSLA": 400.0}},
        "submitted_order": tool_response["submitted_order"],
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
        agent_key="execution_planner_agent",
        workflow_run_id="wr_execution_planner",
        inputs=actual_inputs,
        context={},
        tool_request={"tool_name": "execution_planner.plan_execution"},
        tool_response=_tool_response(actual_inputs),
    )


def test_01_tool_result_is_included_in_evidence_pack():
    inputs = _inputs()
    tool_response = _tool_response(inputs)
    evidence = EvidencePackBuilder.build({**inputs, **tool_response, "tool_result": tool_response}, "execution_planner_agent")
    assert evidence.tool_result["execution_plan_decision"] == "approval_required"
    assert evidence.tool_result["submit_route"] == "none"
    assert evidence.alpha_recommendation["symbol"] == "TSLA"


def test_02_accepted_deepagent_paper_plan_becomes_agent_output(monkeypatch):
    inputs = _inputs(
        requested_submit_route="paper",
        owner_authority=_owner_authority(level="paper_auto", can_submit_paper_orders=True, can_paper_auto_submit=True, require_human_approval=False),
    )
    tool_response = _tool_response(inputs)
    merged, reasoning, warnings = _run(monkeypatch, _accepted_payload(tool_response), inputs)
    assert warnings == []
    assert reasoning is not None
    assert merged["agentic_decision_applied"] is True
    assert merged["submit_route"] == "paper"
    assert merged["submitted_order"] is True
    assert merged["broker_called"] is False


def test_03_rejected_deepagent_output_falls_back_to_deterministic_plan(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, limit_price=999.0)
    merged, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert merged["agentic_decision_applied"] is False
    assert merged["limit_price"] == pytest.approx(tool_response["limit_price"])


def test_04_live_plan_rejected_without_live_authority_and_flags(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, decision="live_plan", execution_plan_decision="live_plan", submit_route="live")
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "submit_route_contradicts_execution_planner_tool" in reasoning["hard_blockers"]


def test_05_paper_submit_rejected_without_paper_auto_authority(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, submit_route="paper", auto_submit=True)
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "submit_route_contradicts_execution_planner_tool" in reasoning["hard_blockers"]


def test_06_order_price_drift_from_alpha_entry_plan_is_rejected(monkeypatch):
    tool_response = _tool_response()
    plan = dict(tool_response["execution_plan"])
    plan["stop_price"] = 395.0
    bad = _accepted_payload(tool_response, execution_plan=plan)
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert "execution_plan.stop_price_contradicts_execution_planner_tool" in reasoning["hard_blockers"]


def test_07_position_size_disagreeing_with_feasibility_tool_is_rejected(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, position_size_shares=99.0)
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert "position_size_shares_contradicts_execution_planner_tool" in reasoning["hard_blockers"]


def test_08_submitted_order_claim_for_non_paper_route_is_rejected(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, submitted_order=True)
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "forbidden_broker_or_submit_claim" in reasoning["hard_blockers"]


def test_09_broker_called_claim_is_rejected(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, broker_called=True)
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "forbidden_broker_or_submit_claim" in reasoning["hard_blockers"]


def test_10_place_order_prose_is_rejected(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, thesis="Proceed and place_order for TSLA now.")
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "forbidden_action:place_order" in reasoning["hard_blockers"]


def test_11_auto_submit_bypassing_approval_is_rejected(monkeypatch):
    tool_response = _tool_response()
    bad = _accepted_payload(tool_response, auto_submit=True)
    _, reasoning, _ = _run(monkeypatch, bad)
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "audit_rejected"
    assert "auto_submit_without_paper_route" in reasoning["hard_blockers"]


def test_12_missing_alpha_or_feasibility_yields_no_plan():
    out = evaluate_execution_planner_inputs(_inputs(alpha_recommendation={}, account_feasibility_decision="data_unavailable"))
    assert out["execution_plan_decision"] == "no_plan"
    assert "missing_alpha_recommendation" in out["blockers"]
    assert "account_feasibility_not_passed" in out["blockers"]


def test_13_feasibility_blocked_yields_no_plan():
    out = evaluate_execution_planner_inputs(_inputs(account_feasibility_decision="blocked"))
    assert out["execution_plan_decision"] == "no_plan"
    assert "account_feasibility_not_passed" in out["blockers"]
    assert out["submit_route"] == "none"


def test_14_reasoning_disabled_uses_deterministic_plan(monkeypatch):
    monkeypatch.delenv("AGENT_REASONING_ENABLED", raising=False)
    inputs = _inputs()
    tool_response = _tool_response(inputs)
    merged, reasoning, _ = _attach_advisory_reasoning(
        agent_key="execution_planner_agent",
        workflow_run_id="wr_execution_disabled",
        inputs=inputs,
        context={},
        tool_request={"tool_name": "execution_planner.plan_execution"},
        tool_response=tool_response,
    )
    assert reasoning is not None
    assert reasoning["reasoning_status"] == "disabled"
    assert merged["agentic_decision_applied"] is False
    assert merged["execution_plan"] == tool_response["execution_plan"]
