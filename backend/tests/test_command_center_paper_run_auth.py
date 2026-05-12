from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
import app.api.routes.daytrading_v1 as daytrading_v1


client = TestClient(app)


class FakeRun:
    status = "ok"
    recommendation = None
    submitted_order = True
    broker_called = False
    llm_used = False
    blockers = []
    warnings = []

    def model_dump(self):
        return {
            "status": self.status,
            "submitted_order": self.submitted_order,
            "broker_called": self.broker_called,
            "live_submit_enabled": False,
            "submit_route": "paper",
            "blockers": [],
            "warnings": [],
        }


def test_paper_run_works_without_token(monkeypatch):
    monkeypatch.setattr(daytrading_v1, "can_run_paper_workflow", lambda: (True, []))
    monkeypatch.setattr(daytrading_v1, "run_workflow", lambda req: FakeRun())

    response = client.post(
        "/api/v1/daytrading/workflow/run",
        json={
            "run_mode": "paper",
            "symbols": [],
            "confirm_live": False,
            "confirm_live_phrase": None,
            "requested_by_email": "vndayambaje@gmail.com",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_mode"] == "paper"
    assert body["broker_called"] is False
    assert body["live_submit_enabled"] is False
    assert body["run"]["broker_called"] is False
    assert body["run"]["live_submit_enabled"] is False


def test_live_run_blocked_by_live_gates_not_token(monkeypatch):
    monkeypatch.setattr(
        daytrading_v1,
        "can_run_live_workflow",
        lambda: (False, ["live_trading_enabled is false", "broker_execution_enabled is false"]),
    )

    response = client.post(
        "/api/v1/daytrading/workflow/run",
        json={
            "run_mode": "live",
            "symbols": [],
            "confirm_live": True,
            "confirm_live_phrase": "LIVE",
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "live_run_blocked_by_gates"
    assert "live_trading_enabled is false" in detail["reasons"]


def test_paper_run_blocked_by_paper_gates_not_token(monkeypatch):
    monkeypatch.setattr(
        daytrading_v1,
        "can_run_paper_workflow",
        lambda: (False, ["paper_trading_enabled is false"]),
    )

    response = client.post(
        "/api/v1/daytrading/workflow/run",
        json={
            "run_mode": "paper",
            "symbols": [],
            "confirm_live": False,
            "confirm_live_phrase": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "paper_run_blocked_by_gates"
