from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _production_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")


def _disabled_payload() -> dict[str, Any]:
    return {
        "status": "disabled",
        "reason": "legacy_runtime_disabled_real_data_only",
        "items": [],
        "symbol": None,
    }


def _assert_allowed(method: str, path: str, *, json_body: dict[str, Any] | None = None) -> None:
    response = client.request(method, path, json=json_body)
    assert response.status_code != 410
    if response.headers.get("content-type", "").startswith("application/json"):
        assert response.json().get("reason") != "legacy_runtime_disabled_real_data_only"


def _assert_blocked(method: str, path: str) -> None:
    response = client.request(method, path)
    assert response.status_code == 410
    assert response.json() == _disabled_payload()


def test_production_allowlist_routes_pass():
    _assert_allowed("GET", "/health")
    _assert_allowed("GET", "/api/platform-readiness/status")
    _assert_allowed("GET", "/api/final-readiness/status")
    _assert_allowed(
        "POST",
        "/api/workflow-orchestrator/run",
        json_body={
            "workflow_name": "US Stock Day-Trading Workflow v1",
            "asset_class": "stock",
            "horizon": "day_trading",
            "mode": "paper_first",
            "source": "runtime",
            "symbols": [],
            "max_candidates": 5,
            "stop_at_stage": 10,
            "dry_run": True,
            "require_human_approval": True,
            "allow_submit": False,
        },
    )
    _assert_allowed("GET", "/api/worker-status/latest")
    _assert_allowed("POST", "/api/scanner/run", json_body={"symbols": ["ROWX"], "max_candidates": 1})
    _assert_allowed("GET", "/api/promotion/strategies/status")
    _assert_allowed("GET", "/api/promotion/models/status")


def test_production_legacy_runtime_routes_are_blocked():
    for path in (
        "/api/market/snapshots",
        "/api/edge-signals/latest",
        "/api/command-center",
        "/api/live-watchlist/latest",
        "/api/models/status",
        "/api/workflow-orchestrator/latest",
        "/api/platform-readiness",
        "/metrics",
        "/",
    ):
        _assert_blocked("GET", path)


def test_non_production_does_not_apply_allowlist(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "development")

    response = client.get("/api/platform-readiness")

    assert response.status_code != 410
