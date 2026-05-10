from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app
import app.services.real_scanner_diagnostics_service as diagnostics_service
import app.services.worker_output_store as worker_output_store
import app.workers.market_scanner_worker as scanner_worker


client = TestClient(app)


class _Provider:
    def __init__(self, configured: bool = True) -> None:
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured


class _MarketData:
    def __init__(self, snapshots: dict[str, dict[str, Any]], priority: list[str] | None = None) -> None:
        self.snapshots = {key.upper(): value for key, value in snapshots.items()}
        self.priority = priority or ["alpaca", "yfinance"]
        self.providers = {"alpaca": _Provider(True), "yfinance": _Provider(True), "polygon": _Provider(True)}

    def _priority_for_source(self, source: str | None = None) -> list[str]:
        requested = (source or "auto").lower().strip()
        if requested in {"alpaca", "yfinance", "polygon"}:
            return [requested]
        return list(self.priority)

    def get_market_snapshot(self, symbol: str, source: str | None = None) -> dict[str, Any]:
        return dict(
            self.snapshots.get(
                symbol.upper(),
                {
                    "symbol": symbol.upper(),
                    "provider": None,
                    "data_quality": "unavailable",
                    "price": None,
                    "volume": None,
                    "is_non_real": False,
                    "provider_statuses": [{"provider": "alpaca", "data_quality": "unavailable", "error": "not available"}],
                },
            )
        )


def _passing_snapshot(symbol: str = "ROWX", provider: str = "alpaca") -> dict[str, Any]:
    return {
        "symbol": symbol,
        "provider": provider,
        "data_quality": "real",
        "price": 12.0,
        "volume": 250_000,
        "average_volume": 100_000,
        "relative_volume": 2.5,
        "bid": 11.99,
        "ask": 12.01,
        "session_state": "regular",
        "is_non_real": False,
    }


def _install_market_data(monkeypatch, snapshots: dict[str, dict[str, Any]], priority: list[str] | None = None) -> _MarketData:
    market_data = _MarketData(snapshots, priority=priority)
    monkeypatch.setattr(diagnostics_service, "_MARKET_DATA", market_data)
    return market_data


def setup_function() -> None:
    worker_output_store.clear_worker_output_memory()


def teardown_function() -> None:
    worker_output_store.clear_worker_output_memory()


def test_scanner_diagnostics_exist_and_report_alpaca_feed(monkeypatch):
    _install_market_data(monkeypatch, {"ROWX": _passing_snapshot("ROWX", provider="alpaca")}, priority=["alpaca", "yfinance"])
    monkeypatch.setenv("ALPACA_MARKET_DATA_FEED", "iex")

    response = client.post("/api/scanner/run", json={"symbols": ["ROWX"], "max_candidates": 10, "data_source": "alpaca"})

    assert response.status_code == 200
    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["scanner_run_id"]
    assert diagnostics["provider_name"] == "alpaca"
    assert diagnostics["provider_priority"] == ["alpaca"]
    assert diagnostics["provider_configured"] is True
    assert diagnostics["feed"] == "iex"
    assert diagnostics["source"] == "manual_request"
    assert diagnostics["candidate_source"] == "manual_request"
    assert diagnostics["total_symbols_passed"] == 1

    latest = client.get("/api/worker-status/latest").json()
    assert latest["latest_scanner_diagnostics"]["scanner_run_id"] == diagnostics["scanner_run_id"]
    assert latest["provider_name"] == "alpaca"
    assert latest["provider_priority"] == ["alpaca"]
    assert latest["provider_configured"] is True
    assert latest["alpaca_configured"] is True
    assert latest["alpaca_feed"] == "iex"
    assert latest["latest_scanner_run_id"] == diagnostics["scanner_run_id"]
    assert latest["scanner_status"] == "candidate_selected"
    assert latest["candidate_source"] == "manual_request"
    assert latest["total_symbols_seen"] == 1
    assert latest["total_symbols_with_provider_data"] == 1
    assert latest["total_symbols_rejected"] == 0
    assert latest["total_symbols_passed"] == 1
    assert latest["rejection_counts"]["provider_unavailable"] == 0
    assert latest["no_qualified_setup_reason"] is None


