from __future__ import annotations

from fastapi.testclient import TestClient

import app.services.qlib_integration.service as qlib_service
from app.main import app


client = TestClient(app)


def test_qlib_unavailable_returns_safe_status(monkeypatch):
    qlib_service._MEMORY.clear()
    monkeypatch.setattr(qlib_service, "_probe_qlib", lambda: (False, None, ["qlib_not_installed_or_not_configured"]))

    status = qlib_service.get_qlib_status()

    assert status.qlib_available is False
    assert status.configured is False
    assert "qlib_not_installed_or_not_configured" in status.blockers
    assert "workflow can continue" in status.next_action


def test_qlib_score_endpoint_unavailable_returns_placeholder_not_trained(monkeypatch):
    qlib_service._MEMORY.clear()
    monkeypatch.setattr(qlib_service, "_probe_qlib", lambda: (False, None, ["qlib_not_installed_or_not_configured"]))
    monkeypatch.setattr(qlib_service, "_db_session", lambda: None)

    response = client.post("/api/qlib/signals/score", json={"symbols": ["TEST_STOCK_A"], "symbol": "TEST_STOCK_A", "scores": {}})

    assert response.status_code == 200
    artifact = response.json()["artifact"]
    assert artifact["artifact_type"] == "signal_scores"
    assert artifact["artifact_status"] == "simulated"
    assert artifact["qlib_available"] is False
    assert "qlib_unavailable_scores_are_placeholder" in artifact["warnings"]
    assert artifact["metadata"]["trained_model_backed"] is False
    assert artifact["scores"]["TEST_STOCK_A"]["source"] == "placeholder_not_trained"


def test_qlib_available_without_model_artifact_marks_scores_unavailable(monkeypatch):
    qlib_service._MEMORY.clear()
    monkeypatch.setattr(qlib_service, "_probe_qlib", lambda: (True, "1.0-test", []))
    monkeypatch.setattr(qlib_service, "_db_session", lambda: None)

    artifact = qlib_service.save_signal_scores(
        qlib_service.QlibSignalScoreCreate(symbols=["TEST_STOCK_A"], symbol="TEST_STOCK_A", scores={"TEST_STOCK_A": {"score": 0.4}})
    )

    assert artifact.artifact_type == "signal_scores"
    assert artifact.artifact_status == "unavailable"
    assert "no_qlib_model_artifact_registered" in artifact.blockers
