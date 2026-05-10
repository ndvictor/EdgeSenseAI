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
        "fractionable": True,
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
    assert diagnostics["selected_count"] == 1
    assert diagnostics["watchlist_count"] == 0
    assert diagnostics["blocked_count"] == 0
    assert diagnostics["selected_candidates"][0]["candidate_status"] == "candidate_selected"

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


def test_high_priced_fractional_symbol_is_not_rejected_for_price(monkeypatch):
    _install_market_data(
        monkeypatch,
        {
            "BIGX": {
                **_passing_snapshot("BIGX"),
                "price": 1000.0,
                "volume": 250_000,
                "average_volume": 100_000,
                "relative_volume": 2.5,
                "bid": 999.9,
                "ask": 1000.1,
                "fractionable": True,
            }
        },
    )

    response = client.post("/api/scanner/run", json={"symbols": ["BIGX"], "max_candidates": 10, "data_source": "alpaca"})

    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["status"] == "candidate_selected"
    candidate = diagnostics["selected_candidates"][0]
    assert candidate["last_price"] == 1000.0
    assert candidate["estimated_quantity"] == 0.05
    assert candidate["fractional_required"] is True
    assert candidate["fractional_supported"] is True
    assert candidate["price_feasibility_status"] == "fractional_feasible"
    assert "price_out_of_range" not in candidate.get("hard_blockers", [])
    assert "price_out_of_range" not in diagnostics["rejection_counts"]


def test_missing_rvol_goes_to_enrichment_not_blocked(monkeypatch):
    _install_market_data(
        monkeypatch,
        {
            "ROWX": {
                "symbol": "ROWX",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 12.0,
                "volume": 250_000,
                "bid": 11.99,
                "ask": 12.01,
                "session_state": "regular",
                "is_non_real": False,
                "fractionable": True,
            }
        },
    )

    response = client.post("/api/scanner/run", json={"symbols": ["ROWX"], "max_candidates": 10})

    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["status"] == "no_qualified_setup"
    assert diagnostics["selected_count"] == 0
    assert diagnostics["watchlist_count"] == 1
    assert diagnostics["blocked_count"] == 0
    watch = diagnostics["watchlist_candidates"][0]
    assert watch["candidate_status"] == "needs_enrichment"
    assert "missing_relative_volume" in watch["soft_warnings"]
    assert "relative_volume" in watch["enrichment_needed"]
    assert "avg_volume" in watch["enrichment_needed"]
    assert watch["next_action"] == "send_to_feature_enrichment"
    assert diagnostics["warning_counts"]["missing_relative_volume"] == 1
    assert diagnostics["enrichment_counts"]["relative_volume"] == 1


def test_provider_unavailable_returns_data_unavailable(monkeypatch):
    _install_market_data(monkeypatch, {})

    response = client.post("/api/scanner/run", json={"symbols": ["ROWX"], "max_candidates": 10})

    assert response.status_code == 200
    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["status"] == "data_unavailable"
    assert diagnostics["reason"] == "data_unavailable"
    assert diagnostics["rejection_counts"]["provider_unavailable"] == 1
    assert diagnostics["blocked_count"] == 1


def test_missing_price_is_still_blocked(monkeypatch):
    _install_market_data(
        monkeypatch,
        {
            "BADX": {
                "symbol": "BADX",
                "provider": "alpaca",
                "data_quality": "real",
                "price": None,
                "volume": 250_000,
                "session_state": "regular",
                "is_non_real": False,
            }
        },
    )

    response = client.post("/api/scanner/run", json={"symbols": ["BADX"], "max_candidates": 10})
    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["blocked_count"] == 1
    assert diagnostics["rejected_candidates"][0]["candidate_status"] == "blocked"
    assert "missing_price" in diagnostics["rejected_candidates"][0]["hard_blockers"]


def test_synthetic_data_is_still_blocked(monkeypatch):
    snapshot = _passing_snapshot("FAKX")
    snapshot["synthetic_data_used"] = True
    _install_market_data(monkeypatch, {"FAKX": snapshot})

    response = client.post("/api/scanner/run", json={"symbols": ["FAKX"], "max_candidates": 10})
    diagnostics = response.json()["scanner_diagnostics"]
    assert diagnostics["status"] == "data_unavailable"
    assert diagnostics["rejected_candidates"][0]["candidate_status"] == "blocked"
    assert "provider_unavailable" in diagnostics["rejected_candidates"][0]["hard_blockers"]


def test_closed_session_wide_spread_is_warning_not_blocker(monkeypatch):
    snapshot = _passing_snapshot("WIDEX")
    snapshot["bid"] = 10.0
    snapshot["ask"] = 12.0
    snapshot["session_state"] = "unknown"
    _install_market_data(monkeypatch, {"WIDEX": snapshot})

    response = client.post("/api/scanner/run", json={"symbols": ["WIDEX"], "max_candidates": 10})
    diagnostics = response.json()["scanner_diagnostics"]
    row = diagnostics["selected_candidates"][0]
    assert "spread_too_wide" not in row["hard_blockers"]
    assert "wide_spread_after_hours" in row["soft_warnings"]


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
