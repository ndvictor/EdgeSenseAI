from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import app.services.agent_runtime.wrappers.qlib_adapter as qlib_adapter
import app.services.agent_runtime.wrappers.strategy_selection_adapter as strategy_adapter
import app.services.agent_runtime.wrappers.backtest_validation_adapter as backtest_adapter
import app.services.workflow_orchestrator.service as orchestrator_service
from app.services.model_evidence.models import ModelEvidenceOut
from app.services.model_evidence.service import evaluate_model_evidence
from app.services.proof_registry.models import ProofRegistryRecordOut
from app.services.qlib_integration.models import QlibArtifactOut
from app.services.strategy_evidence.models import StrategyEvidenceOut
from app.services.strategy_evidence.service import evaluate_strategy_evidence
from app.services.workflow_governance.models import WorkflowGovernanceCheckRequest
from app.services.workflow_governance.service import check_governance
from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def test_orchestrator_accepts_day_trading(monkeypatch):
    monkeypatch.setattr(orchestrator_service, "_db_session", lambda: None)
    monkeypatch.setattr(orchestrator_service, "write_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(orchestrator_service, "default_stage_plan", lambda **_kwargs: [])
    monkeypatch.setattr(orchestrator_service, "orchestrator_pipeline_agent_count", lambda: 0)
    monkeypatch.setattr(
        orchestrator_service,
        "check_governance",
        lambda _req: SimpleNamespace(decision="allowed", blockers=[], warnings=[], next_action="ok", model_dump=lambda: {}),
    )

    run = orchestrator_service.run_workflow(OrchestratorRunRequest(horizon="day_trading", dry_run=True, symbols=["AMD"]))

    assert run.status == "completed_preview"
    assert "horizon_not_supported_for_autonomous_workflow" not in run.blockers
    assert run.supported_horizons == ["day_trading"]


def test_orchestrator_blocks_swing_trading_horizon(monkeypatch):
    monkeypatch.setattr(orchestrator_service, "_db_session", lambda: None)
    monkeypatch.setattr(orchestrator_service, "write_event", lambda *_args, **_kwargs: None)

    run = orchestrator_service.run_workflow(OrchestratorRunRequest(horizon="swing_trading", dry_run=True, symbols=["AMD"]))

    assert run.status == "blocked"
    assert "horizon_not_supported_for_autonomous_workflow" in run.blockers
    assert run.supported_horizons == ["day_trading"]


def test_governance_blocks_non_day_trading_horizon(monkeypatch):
    import app.services.workflow_governance.service as governance_service

    monkeypatch.setattr(governance_service, "_db_session", lambda: None)
    monkeypatch.setattr(governance_service, "get_active_workflow_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(governance_service, "effective_bool", lambda key: key in {"WORKFLOW_ENABLED", "PAPER_TRADING_ENABLED", "REQUIRE_HUMAN_APPROVAL"})

    response = check_governance(WorkflowGovernanceCheckRequest(horizon="overnight", symbols=["AMD"]))

    assert response.decision == "blocked"
    assert "horizon_not_supported_for_autonomous_workflow" in response.blockers
    assert response.limits["supported_horizons"] == ["day_trading"]


def test_strategy_selection_does_not_select_swing_strategy(monkeypatch):
    class Ranked:
        def __init__(self, strategy_key: str, horizon: str, score: float):
            self.strategy_key = strategy_key
            self.horizon = horizon
            self.strategy_score = score
            self.strategy_family = "test"
            self.model_stack_hint = []
            self.scanner_needs = []
            self.data_needs = []
            self.blockers = []
            self.warnings = []

        def model_dump(self):
            return {"strategy_key": self.strategy_key, "horizon": self.horizon, "strategy_score": self.strategy_score}

    monkeypatch.setattr(
        strategy_adapter,
        "run_strategy_ranking",
        lambda req: SimpleNamespace(
            run_id="rank_1",
            debate_run_id=None,
            top_strategy_key="swing_strategy",
            ranked_strategies=[Ranked("swing_strategy", "swing", 0.99)],
            active_strategies=[],
            recommended_research_candidate_keys=[],
        ),
    )
    monkeypatch.setattr(strategy_adapter, "save_strategy_evidence", lambda *_args, **_kwargs: None)

    out = strategy_adapter.select_strategy(market_phase="market_open", active_loop="paper_first", regime="risk_on", horizon="day_trading")

    assert out["selected_strategy_key"] is None
    assert all(row.get("horizon") == "day_trading" for row in out["ranked_strategies"])


def test_model_evidence_with_swing_horizon_is_not_selected():
    records = [
        ModelEvidenceOut(
            evidence_id="mev_swing",
            model_key="swing_model",
            model_name="Swing Model",
            model_family="test",
            asset_class="stock",
            horizon="swing",
            status="ready",
            score=0.99,
            confidence=0.9,
            rank=1,
            drift_status=None,
            training_status="trained",
            backtest_status=None,
            paper_status=None,
            qlib_artifact_id=None,
            metrics={},
            blockers=[],
            warnings=[],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
    ]

    result = evaluate_model_evidence(records)

    assert result["selected_model_keys"] == []
    assert "model_not_applicable_to_autonomous_horizon:swing_model" in result["warnings"]


def test_proof_record_with_swing_horizon_is_ignored_for_day_trading(monkeypatch):
    swing_proof = ProofRegistryRecordOut(
        proof_id="proof_swing",
        symbol="AMD",
        asset_class="stock",
        horizon="swing",
        strategy_key="stock_day_trading",
        model_key=None,
        proof_type="backtest",
        proof_status="proven",
        sample_size=200,
        win_rate=0.6,
        avg_r_multiple=0.2,
        sharpe_ratio=1.0,
        max_drawdown_r=-2,
        slippage_fail_rate=0,
        rule_violation_rate=0,
        backtest_run_id="bt_swing",
        paper_run_id=None,
        source="test",
        evidence={},
        blockers=[],
        warnings=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr(backtest_adapter, "list_proof_records", lambda limit=50: [swing_proof])
    monkeypatch.setattr(backtest_adapter, "list_artifacts", lambda limit=50: [])

    out = backtest_adapter.validate_backtest_or_proof(strategy_key="stock_day_trading", asset_class="stock", horizon="day_trading")

    assert out["proof_status"] == "backtest_required"
    assert out["proof_status"] != "proven"


def test_qlib_swing_artifact_is_not_promoted_into_workflow(monkeypatch):
    class Status:
        qlib_available = True
        qlib_version = "test"
        configured = True
        artifact_count = 1
        latest_signal_count = 0
        latest_backtest_count = 1
        latest_model_count = 0
        blockers = []
        warnings = []
        next_action = "ok"

    artifact = QlibArtifactOut(
        artifact_id="qb_swing",
        artifact_type="backtest",
        artifact_status="recorded",
        model_key=None,
        strategy_key="stock_day_trading",
        symbol="AMD",
        symbols=["AMD"],
        asset_class="stock",
        horizon="swing",
        qlib_available=True,
        qlib_version="test",
        artifact_path=None,
        metrics={},
        scores={},
        metadata={},
        blockers=[],
        warnings=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr(qlib_adapter, "get_qlib_status", lambda: Status())
    monkeypatch.setattr(qlib_adapter, "get_latest_signal_scores", lambda: None)
    monkeypatch.setattr(qlib_adapter, "list_artifacts", lambda limit=10: [artifact])

    out = qlib_adapter.qlib_research_snapshot(horizon="day_trading")

    assert out["qlib_artifact_id"] is None
    assert out["latest_backtest_artifacts"][0]["applicable_to_current_workflow"] is False


def test_strategy_evidence_evaluator_ignores_swing_records():
    record = StrategyEvidenceOut(
        evidence_id="sev_swing",
        strategy_key="swing_strategy",
        strategy_group="stock",
        asset_class="stock",
        horizon="swing",
        status="ready",
        strategy_score=0.99,
        regime_fit=0.9,
        proof_status="proven",
        selected_model_keys=[],
        scanner_needs=[],
        data_needs=[],
        metrics={},
        blockers=[],
        warnings=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    result = evaluate_strategy_evidence([record], market_context={})

    assert result["selected_strategy_key"] is None
    assert "strategy_not_applicable_to_autonomous_horizon:swing_strategy" in result["warnings"]


def test_workflow_carryforward_default_and_preserved_horizon_is_day_trading():
    state = WorkflowCarryForwardState()
    assert state.horizon == "day_trading"
    assert state.to_agent_inputs()["horizon"] == "day_trading"


def test_small_account_stage_is_before_strategy_eligibility_in_default_plan():
    from app.services.workflow_orchestrator.stage_plan import default_stage_plan

    plan = default_stage_plan()

    assert plan.index("small_account_feasibility_agent") < plan.index("strategy_eligibility_agent")


def test_workflow_runbook_does_not_expose_swing_as_autonomous_horizon():
    page = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "workflow-runbook" / "page.tsx"
    text = page.read_text(encoding="utf-8").lower()

    assert 'horizon: "day_trading"' in text
    assert "swing_trading" not in text
    assert "multi_day" not in text
    assert "overnight" not in text
    assert "position_trade" not in text
