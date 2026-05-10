from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_runtime.wrappers.alpha_engine_adapter import run_alpha_engine_selection
from app.services.agent_runtime.wrappers.glue_agents import run_glue_agent
from app.services.agent_runtime.wrappers.safety import SafetyResult
import app.services.agent_runtime.wrappers.glue_agents as glue_agents
import app.services.workflow_orchestrator.service as orchestrator_service


client = TestClient(app)


def _real_feature_row(**overrides: Any) -> dict[str, Any]:
    data = {
        "symbol": "ROWX",
        "last_price": 10.0,
        "volume": 5_000_000,
        "avg_volume": 1_000_000,
        "relative_volume": 5.0,
        "day_change_pct": 8.0,
        "spread_bps": 8.0,
        "vwap": 9.7,
        "price_above_vwap": True,
        "premarket_high": 10.2,
        "trend_score": 80.0,
        "liquidity_score": 85.0,
        "session_state": "regular",
        "source": "provider",
        "provider_name": "provider_test",
    }
    data.update(overrides)
    return data


def _safe(inputs: dict[str, Any]) -> SafetyResult:
    return SafetyResult(sanitized_inputs=inputs, blockers=[], warnings=[])


def test_no_candidate_rows_returns_alpha_status_no_qualified_setup():
    out = run_alpha_engine_selection({}, {"workflow_run_id": "wr_alpha_empty"})

    assert out["alpha_status"] == "no_qualified_setup"
    assert out["recommendation"]["status"] == "no_qualified_setup"
    assert out["recommendation"]["symbol"] is None


def test_real_feature_row_with_high_relative_volume_returns_candidate_selected():
    out = run_alpha_engine_selection({"feature_rows": [_real_feature_row()]}, {"workflow_run_id": "wr_alpha_real"})

    assert out["alpha_status"] == "candidate_selected"
    assert out["alpha_selected_symbol"] == "ROWX"
    assert out["alpha_strategy_key"] == "relative_volume_momentum_breakout_v1"


def test_selected_symbol_comes_from_feature_row_not_hardcoded_fallback():
    out = run_alpha_engine_selection({"feature_rows": [_real_feature_row(symbol="ROWY")]}, {"workflow_run_id": "wr_alpha_symbol"})

    assert out["alpha_status"] == "candidate_selected"
    assert out["alpha_selected_symbol"] == "ROWY"


def test_synthetic_feature_row_is_rejected():
    out = run_alpha_engine_selection({"feature_rows": [_real_feature_row(synthetic=True)]}, {"workflow_run_id": "wr_alpha_synth"})

    assert out["alpha_status"] != "candidate_selected"
    assert out["alpha_selected_symbol"] is None


def test_mock_feature_row_is_rejected():
    out = run_alpha_engine_selection({"feature_rows": [_real_feature_row(mock=True)]}, {"workflow_run_id": "wr_alpha_mock"})

    assert out["alpha_status"] != "candidate_selected"
    assert out["alpha_selected_symbol"] is None


def test_strategy_selection_agent_respects_alpha_strategy_key():
    inputs = {
        "horizon": "day_trading",
        "alpha_status": "candidate_selected",
        "alpha_selected_symbol": "ROWX",
        "alpha_strategy_key": "relative_volume_momentum_breakout_v1",
        "alpha_warnings": [],
    }
    out = run_glue_agent(
        agent_key="strategy_selection_agent",
        inputs=inputs,
        context={"workflow_run_id": "wr_alpha_strategy"},
        safety=_safe(inputs),
    )

    assert out["tool_response"]["selected_strategy_key"] == "relative_volume_momentum_breakout_v1"
    assert out["tool_response"]["selected_symbol"] == "ROWX"


def test_workflow_response_includes_alpha_recommendation(monkeypatch):
    monkeypatch.setattr(orchestrator_service, "_db_session", lambda: None)
    monkeypatch.setattr(orchestrator_service, "write_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(orchestrator_service, "production_database_blocker", lambda: None)
    monkeypatch.setattr(
        orchestrator_service,
        "check_governance",
        lambda *_args, **_kwargs: SimpleNamespace(decision="allowed", blockers=[], warnings=[], next_action="ok", model_dump=lambda: {}),
    )
    monkeypatch.setattr(
        orchestrator_service,
        "default_stage_plan",
        lambda **_kwargs: ["watchlist_builder_agent", "alpha_engine_agent", "strategy_selection_agent"],
    )
    monkeypatch.setattr(orchestrator_service, "orchestrator_pipeline_agent_count", lambda: 3)
    monkeypatch.setattr(
        glue_agents,
        "build_watchlist",
        lambda **_kwargs: {
            "symbols": ["ROWX"],
            "selected_candidate": "ROWX",
            "feature_rows": [_real_feature_row()],
            "blockers": [],
            "warnings": [],
        },
    )

    response = client.post(
        "/api/workflow-orchestrator/run",
        json={"dry_run": True, "allow_submit": False, "symbols": ["ROWX"], "source": "manual", "stop_at_stage": 3},
    )
    assert response.status_code == 200
    run = response.json()["run"]

    assert run["alpha_recommendation"]["status"] == "candidate_selected"
    assert run["alpha_status"] == "candidate_selected"
    assert run["recommendation"]["status"] == "candidate_selected"
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
