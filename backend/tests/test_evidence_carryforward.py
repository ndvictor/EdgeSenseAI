from __future__ import annotations

from typing import Any

import app.services.agent_runtime.wrappers.backtest_validation_adapter as backtest_adapter
import app.services.agent_runtime.wrappers.qlib_adapter as qlib_adapter
from app.services.agent_runtime.models import AgentRunResult, iso_utc_now
from app.services.workflow_orchestrator.pipeline_carryforward import apply_stage_carryforward
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def _agent_result(agent_key: str, result: dict[str, Any]) -> AgentRunResult:
    return AgentRunResult(
        run_id=f"ar_{agent_key}",
        workflow_run_id="wr_evidence",
        agent_key=agent_key,
        status="completed",
        decision={"phase": "test", "agent_key": agent_key, "tool": f"test.{agent_key}", "result": result},
        blockers=[],
        warnings=list(result.get("warnings") or []),
        next_action="ok",
        next_agent=result.get("next_agent"),
        artifacts={"llm_used": False, "broker_called": False, "submitted_order": False},
        trace_id=f"tr_{agent_key}",
        trace=[],
        idempotency_key=f"id:{agent_key}",
        inputs_hash=f"hash:{agent_key}",
        created_at=iso_utc_now(),
        persistence_mode="memory",
    )


def test_backtest_validation_agent_does_not_fake_proof(monkeypatch):
    monkeypatch.setattr(backtest_adapter, "list_proof_records", lambda limit=50: [])
    monkeypatch.setattr(backtest_adapter, "list_artifacts", lambda limit=50: [])

    out = backtest_adapter.validate_backtest_or_proof(strategy_key="stock_day_trading", asset_class="stock", horizon="day_trading")

    assert out["proof_status"] == "backtest_required"
    assert out["proof_status"] != "proven"
    assert "no_proof_record_found" in out["blockers"]


def test_qlib_research_agent_does_not_block_when_qlib_unavailable(monkeypatch):
    class Status:
        qlib_available = False
        qlib_version = None
        configured = False
        artifact_count = 0
        latest_signal_count = 0
        latest_backtest_count = 0
        latest_model_count = 0
        blockers = ["qlib_not_installed_or_not_configured"]
        warnings = ["qlib_optional_not_required_for_workflow"]
        next_action = "Qlib is optional and workflow can continue unless selected strategy requires Qlib evidence."

    monkeypatch.setattr(qlib_adapter, "get_qlib_status", lambda: Status())
    monkeypatch.setattr(qlib_adapter, "get_latest_signal_scores", lambda: None)
    monkeypatch.setattr(qlib_adapter, "list_artifacts", lambda limit=10: [])

    out = qlib_adapter.qlib_research_snapshot()

    assert out["qlib_available"] is False
    assert out["blockers"] == []
    assert "qlib_not_installed_or_not_configured" in out["warnings"]
    assert out["next_agent"] == "backtest_validation_agent"


def test_orchestrator_carry_forward_includes_qlib_proof_model_strategy_evidence_fields():
    state = WorkflowCarryForwardState(symbols=["AMD"])

    apply_stage_carryforward(
        agent_key="qlib_research_agent",
        agent_result=_agent_result(
            "qlib_research_agent",
            {
                "qlib_available": False,
                "qlib_version": None,
                "qlib_artifact_id": "qa_1",
                "qlib_artifact_counts": {"signal": 1, "backtest": 0, "model": 0, "total": 1},
                "warnings": ["qlib_not_installed_or_not_configured"],
            },
        ),
        state=state,
    )
    apply_stage_carryforward(
        agent_key="model_selection_agent",
        agent_result=_agent_result("model_selection_agent", {"selected_model_key": "rules_v1", "selected_model_keys": ["rules_v1"]}),
        state=state,
    )
    apply_stage_carryforward(
        agent_key="strategy_selection_agent",
        agent_result=_agent_result("strategy_selection_agent", {"selected_strategy_key": "stock_day_trading", "proof_status": "backtest_required"}),
        state=state,
    )
    apply_stage_carryforward(
        agent_key="backtest_validation_agent",
        agent_result=_agent_result(
            "backtest_validation_agent",
            {
                "proof_id": "proof_1",
                "proof_status": "backtest_required",
                "blockers": ["no_proof_record_found"],
                "warnings": ["Proof is required"],
            },
        ),
        state=state,
    )
    apply_stage_carryforward(
        agent_key="small_account_feasibility_agent",
        agent_result=_agent_result(
            "small_account_feasibility_agent",
            {
                "decision": "degraded",
                "account_equity": 1000.0,
                "max_risk_dollars": 5.0,
                "max_daily_loss_dollars": 15.0,
                "feasible_symbols": ["AMD"],
                "rejected_symbols": [],
                "blockers": [],
                "warnings": ["proof_not_ready_for_small_account"],
            },
        ),
        state=state,
    )

    assert state.qlib_available is False
    assert state.qlib_artifact_id == "qa_1"
    assert state.qlib_artifact_counts["signal"] == 1
    assert state.selected_model_key == "rules_v1"
    assert state.selected_strategy_key == "stock_day_trading"
    assert state.strategy_key == "stock_day_trading"
    assert state.proof_status == "backtest_required"
    assert state.proof_id == "proof_1"
    assert "no_proof_record_found" in state.evidence_blockers
    assert state.small_account_decision == "degraded"
    assert state.max_risk_dollars == 5.0
    assert state.max_daily_loss_dollars == 15.0
    assert state.feasible_symbols == ["AMD"]
    assert "proof_not_ready_for_small_account" in state.small_account_warnings
