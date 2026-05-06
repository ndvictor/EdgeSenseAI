"""Contract tests for /api/integration-checks (no required external APIs)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_integration_checks_catalog():
    r = client.get("/api/integration-checks/catalog")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 17
    keys = {c["key"] for c in body["checks"]}
    assert "paper_order" in keys
    assert "data_source_connectivity" in keys


def test_integration_checks_run_subset():
    """Deterministic checks only — avoids live market/provider HTTP in CI."""
    r = client.post(
        "/api/integration-checks/run",
        json={
            "symbols": ["SPY"],
            "source": "mock",
            "allow_mock": True,
            "checks": [
                "ranking_model",
                "risk_check",
                "portfolio_check",
                "alerts",
                "post_trade_analytics",
                "strategy_decay",
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"]
    assert body["status"] in {"pass", "warn", "fail"}
    assert "checks" in body
    assert len(body["checks"]) == 6
    for c in body["checks"]:
        assert c["key"]
        assert c["status"] in {"pass", "warn", "fail", "skip"}
        assert c["belongs_to"]


def test_integration_checks_no_secrets_in_response():
    r = client.post(
        "/api/integration-checks/run",
        json={"symbols": ["AAPL"], "checks": ["alerts"], "allow_mock": True},
    )
    assert r.status_code == 200
    text = r.text
    assert "APCA-API-SECRET" not in text
    assert "APCA-API-KEY-ID" not in text
