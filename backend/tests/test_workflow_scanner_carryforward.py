from __future__ import annotations

from typing import Any

import pytest

import app.services.workflow_orchestrator.service as orchestrator_service
from app.services.agent_runtime.wrappers.alpha_engine_adapter import run_alpha_engine_selection
from app.services.agent_runtime.wrappers.glue_agents import run_glue_agent
from app.services.agent_runtime.wrappers.safety import SafetyResult
from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator.scanner_carryforward import seed_workflow_state_from_scanner_diagnostics
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def _scanner_dx_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "symbol": "ROWX",
        "last_price": 427.7,
        "volume": 1_136_306.0,
        "dollar_volume": 485_998_076.2,
        "spread_bps": 12.0,
        "data_quality": "real",
        "feature_quality": "partial",
        "hard_blockers": [],
        "soft_warnings": ["relative_volume_unavailable"],
        "source": "manual_request",
        "candidate_source": "manual_request",
    }
    base.update(overrides)
    return base


def _fake_scanner_diagnostics(**row_overrides: Any) -> dict[str, Any]:
    row = _scanner_dx_row(**row_overrides)
    return {
        "scanner_run_id": "scanner-test-1",
        "provider_name": "alpaca",
        "provider_priority": ["alpaca", "polygon"],
        "provider_configured": True,
        "alpaca_configured": True,
        "alpaca_feed": "iex",
        "feed": "iex",
        "source": "manual_request",
        "candidate_source": "manual_request",
        "status": "candidate_selected",
        "selected_candidates": [row],
        "rejected_candidates": [],
        "total_symbols_seen": 1,
        "total_symbols_passed": 1,
        "rejection_counts": {},
        "submitted_order": False,
        "broker_called": False,
        "llm_used": False,
    }


def test_seed_state_maps_scanner_candidate_fields():
    state = WorkflowCarryForwardState(symbols=["ROWX"], workflow_request_symbols=["ROWX"], source="manual")
    dx = _fake_scanner_diagnostics()
    seed_workflow_state_from_scanner_diagnostics(state, dx, {"source": "workflow_manual_request"}, "manual")

    assert state.latest_price == 427.7
    assert state.spread_bps == pytest.approx(12.0)
    assert state.avg_dollar_volume == pytest.approx(485_998_076.2)
    assert state.feature_row_count == 1
    assert len(state.scanner_candidates) == 1
    assert state.candidate_source == "manual_request"
    assert state.selected_symbol == "ROWX"
    assert state.usable_symbols == ["ROWX"]
    assert state.submitted_order is False
    assert state.broker_called is False


def test_workflow_carryforward_from_scanner(monkeypatch):
    dx = _fake_scanner_diagnostics()

    def _fake_build_scanner_diagnostics(**kwargs: Any) -> dict[str, Any]:
        return dict(dx)

    monkeypatch.setattr(orchestrator_service, "build_scanner_diagnostics", _fake_build_scanner_diagnostics)

    run = orchestrator_service.run_workflow(
        OrchestratorRunRequest(
            symbols=["ROWX"],
            dry_run=True,
            allow_submit=False,
            source="alpaca",
            stop_at_stage=12,
            strategy_key="stock_day_trading",
        )
    )

    assert run.allow_submit is False
    assert run.submitted_order is False
    assert run.broker_called is False
    assert run.llm_used is False

    assert run.feature_row_count >= 1
    assert run.latest_snapshot_count >= 1

    wl = next((s for s in run.stage_timeline if s.get("agent_key") == "watchlist_builder_agent"), None)
    assert wl is not None
    snap = wl.get("pipeline_inputs_snapshot") or {}
    assert snap.get("candidate_source") != "universe_selection"
    assert snap.get("latest_price") == 427.7
    assert snap.get("spread_bps") == pytest.approx(12.0)
    assert snap.get("feature_row_count", 0) >= 1

    assert run.alpha_status in {"candidate_selected", "watchlist_only", "needs_more_evidence"}
    assert run.alpha_status != "data_unavailable"
    ab = list((run.alpha_recommendation or {}).get("blockers") or [])
    assert "last_price_missing" not in ab
    assert "volume_missing" not in ab
    assert "spread_bps_missing" not in ab

    sa = next((s for s in run.stage_timeline if s.get("agent_key") == "small_account_feasibility_agent"), None)
    assert sa is not None
    sa_snap = sa.get("pipeline_inputs_snapshot") or {}
    assert "missing_entry" not in (sa_snap.get("small_account_blockers") or [])


def test_watchlist_prefill_preserves_manual_request_source():
    row = _scanner_dx_row()
    inputs = {
        "asset_class": "stock",
        "horizon": "day_trading",
        "workflow_request_symbols": ["ROWX"],
        "scanner_candidates": [row],
        "candidate_source": "manual_request",
        "symbols": ["ROWX"],
        "usable_symbols": ["ROWX"],
        "source": "alpaca",
        "max_symbols": 10,
    }
    out = run_glue_agent(
        agent_key="watchlist_builder_agent",
        inputs=inputs,
        context={"source": "workflow_orchestrator"},
        safety=SafetyResult(sanitized_inputs=inputs, blockers=[], warnings=[]),
    )
    tr = (out.get("tool_response") or {})
    assert tr.get("candidate_source") == "manual_request"
    assert out.get("tool_name") == "watchlist_builder.scanner_runtime_prefill"
    assert "universe_selection" not in str(out).lower()


def test_alpha_partial_scanner_row_not_data_unavailable():
    row = {
        "symbol": "ROWX",
        "last_price": 427.7,
        "volume": 1_136_306.0,
        "spread_bps": 900.0,
        "avg_volume": None,
        "relative_volume": None,
        "dollar_volume": 485_998_076.2,
        "data_quality": "real",
        "source": "manual_request",
        "candidate_source": "manual_request",
        "hard_blockers": [],
    }
    out = run_alpha_engine_selection(
        {"scanner_candidates": [row], "feature_rows": [row], "watchlist": [row], "account_equity": 1000.0},
        {"workflow_run_id": "wr_carry"},
    )
    assert out["alpha_status"] in {"candidate_selected", "watchlist_only", "needs_more_evidence"}
    assert out["alpha_status"] != "data_unavailable"
    assert "last_price_missing" not in out.get("alpha_blockers", [])
    assert "volume_missing" not in out.get("alpha_blockers", [])
    assert "spread_bps_missing" not in out.get("alpha_blockers", [])


def test_small_account_uses_latest_price_from_inputs():
    from app.services.agent_runtime.wrappers.small_account_feasibility_adapter import evaluate_small_account_inputs

    out = evaluate_small_account_inputs(
        {
            "account_equity": 1000.0,
            "selected_symbol": "ROWX",
            "symbols": ["ROWX"],
            "usable_symbols": ["ROWX"],
            "latest_price": 427.7,
            "spread_bps": 12.0,
            "avg_dollar_volume": 400_000_000.0,
            "planned_risk_dollars": 5.0,
            "max_risk_per_trade_percent": 0.5,
            "max_daily_loss_percent": 1.5,
        }
    )
    assert "missing_entry" not in out.get("blockers", [])
