from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main_app
import app.api.routes.workflow_orchestrator as workflow_orchestrator_routes


class _FakeWorkflowRun(SimpleNamespace):
    def model_dump(self):
        return dict(self.__dict__)


def _client_in_production(monkeypatch) -> TestClient:
    monkeypatch.setattr(main_app.settings, "app_env", "production")
    monkeypatch.setattr(main_app.settings, "environment", "production")
    return TestClient(main_app.app)


def test_production_allowlist_allows_only_contract_routes(monkeypatch):
    client = _client_in_production(monkeypatch)

    fake_run = _FakeWorkflowRun(
        status="no_qualified_setup",
        recommendation={"status": "no_qualified_setup", "symbol": None},
        submitted_order=False,
        broker_called=False,
        llm_used=False,
        blockers=["no_scanner_candidates_passed_filters"],
        warnings=[],
        workflow_run_id="wr_allowlist_test",
    )
    monkeypatch.setattr(workflow_orchestrator_routes, "run_workflow", lambda _body: fake_run)

    allowed = [
        ("GET", "/health", None),
        ("GET", "/api/platform-readiness/status", None),
        ("GET", "/api/final-readiness/status", None),
        ("POST", "/api/workflow-orchestrator/run", {"dry_run": True, "allow_submit": False, "symbols": []}),
        ("GET", "/api/worker-status/latest", None),
        ("POST", "/api/scanner/run", {"symbols": [], "strategy_key": "stock_day_trading"}),
        ("GET", "/api/promotion/strategies/status", None),
        ("GET", "/api/promotion/models/status", None),
    ]

    for method, path, payload in allowed:
        response = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
        assert response.status_code != 410, f"{method} {path} should be production-allowed"


def test_production_allowlist_blocks_legacy_routes(monkeypatch):
    client = _client_in_production(monkeypatch)

    blocked = [
        "/api/market/snapshots",
        "/api/edge-signals/latest",
        "/api/command-center",
        "/api/live-watchlist/latest",
        "/api/models/status",
        "/api/workflow-orchestrator/latest",
        "/api/platform-readiness",
        "/metrics",
        "/",
    ]

    for path in blocked:
        response = client.get(path)
        assert response.status_code == 410, path
        body = response.json()
        assert body["status"] == "disabled"
        assert body["reason"] == main_app.LEGACY_DISABLED_REASON
        assert body["items"] == []
        assert body["symbol"] is None


def test_non_production_keeps_legacy_routes_available(monkeypatch):
    monkeypatch.setattr(main_app.settings, "app_env", "dev")
    monkeypatch.setattr(main_app.settings, "environment", "dev")
    client = TestClient(main_app.app)

    response = client.get("/metrics")
    assert response.status_code != 410
