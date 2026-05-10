from __future__ import annotations

from pathlib import Path
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
    assert response.status_code != 410, response.text
    if response.headers.get("content-type", "").startswith("application/json"):
        assert response.json().get("reason") != "legacy_runtime_disabled_real_data_only"


def _assert_blocked(method: str, path: str) -> None:
    response = client.request(method, path)
    assert response.status_code == 410
    assert response.json() == _disabled_payload()


def test_daytrading_v1_routes_allowed_in_production():
    _assert_allowed("GET", "/api/v1/daytrading/status")
    _assert_allowed("GET", "/api/v1/daytrading/scanner/latest")
    _assert_allowed("GET", "/api/v1/daytrading/workers/latest")
    _assert_allowed(
        "POST",
        "/api/v1/daytrading/scanner/run",
        json_body={"symbols": ["ROWX"], "max_candidates": 1},
    )
    _assert_allowed(
        "POST",
        "/api/v1/daytrading/workflow/run",
        json_body={"dry_run": True, "allow_submit": False, "symbols": [], "source": "runtime"},
    )
    _assert_allowed("GET", "/api/v1/daytrading/workflow/latest")
    _assert_allowed("GET", "/api/v1/daytrading/recommendation/latest")
    _assert_allowed("GET", "/api/v1/daytrading/evidence/strategies")
    _assert_allowed("GET", "/api/v1/daytrading/evidence/models")
    _assert_allowed("GET", "/api/v1/daytrading/risk/status")
    _assert_allowed("GET", "/api/v1/daytrading/execution-boundary")
    _assert_allowed("GET", "/api/v1/daytrading/contracts/routes")


def test_legacy_routes_still_blocked_in_production():
    for path in (
        "/api/command-center",
        "/api/live-watchlist/latest",
        "/api/edge-signals/latest",
        "/api/market/snapshots",
        "/api/features/latest",
        "/api/model-pipeline/status",
        "/api/candidate-universe",
        "/api/universe-selection/runs/latest",
    ):
        _assert_blocked("GET", path)


def test_new_daytrading_dashboard_calls_only_v1_api_paths():
    repo_root = Path(__file__).resolve().parents[2]
    page = repo_root / "frontend" / "src" / "app" / "daytrading-workflow" / "new" / "[[...section]]" / "page.tsx"
    text = page.read_text(encoding="utf-8")
    assert "/api/v1/daytrading/" in text
    legacy_substrings = (
        "/api/workflow-orchestrator",
        "/api/worker-status",
        "/api/scanner/run",
        "/api/promotion/",
        '"/health"',
        "/api/platform-readiness",
        "/api/final-readiness",
        "/api/command-center",
        "/api/live-watchlist",
        "/api/edge-signals",
        "/api/models/status",
        "/api/market/snapshots",
        "/api/features/",
        "/api/model-pipeline/",
        "/api/candidate-universe",
        "/api/universe-selection",
    )
    for frag in legacy_substrings:
        assert frag not in text, f"unexpected legacy fragment {frag!r} in new dashboard"


def test_daytrading_v1_router_does_not_embed_forbidden_legacy_paths():
    repo_root = Path(__file__).resolve().parents[2]
    src = (repo_root / "backend" / "app" / "api" / "routes" / "daytrading_v1.py").read_text(encoding="utf-8")
    forbidden = (
        "/api/command-center",
        "/api/live-watchlist",
        "/api/edge-signals",
        "/api/models/status",
        "/api/market/snapshots",
        "/api/features/",
        "/api/model-pipeline/",
        "/api/candidate-universe",
        "/api/universe-selection",
    )
    for frag in forbidden:
        assert frag not in src, f"unexpected {frag!r} in daytrading_v1.py"
