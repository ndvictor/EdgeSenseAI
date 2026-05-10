from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _assert_disabled(method: str, path: str) -> None:
    response = client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code in {410, 503}
    assert response.json() == {
        "status": "disabled",
        "reason": "legacy_runtime_disabled_real_data_only",
        "items": [],
        "symbol": None,
    }


def test_legacy_edge_signals_and_recommendation_routes_are_disabled():
    _assert_disabled("GET", "/api/edge-signals/latest")
    _assert_disabled("POST", "/api/edge-signals/scan")
    _assert_disabled("POST", "/api/decision-workflows/run-default")
    _assert_disabled("POST", "/api/recommendation-pipeline/run")


def test_legacy_universe_candidate_snapshot_and_model_lab_routes_are_disabled():
    _assert_disabled("GET", "/api/candidate-universe")
    _assert_disabled("POST", "/api/candidate-universe/add")
    _assert_disabled("GET", "/api/universe-selection/runs/latest")
    _assert_disabled("POST", "/api/universe-selection/run")
    _assert_disabled("GET", "/api/market/snapshots")
    _assert_disabled("GET", "/api/feature-store/latest")
    _assert_disabled("POST", "/api/model-lab/run")
    _assert_disabled("POST", "/api/workflow-scheduler/run-once")


def test_production_allowed_routes_are_not_quarantined():
    worker_status = client.get("/api/worker-status/latest")
    assert worker_status.status_code != 410
    assert worker_status.json()["status"] == "ok"

    health = client.get("/health")
    assert health.status_code != 410
