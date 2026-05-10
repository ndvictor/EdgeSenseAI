from __future__ import annotations

from fastapi.testclient import TestClient

import app.services.agent_runtime.wrappers.glue_agents as glue_agents
import app.services.workflow_orchestrator.service as orchestrator_service
from app.main import app


client = TestClient(app)


def _allow_governance(monkeypatch):
    monkeypatch.setattr(
        orchestrator_service,
        "check_governance",
        lambda _req: type(
            "Gov",
            (),
            {
                "decision": "allowed",
                "blockers": [],
                "warnings": [],
                "next_action": "allowed",
                "model_dump": lambda self: {"decision": "allowed", "blockers": [], "warnings": []},
            },
        )(),
    )


def _post_empty_symbols(stop_at_stage: int = 6):
    return client.post(
        "/api/workflow-orchestrator/run",
        json={
            "asset_class": "stock",
            "horizon": "day_trading",
            "mode": "paper_first",
            "source": "runtime",
            "symbols": [],
            "max_candidates": 5,
            "stop_at_stage": stop_at_stage,
            "dry_run": True,
            "allow_submit": False,
            "require_human_approval": True,
            "metadata": {"allow_synthetic_market_data": False},
        },
    )


def test_empty_symbols_uses_scanner_discovery_candidates(monkeypatch):
    _allow_governance(monkeypatch)
    calls: list[dict] = []

    def fake_watchlist(**kwargs):
        calls.append(kwargs)
        return {
            "symbols": ["MSFT"],
            "ranked_candidates": [{"symbol": "MSFT", "source_type": "scanner", "provider": "yfinance"}],
            "selected_candidate": "MSFT",
            "candidate_source": "scanner/provider",
            "raw_candidate_count": 1,
            "filtered_candidate_count": 1,
            "blockers": [],
            "warnings": [],
            "recommendation": {"status": "candidate_selected", "symbol": "MSFT", "mock_data_used": False, "synthetic_data_used": False},
            "next_action": "Proceed to strategy selection.",
        }

    monkeypatch.setattr(glue_agents, "build_watchlist", fake_watchlist)

    response = _post_empty_symbols()

    assert response.status_code == 200
    run = response.json()["run"]
    assert calls
    assert calls[0]["seed_symbols"] == []
    assert "no_symbols_selected" not in run["blockers"]
    assert run["recommendation"]["status"] == "candidate_selected"
    assert run["recommendation"]["symbol"] == "MSFT"
    assert run["recommendation"]["mock_data_used"] is False
    assert run["recommendation"]["synthetic_data_used"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert "AMD" not in str(run)


def test_empty_symbols_no_candidates_returns_no_qualified_setup(monkeypatch):
    _allow_governance(monkeypatch)
    monkeypatch.setattr(
        glue_agents,
        "build_watchlist",
        lambda **_kwargs: {
            "decision": "no_trade",
            "symbols": [],
            "ranked_candidates": [],
            "selected_candidate": None,
            "candidate_source": "none",
            "raw_candidate_count": 0,
            "filtered_candidate_count": 0,
            "blockers": ["no_scanner_candidates_passed_filters"],
            "warnings": [],
            "recommendation": {"status": "no_qualified_setup", "symbol": None, "mock_data_used": False, "synthetic_data_used": False},
            "next_action": "No provider-backed scanner/candidate symbols are available.",
        },
    )

    response = _post_empty_symbols()

    assert response.status_code == 200
    run = response.json()["run"]
    assert "no_symbols_selected" not in run["blockers"]
    assert run["recommendation"]["status"] == "no_qualified_setup"
    assert run["recommendation"]["symbol"] is None
    assert run["recommendation"]["mock_data_used"] is False
    assert run["recommendation"]["synthetic_data_used"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert "AMD" not in str(run)


def test_empty_symbols_provider_unavailable_returns_data_unavailable(monkeypatch):
    _allow_governance(monkeypatch)
    monkeypatch.setattr(
        glue_agents,
        "build_watchlist",
        lambda **_kwargs: {
            "decision": "blocked",
            "symbols": [],
            "ranked_candidates": [],
            "selected_candidate": None,
            "candidate_source": "scanner/provider",
            "raw_candidate_count": 1,
            "filtered_candidate_count": 0,
            "blockers": ["scanner_or_provider_unavailable"],
            "warnings": ["provider unavailable"],
            "recommendation": {"status": "data_unavailable", "symbol": None, "mock_data_used": False, "synthetic_data_used": False},
            "next_action": "Provider-backed discovery failed.",
        },
    )

    response = _post_empty_symbols()

    assert response.status_code == 200
    run = response.json()["run"]
    assert "no_symbols_selected" not in run["blockers"]
    assert run["recommendation"]["status"] == "data_unavailable"
    assert run["recommendation"]["mock_data_used"] is False
    assert run["recommendation"]["synthetic_data_used"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert "AMD" not in str(run)
