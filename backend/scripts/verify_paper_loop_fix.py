#!/usr/bin/env python3
"""Verify paper workflow populates the autonomy loop (no loop_empty after run)."""

from __future__ import annotations

import os
import sys
from importlib import import_module

# backend/ on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

patch = import_module("unittest.mock").patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.paper_autonomy import paper_order_store, paper_position_store
import app.services.workflow_orchestrator.service as orchestrator_service

client = TestClient(app)

SCANNER_DX = {
    "scanner_run_id": "verify-paper-loop",
    "provider_name": "manual",
    "provider_configured": True,
    "alpaca_configured": True,
    "source": "manual_request",
    "candidate_source": "manual_request",
    "status": "ok",
    "selected_candidates": [{"symbol": "AAPL", "hard_blockers": []}],
    "rejected_candidates": [],
    "total_symbols_seen": 1,
    "total_symbols_passed": 1,
}

AGENT_FLAGS = {
    "agent_can_recommend_trades": True,
    "agent_can_create_paper_plans": True,
    "agent_can_create_approval_requests": True,
    "agent_can_submit_paper_orders": True,
    "agent_can_auto_submit_paper_orders": True,
    "agent_can_submit_live_orders": False,
}


def _patch_runtime(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator_service, "build_scanner_diagnostics", lambda **kwargs: dict(SCANNER_DX))
    monkeypatch.setattr(
        "app.services.account_owner_policy.service.effective_bool",
        lambda key: key in {"WORKFLOW_ENABLED", "PAPER_TRADING_ENABLED", "BROKER_EXECUTION_ENABLED"},
    )
    monkeypatch.setattr(
        "app.core.settings.get_settings",
        lambda: type("S", (), {"agent_capability_flags": dict(AGENT_FLAGS)})(),
    )
    monkeypatch.setattr(
        "app.services.alpaca_paper_account_service.get_alpaca_paper_snapshot",
        lambda: type(
            "Snap",
            (),
            {"account": type("A", (), {"equity": 200_000.0, "buying_power": 200_000.0})()},
        )(),
    )

    class _Snap:
        price = 191.25
        provider = "yfinance"

    class _Resp:
        normalized_snapshot = _Snap()

    monkeypatch.setattr(
        "app.services.workflow_orchestrator.paper_run_bootstrap.run_feature_store_pipeline",
        lambda request: _Resp(),
    )


def main() -> int:
    token = (os.environ.get("OPS_ADMIN_TOKEN") or "").strip()
    if not token:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.isfile(env_path):
            for line in open(env_path, encoding="utf-8"):
                if line.startswith("OPS_ADMIN_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
    if not token:
        print("FAIL: OPS_ADMIN_TOKEN not set")
        return 1

    os.environ["OPS_ADMIN_TOKEN"] = token
    headers = {"X-Ops-Admin-Token": token}
    mp = import_module("pytest").MonkeyPatch()
    _patch_runtime(mp)
    try:
        pre_orders = len(paper_order_store.list_orders())
        pre_open = len(paper_position_store.list_open())

        gates = client.put(
            "/api/v1/daytrading/settings/gates",
            headers=headers,
            json={
                "paper_trading_enabled": True,
                "owner_authority_level": "paper_auto",
                "agent_can_auto_submit_paper_orders": True,
            },
        )
        if gates.status_code != 200:
            print(f"FAIL: gates PUT {gates.status_code} {gates.text[:300]}")
            return 1

        tower_before = client.get("/api/v1/daytrading/paper-autonomy/control-tower")
        assert tower_before.status_code == 200
        alerts_before = {a.get("code") for a in tower_before.json().get("alerts") or []}

        run = client.post(
            "/api/v1/daytrading/workflow/run",
            headers=headers,
            json={"run_mode": "paper", "symbols": ["AAPL"], "source": "runtime"},
        )
        if run.status_code != 200:
            print(f"FAIL: workflow/run {run.status_code} {run.text[:500]}")
            return 1

        body = run.json()
        orders = paper_order_store.list_orders()
        new_orders = len(orders) - pre_orders
        open_pos = len(paper_position_store.list_open()) - pre_open

        tower_after = client.get("/api/v1/daytrading/paper-autonomy/control-tower")
        payload = tower_after.json()
        summary = payload.get("summary") or {}
        alert_codes = [a.get("code") for a in payload.get("alerts") or []]

        print("--- paper loop verification ---")
        print(f"workflow status: {body.get('status')}")
        print(f"submitted_order: {body.get('submitted_order')}")
        print(f"broker_called: {body.get('broker_called')}")
        print(f"new paper orders: {new_orders}")
        print(f"new open positions: {open_pos}")
        print(f"control_tower paper_orders: {summary.get('paper_orders')}")
        print(f"alerts before: {sorted(alerts_before)}")
        print(f"alerts after:  {sorted(set(alert_codes))}")
        if body.get("blockers"):
            print(f"blockers (sample): {body.get('blockers')[:12]}")

        failures: list[str] = []
        if new_orders < 1:
            failures.append("expected at least one new paper order")
        if body.get("broker_called"):
            failures.append("broker_called must stay false")
        if not body.get("submitted_order"):
            failures.append("workflow response submitted_order should be true")
        if "loop_empty" in alert_codes and summary.get("paper_orders", 0) > 0:
            failures.append("loop_empty alert present but paper_orders > 0")

        if failures:
            print("FAIL:")
            for f in failures:
                print(f"  - {f}")
            return 1

        print("PASS: paper workflow created records; loop_empty cleared when orders exist.")
        if "loop_empty" in alerts_before and "loop_empty" not in alert_codes:
            print("      (loop_empty was present before run and is gone after)")
        elif "loop_empty" not in alert_codes:
            print("      (control tower has no loop_empty alert)")
        return 0
    finally:
        mp.undo()


if __name__ == "__main__":
    raise SystemExit(main())
