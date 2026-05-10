from __future__ import annotations

from typing import Any

from app.services.agent_runtime.wrappers.glue_agents import run_glue_agent
from app.services.agent_runtime.wrappers.safety import SafetyResult
from app.services.agent_runtime.wrappers.small_account_feasibility_adapter import merge_small_account_feasibility_context
from app.services.workflow_orchestrator.pipeline_carryforward import _enrich_alpha_recommendation_with_row
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def _safe(inputs: dict[str, Any]) -> SafetyResult:
    return SafetyResult(sanitized_inputs=inputs, blockers=[], warnings=[])


def test_glue_carries_alpha_entry_plan_and_liquidity_fields():
    alpha_rec = {
        "symbol": "ABC",
        "strategy_key": "relative_volume_momentum_breakout_v1",
        "setup_type": "orb",
        "final_score": 82.0,
        "confidence": 74.0,
        "predicted_return_r": 0.35,
        "predicted_expected_value_r": 0.22,
        "predicted_win_probability": 0.55,
        "entry_plan": {
            "entry": 150.0,
            "stop": 148.0,
            "target": 155.0,
            "risk_per_share": 2.0,
            "expected_r": 1.1,
        },
    }
    row = {
        "symbol": "ABC",
        "last_price": 150.0,
        "spread_bps": 10.0,
        "volume": 8_000_000.0,
        "dollar_volume": 1_200_000_000.0,
        "session_state": "regular",
        "data_quality": "real",
        "provider_name": "alpaca",
    }
    inputs: dict[str, Any] = {
        "mode": "paper_first",
        "account_equity": 100_000.0,
        "buying_power": 100_000.0,
        "selected_symbol": "ABC",
        "alpha_recommendation": alpha_rec,
        "feature_rows": [row],
        "usable_symbols": ["ABC"],
        "symbols": ["ABC"],
        "planned_risk_dollars": 200.0,
        "execution_mode": "plan_only",
        "fractional_trading_enabled": True,
    }
    merged = merge_small_account_feasibility_context(inputs)
    assert merged["entry"] == 150.0
    assert merged["stop"] == 148.0
    assert merged["spread_bps"] == 10.0
    assert merged["volume"] == 8_000_000.0
    assert merged["dollar_volume"] == 1_200_000_000.0
    assert merged["predicted_expected_value_r"] == 0.22

    out = run_glue_agent(
        agent_key="small_account_feasibility_agent",
        inputs=inputs,
        context={"workflow_run_id": "wr_glue_feas"},
        safety=_safe(inputs),
    )
    tr = out.get("tool_response") or {}
    assert tr.get("account_feasibility_decision") in {"feasible", "degraded", "blocked"}
    assert tr.get("broker_called") is False
    assert tr.get("submitted_order") is False
    assert tr.get("llm_used") is False


def test_missing_proof_does_not_erase_alpha_recommendation_or_block_feasibility():
    alpha_rec = {
        "symbol": "ABC",
        "strategy_key": "relative_volume_momentum_breakout_v1",
        "setup_type": "orb",
        "entry_plan": {"entry": 50.0, "stop": 49.0, "target": 52.0, "expected_r": 1.0},
        "predicted_expected_value_r": 0.15,
        "predicted_win_probability": 0.5,
        "final_score": 80.0,
        "confidence": 72.0,
    }
    row = {
        "symbol": "ABC",
        "last_price": 50.0,
        "spread_bps": 6.0,
        "volume": 20_000_000.0,
        "dollar_volume": 1_000_000_000.0,
    }
    inputs: dict[str, Any] = {
        "mode": "paper_first",
        "account_equity": 50_000.0,
        "buying_power": 50_000.0,
        "alpha_recommendation": dict(alpha_rec),
        "feature_rows": [row],
        "usable_symbols": ["ABC"],
        "selected_symbol": "ABC",
        "proof_status": "proof_required",
        "planned_risk_dollars": 100.0,
        "execution_mode": "plan_only",
    }
    merged = merge_small_account_feasibility_context(inputs)
    assert merged["alpha_recommendation"]["symbol"] == "ABC"
    out = run_glue_agent(
        agent_key="small_account_feasibility_agent",
        inputs=inputs,
        context={"workflow_run_id": "wr_proof"},
        safety=_safe(inputs),
    )
    tr = out.get("tool_response") or {}
    assert "proof_not_ready_for_promotion" in (tr.get("warnings") or [])
    assert "proof_not_ready_for_promotion" not in (tr.get("blockers") or [])


def test_pipeline_enrich_merges_spread_and_volume_into_alpha_recommendation():
    state = WorkflowCarryForwardState(
        alpha_selected_symbol="ZZZ",
        candidate_source="manual_request",
        provider_name="alpaca",
    )
    state.alpha_recommendation = {
        "symbol": "ZZZ",
        "strategy_key": "relative_volume_momentum_breakout_v1",
        "entry_plan": {"entry": 10.0, "stop": 9.5, "target": 11.0, "expected_r": 1.0},
    }
    state.feature_rows = [
        {
            "symbol": "ZZZ",
            "last_price": 10.0,
            "spread_bps": 7.0,
            "volume": 1_000_000.0,
            "dollar_volume": 10_000_000.0,
            "session_state": "regular",
            "data_quality": "real",
        }
    ]
    _enrich_alpha_recommendation_with_row(state)
    rec = state.alpha_recommendation
    assert rec.get("spread_bps") == 7.0
    assert rec.get("volume") == 1_000_000.0
    assert rec.get("dollar_volume") == 10_000_000.0