def test_worker_without_dynamic_universe_reports_no_real_discovery_universe(monkeypatch):
    monkeypatch.setattr(scanner_worker, "require_production_data_policy", lambda: None)
    monkeypatch.setattr(scanner_worker, "list_candidates", lambda status=None: [])
    monkeypatch.setattr(scanner_worker, "get_latest_universe_selection", lambda: None)

    result = scanner_worker.run()

    assert result["recommendation_status"] == "no_qualified_setup"
    assert "no_real_discovery_universe_configured" in result["blockers"]
    assert result["scanner_diagnostics"]["reason"] == "no_real_discovery_universe_configured"
    assert result["scanner_diagnostics"]["total_symbols_seen"] == 0


def test_provider_unavailable_returns_data_unavailable(monkeypatch):
    _install_market_data(monkeypatch, {})

    response = client.post("/api/scanner/run", json={"symbols": ["ROWX"], "max_candidates": 10})

    assert response.status_code == 200
    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["status"] == "data_unavailable"
    assert diagnostics["reason"] == "data_unavailable"
    assert diagnostics["rejection_counts"]["provider_unavailable"] == 1


def test_missing_rvol_and_spread_are_rejected_with_reason_counts(monkeypatch):
    _install_market_data(
        monkeypatch,
        {
            "ROWX": {
                "symbol": "ROWX",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 12.0,
                "volume": 250_000,
                "is_non_real": False,
            }
        },
    )

    response = client.post("/api/scanner/run", json={"symbols": ["ROWX"], "max_candidates": 10})

    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["status"] == "no_qualified_setup"
    assert diagnostics["rejection_counts"]["missing_relative_volume"] == 1
    assert diagnostics["rejection_counts"]["missing_spread"] == 1
    assert diagnostics["total_symbols_rejected"] == 1


def test_passed_manual_candidate_persists_but_not_as_autonomous_scanner_candidate(monkeypatch):
    _install_market_data(monkeypatch, {"ROWX": _passing_snapshot("ROWX")})

    response = client.post("/api/scanner/run", json={"symbols": ["ROWX"], "max_candidates": 10})

    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["total_symbols_passed"] == 1
    latest = client.get("/api/worker-status/latest").json()["scanner_worker"]
    assert latest["scanner_candidates"][0]["source"] == "manual_request"
    assert latest["scanner_candidates"][0]["candidate_source"] == "manual_request"
    assert worker_output_store.get_latest_scanner_candidates() == []


def test_worker_passed_candidate_persists_as_scanner_source(monkeypatch):
    _install_market_data(monkeypatch, {"ROWX": _passing_snapshot("ROWX")})
    monkeypatch.setattr(scanner_worker, "require_production_data_policy", lambda: None)
    monkeypatch.setattr(scanner_worker, "_candidate_symbols", lambda limit: ["ROWX"])

    result = scanner_worker.run()

    assert result["recommendation_status"] == "candidate_selected"
    latest_candidates = worker_output_store.get_latest_scanner_candidates()
    assert latest_candidates[0]["source"] == "scanner"
    assert latest_candidates[0]["candidate_source"] == "scanner"


def test_scanner_proof_does_not_submit_or_call_model(monkeypatch):
    _install_market_data(monkeypatch, {"ROWX": _passing_snapshot("ROWX")})

    response = client.post("/api/scanner/run", json={"symbols": ["ROWX"], "max_candidates": 10})
    payload = response.json()

    assert payload["submitted_order"] is False
    assert payload["broker_called"] is False
    assert payload["llm_used"] is False
    assert payload["scanner_diagnostics"]["submitted_order"] is False
    assert payload["scanner_diagnostics"]["broker_called"] is False
    assert payload["scanner_diagnostics"]["llm_used"] is False
