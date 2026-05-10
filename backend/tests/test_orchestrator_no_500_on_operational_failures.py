from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
import app.services.agent_runtime.wrappers.data_readiness_adapter as data_readiness_adapter
import app.services.agent_runtime.wrappers.glue_agents as glue_agents
import app.services.universe_selection_service as universe_selection_service


client = TestClient(app)


def _fake_data_ready(symbol: str):
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(id=f"fs_{symbol}", ticker=symbol, data_quality="pass")
    snap = SimpleNamespace(
        timestamp=now,
        price=100.0,
        volume=100000,
        change_percent=0.5,
        relative_volume=1.0,
        spread_percent=0.02,
        provider="yfinance",
        is_mock=False,
        data_quality="real",
    )
    report = SimpleNamespace(quality_status="pass", freshness_status="fresh", blockers=[], warnings=[])
    return SimpleNamespace(
        row=row,
        normalized_snapshot=snap,
        quality_report=report,
        storage_mode="in_memory",
        warnings=[],
        provider_statuses=[{"provider": "yfinance", "data_quality": "real", "error": None}],
    )


def test_orchestrator_returns_structured_blocked_when_freshness_unavailable(monkeypatch):
    monkeypatch.setattr(data_readiness_adapter, "run_feature_store_pipeline", lambda req: _fake_data_ready(req.symbol))
    monkeypatch.setattr(data_readiness_adapter, "get_feature_row_persistence_status", lambda _row_id: {"persisted": False, "data_source": "in_memory_fallback"})
    monkeypatch.setattr(
        glue_agents,
        "scan_market_condition",
        lambda symbols, source="auto": {
            "decision": "degraded",
            "market_context": {"should_trigger_workflow": False, "regime": "unknown"},
            "blockers": [],
            "warnings": ["market condition unavailable"],
            "next_agent": "watchlist_builder_agent",
        },
    )

    def failed_freshness(_request):
        from app.services.data_freshness_gate_service import DataFreshnessCheckResponse, DataFreshnessSummary

        return DataFreshnessCheckResponse(
            run_id="fresh-test",
            status="fail",
            source="auto",
            checked_at=datetime.now(timezone.utc).isoformat(),
            results=[],
            blockers=["provider_unavailable"],
            warnings=["freshness_unavailable"],
            summary=DataFreshnessSummary(total_checked=1, blocked_count=1, unavailable_count=1),
        )

    monkeypatch.setattr(universe_selection_service, "run_data_freshness_check", failed_freshness)

    response = client.post(
        "/api/workflow-orchestrator/run",
        json={
            "asset_class": "stock",
            "horizon": "day_trading",
            "mode": "paper_first",
            "source": "runtime",
            "symbols": ["MSFT"],
            "max_candidates": 5,
            "stop_at_stage": 10,
            "dry_run": True,
            "require_human_approval": True,
            "allow_submit": False,
            "metadata": {
                "allow_synthetic_market_data": False,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    run = payload["run"]
    assert run["status"] == "blocked"
    assert payload["submitted_order"] is False
    assert payload["broker_called"] is False
    assert payload["llm_used"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert run["recommendation"]["status"] in {"data_unavailable", "no_qualified_setup"}
    assert run["recommendation"]["mock_data_used"] is False
    assert run["recommendation"]["synthetic_data_used"] is False
    assert run["recommendation"]["symbol"] is None


def test_runtime_empty_symbols_do_not_fall_back_to_amd():
    response = client.post(
        "/api/workflow-orchestrator/run",
        json={
            "asset_class": "stock",
            "horizon": "day_trading",
            "mode": "paper_first",
            "source": "runtime",
            "symbols": [],
            "stop_at_stage": 4,
            "dry_run": True,
            "require_human_approval": True,
            "allow_submit": False,
        },
    )

    assert response.status_code == 200
    run = response.json()["run"]
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert run["recommendation"]["mock_data_used"] is False
    assert run["recommendation"]["synthetic_data_used"] is False
    assert "AMD" not in str(run)
