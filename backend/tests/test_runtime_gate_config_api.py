"""Trading Gates And Run Control API tests.

These tests cover the owner-controlled runtime gate surface added for the
DeepAgents Control Tower:

- live + broker execution default disabled,
- mutations require OPS_ADMIN_TOKEN,
- paper gates can be enabled from the API,
- live gates require explicit confirmation and owner authority,
- workflow RUN is protected and validates paper/live gate state before calling
  the orchestrator.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import daytrading_v1
from app.main import app
from app.services.workflow_orchestrator.models import OrchestratorRunResponse, iso_utc_now


client = TestClient(app)
TOKEN = "test-ops-token"
HEADERS = {"X-Ops-Admin-Token": TOKEN, "X-Ops-Admin-Email": "owner@example.com"}


@pytest.fixture(autouse=True)
def _isolated_runtime_settings(tmp_path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "runtime_settings.json"
    monkeypatch.setattr("app.core.runtime_settings_store.RUNTIME_SETTINGS_FILE", path)
    monkeypatch.setenv("OPS_ADMIN_TOKEN", TOKEN)
    yield


def test_gate_defaults_disable_live_and_broker_execution() -> None:
    response = client.get("/api/v1/daytrading/settings/gates")

    assert response.status_code == 200
    payload = response.json()
    gates = payload["gates"]
    assert gates["live"]["live_trading_enabled"] is False
    assert gates["live"]["broker_execution_enabled"] is False
    assert gates["broker_called"] is False
    assert payload["context"]["live_run_allowed"] is False


def test_process_env_overrides_stale_runtime_file_on_gate_read(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Azure Portal env must win over baked runtime_settings.json defaults."""
    path = tmp_path / "runtime_settings.json"
    path.write_text(
        '{"OWNER_AUTHORITY_LEVEL":"paper_manual","AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS":false}',
        encoding="utf-8",
    )
    monkeypatch.setenv("OWNER_AUTHORITY_LEVEL", "paper_auto")
    monkeypatch.setenv("AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS", "true")

    response = client.get("/api/v1/daytrading/settings/gates")

    assert response.status_code == 200
    gates = response.json()["gates"]
    assert gates["live"]["owner_authority_level"] == "paper_auto"
    assert gates["paper"]["agent_can_auto_submit_paper_orders"] is True


def test_gate_mutation_requires_ops_admin_token() -> None:
    response = client.put(
        "/api/v1/daytrading/settings/gates",
        json={"paper_trading_enabled": True},
    )

    assert response.status_code == 401


def test_api_can_enable_paper_gates_and_audit_operator() -> None:
    response = client.put(
        "/api/v1/daytrading/settings/gates",
        headers=HEADERS,
        json={
            "paper_trading_enabled": True,
            "agent_can_submit_paper_orders": True,
            "agent_can_auto_submit_paper_orders": True,
            "owner_authority_level": "paper_auto",
            "change_reason": "enable autonomous paper loop",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["gates"]["paper"]["agent_can_auto_submit_paper_orders"] is True
    assert payload["gates"]["live"]["owner_authority_level"] == "paper_auto"
    assert payload["gates"]["audit"]["updated_by_email"] == "owner@example.com"
    assert payload["gates"]["audit"]["change_reason"] == "enable autonomous paper loop"


def test_live_gate_enable_requires_confirmation() -> None:
    response = client.put(
        "/api/v1/daytrading/settings/gates",
        headers=HEADERS,
        json={
            "live_trading_enabled": True,
            "broker_execution_enabled": True,
            "require_human_approval": True,
            "owner_authority_level": "live_submit",
        },
    )

    assert response.status_code == 400
    assert "confirm_live" in str(response.json()["detail"])


def test_live_gate_enable_with_confirmation() -> None:
    response = client.put(
        "/api/v1/daytrading/settings/gates",
        headers=HEADERS,
        json={
            "live_trading_enabled": True,
            "broker_execution_enabled": True,
            "require_human_approval": True,
            "owner_authority_level": "live_submit",
            "agent_can_submit_live_orders": True,
            "confirm_live": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["gates"]["live"]["live_trading_enabled"] is True
    assert payload["gates"]["live"]["broker_execution_enabled"] is True
    assert payload["context"]["live_run_allowed"] is True


def _fake_orchestrator_response(*, broker_called: bool = False, submitted_order: bool = False) -> OrchestratorRunResponse:
    return OrchestratorRunResponse(
        orchestrator_run_id="or_test",
        workflow_run_id="wr_test",
        status="completed_preview",
        current_stage=100,
        current_agent_key=None,
        broker_called=broker_called,
        submitted_order=submitted_order,
        recommendation={"status": "ok", "symbol": "AAPL"},
        llm_used=False,
        created_at=iso_utc_now(),
        updated_at=iso_utc_now(),
    )


def test_paper_run_requires_token_and_never_calls_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    response = client.post("/api/v1/daytrading/workflow/run", json={"run_mode": "paper"})
    assert response.status_code == 401

    client.put(
        "/api/v1/daytrading/settings/gates",
        headers=HEADERS,
        json={"paper_trading_enabled": True},
    )

    def fake_run_workflow(req: Any) -> OrchestratorRunResponse:
        assert req.allow_submit is True
        assert req.dry_run is False
        return _fake_orchestrator_response(broker_called=False, submitted_order=False)

    monkeypatch.setattr(daytrading_v1, "run_workflow", fake_run_workflow)

    response = client.post(
        "/api/v1/daytrading/workflow/run",
        headers=HEADERS,
        json={"run_mode": "paper", "symbols": ["AAPL"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_mode"] == "paper"
    assert payload["broker_called"] is False


def test_live_run_rejected_until_gates_and_phrase_allow_it(monkeypatch: pytest.MonkeyPatch) -> None:
    response = client.post(
        "/api/v1/daytrading/workflow/run",
        headers=HEADERS,
        json={"run_mode": "live", "confirm_live": True, "confirm_live_phrase": "LIVE"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "live_run_blocked_by_gates"

    client.put(
        "/api/v1/daytrading/settings/gates",
        headers=HEADERS,
        json={
            "live_trading_enabled": True,
            "broker_execution_enabled": True,
            "require_human_approval": True,
            "owner_authority_level": "live_submit",
            "confirm_live": True,
        },
    )

    bad_phrase = client.post(
        "/api/v1/daytrading/workflow/run",
        headers=HEADERS,
        json={"run_mode": "live", "confirm_live": True, "confirm_live_phrase": "NOT LIVE"},
    )
    assert bad_phrase.status_code == 400
    assert bad_phrase.json()["detail"]["error"] == "live_run_requires_confirm_phrase"

    def fake_live_run_workflow(req: Any) -> OrchestratorRunResponse:
        assert req.mode == "live"
        assert req.allow_submit is True
        return _fake_orchestrator_response(broker_called=False, submitted_order=False)

    monkeypatch.setattr(daytrading_v1, "run_workflow", fake_live_run_workflow)

    ok = client.post(
        "/api/v1/daytrading/workflow/run",
        headers=HEADERS,
        json={"run_mode": "live", "confirm_live": True, "confirm_live_phrase": "LIVE"},
    )
    assert ok.status_code == 200
    assert ok.json()["run_mode"] == "live"


def test_invalid_percent_gate_rejected() -> None:
    response = client.put(
        "/api/v1/daytrading/settings/gates",
        headers=HEADERS,
        json={"max_risk_per_trade_pct": 101},
    )

    assert response.status_code == 422
