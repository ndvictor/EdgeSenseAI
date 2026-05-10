from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_promotion_strategies_status_readonly():
    client = TestClient(app)
    r = client.get("/api/promotion/strategies/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_source"] == "promotion_center_readonly_v1"
    assert isinstance(payload["strategies"], list)
    for row in payload["strategies"]:
        assert "strategy_key" in row
        assert "promotion_readiness" in row
        assert row["promotion_readiness"] in {"not_ready", "eligible_for_review"}
        assert isinstance(row["blockers"], list)


def test_promotion_models_status_readonly():
    client = TestClient(app)
    r = client.get("/api/promotion/models/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["models"], list)
    for row in payload["models"]:
        assert "model_key" in row
        assert row["promotion_readiness"] in {"not_ready", "eligible_for_review"}
