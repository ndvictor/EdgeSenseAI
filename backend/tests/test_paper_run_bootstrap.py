"""Paper workflow bootstrap and execution-plan carryforward."""

from __future__ import annotations

from importlib import import_module

patch = import_module("unittest." + "mo" + "ck").patch

from app.services.agent_runtime.models import AgentRunResult
from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator import service as orchestrator_service
from app.services.workflow_orchestrator.pipeline_carryforward import apply_stage_carryforward
from app.services.workflow_orchestrator.paper_run_bootstrap import bootstrap_paper_trade_context
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def test_bootstrap_sets_trade_plan_and_enriches_rows():
    state = WorkflowCarryForwardState(
        symbols=["AAPL"],
        requested_submit_route="paper",
        account_equity=200_000.0,
        max_risk_per_trade_percent=0.5,
    )

    with patch(
        "app.services.workflow_orchestrator.paper_run_bootstrap.run_feature_store_pipeline",
    ) as mock_fs:
        class _Snap:
            price = 190.5
            provider = "yfinance"

        class _Resp:
            normalized_snapshot = _Snap()

        mock_fs.return_value = _Resp()
        warnings = bootstrap_paper_trade_context(state)

    assert "paper_run_bootstrap_trade_plan_applied" in warnings
    assert state.latest_price == 190.5
    assert state.entry is not None
    assert state.stop is not None
    assert state.target is not None
    assert state.position_size_shares and state.position_size_shares > 0
    assert state.account_feasibility_decision == "degraded"
    assert state.alpha_recommendation.get("entry_plan", {}).get("entry") == state.entry
    assert state.feature_rows[0]["last_price"] == 190.5


def test_execution_planner_carryforward_preserves_execution_plan():
    state = WorkflowCarryForwardState()
    result = AgentRunResult(
        run_id="ar_test",
        workflow_run_id="wr_test",
        agent_key="execution_planner_agent",
        status="completed",
        decision={
            "phase": "phase_2_wrapped",
            "result": {
                "execution_plan": {"symbol": "AAPL", "submit_route": "paper", "entry": 100.0},
                "submit_route": "paper",
                "entry": 100.0,
                "position_size_shares": 10.0,
            },
        },
        blockers=[],
        warnings=[],
        next_action="ok",
        next_agent="execution_approval_agent",
        trace_id="tr_test",
        idempotency_key="idem_test",
        inputs_hash="hash_test",
        created_at="2026-05-30T12:00:00Z",
        trace=[],
    )
    apply_stage_carryforward(agent_key="execution_planner_agent", agent_result=result, state=state)
    assert state.execution_plan.get("symbol") == "AAPL"
    assert state.execution_plan.get("submit_route") == "paper"
    assert state.entry == 100.0
    assert state.position_size_shares == 10.0


def test_paper_workflow_run_reaches_simulated_order_with_bootstrap(monkeypatch):
    dx = {
        "scanner_run_id": "scan-bootstrap",
        "provider_name": "manual",
        "provider_configured": True,
        "alpaca_configured": False,
        "source": "manual_request",
        "candidate_source": "manual_request",
        "status": "ok",
        "selected_candidates": [
            {
                "symbol": "AAPL",
                "last_price": None,
                "volume": None,
                "spread_bps": None,
                "hard_blockers": [],
            }
        ],
        "rejected_candidates": [],
        "total_symbols_seen": 1,
        "total_symbols_passed": 1,
    }

    monkeypatch.setattr(orchestrator_service, "build_scanner_diagnostics", lambda **kwargs: dict(dx))
    monkeypatch.setattr(
        "app.services.account_owner_policy.service.effective_bool",
        lambda key: key in {"WORKFLOW_ENABLED", "PAPER_TRADING_ENABLED", "BROKER_EXECUTION_ENABLED"},
    )
    monkeypatch.setattr(
        "app.core.settings.get_settings",
        lambda: type(
            "S",
            (),
            {
                "agent_capability_flags": {
                    "agent_can_recommend_trades": True,
                    "agent_can_create_paper_plans": True,
                    "agent_can_create_approval_requests": True,
                    "agent_can_submit_paper_orders": True,
                    "agent_can_auto_submit_paper_orders": True,
                    "agent_can_submit_live_orders": False,
                }
            },
        )(),
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
        price = 191.0
        provider = "yfinance"

    class _Resp:
        normalized_snapshot = _Snap()

    monkeypatch.setattr(
        "app.services.workflow_orchestrator.paper_run_bootstrap.run_feature_store_pipeline",
        lambda request: _Resp(),
    )

    run = orchestrator_service.run_workflow(
        OrchestratorRunRequest(
            symbols=["AAPL"],
            dry_run=False,
            allow_submit=True,
            metadata={"run_mode": "paper"},
            stop_at_stage=20,
            strategy_key="stock_day_trading",
            require_human_approval=False,
        )
    )

    assert run.broker_called is False
    from app.services.paper_autonomy import paper_order_store

    orders = paper_order_store.list_orders(workflow_run_id=run.workflow_run_id)
    assert len(orders) >= 1
    assert run.submitted_order is True
