from __future__ import annotations

from app.services.model_evidence.models import ModelEvidenceOut
from app.services.model_evidence.service import evaluate_model_evidence
from app.services.proof_registry.service import evaluate_proof_status
from app.services.strategy_evidence.models import StrategyEvidenceOut
from app.services.strategy_evidence.service import evaluate_strategy_evidence


def test_proof_evaluator_returns_proven_only_when_thresholds_met():
    decision = evaluate_proof_status(
        {
            "strategy_key": "stock_day_trading",
            "sample_size": 120,
            "avg_r_multiple": 0.12,
            "max_drawdown_r": -4.5,
            "rule_violation_rate": 0,
        }
    )

    assert decision["proof_status"] == "proven"


def test_missing_proof_returns_backtest_required_or_proof_required():
    strategy_decision = evaluate_proof_status({"strategy_key": "stock_day_trading"})
    empty_decision = evaluate_proof_status({})

    assert strategy_decision["proof_status"] == "backtest_required"
    assert empty_decision["proof_status"] == "proof_required"


def test_rule_violations_block_proof():
    decision = evaluate_proof_status(
        {
            "strategy_key": "stock_day_trading",
            "sample_size": 200,
            "avg_r_multiple": 0.3,
            "max_drawdown_r": -2,
            "rule_violation_rate": 0.01,
        }
    )

    assert decision["proof_status"] == "blocked"
    assert "rule_violation_rate_positive" in decision["blockers"]


def _model(model_key: str, status: str, **kwargs) -> ModelEvidenceOut:
    return ModelEvidenceOut(
        evidence_id=f"mev_{model_key}",
        model_key=model_key,
        model_name=model_key,
        model_family="test",
        asset_class="stock",
        horizon="day_trading",
        status=status,
        score=kwargs.get("score"),
        confidence=kwargs.get("confidence"),
        rank=kwargs.get("rank"),
        drift_status=kwargs.get("drift_status"),
        training_status=kwargs.get("training_status"),
        backtest_status=kwargs.get("backtest_status"),
        paper_status=kwargs.get("paper_status"),
        qlib_artifact_id=kwargs.get("qlib_artifact_id"),
        metrics={},
        blockers=kwargs.get("blockers", []),
        warnings=kwargs.get("warnings", []),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_model_evidence_evaluator_separates_ready_blocked_not_trained():
    result = evaluate_model_evidence(
        [
            _model("ready_model", "ready", score=0.9, rank=1, training_status="trained"),
            _model("blocked_model", "blocked", blockers=["drift_blocked"]),
            _model("new_model", "not_trained", training_status="not_trained"),
        ]
    )

    assert result["selected_model_keys"] == ["ready_model"]
    assert result["blocked_models"] == ["blocked_model"]
    assert result["not_trained_models"] == ["new_model"]


def _strategy(strategy_key: str, status: str, **kwargs) -> StrategyEvidenceOut:
    return StrategyEvidenceOut(
        evidence_id=f"sev_{strategy_key}",
        strategy_key=strategy_key,
        strategy_group="stock",
        asset_class="stock",
        horizon="day_trading",
        status=status,
        strategy_score=kwargs.get("strategy_score"),
        regime_fit=kwargs.get("regime_fit"),
        proof_status=kwargs.get("proof_status"),
        selected_model_keys=kwargs.get("selected_model_keys", []),
        scanner_needs=[],
        data_needs=[],
        metrics={},
        blockers=kwargs.get("blockers", []),
        warnings=kwargs.get("warnings", []),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_strategy_evidence_evaluator_ranks_ready_and_blocks_invalid():
    result = evaluate_strategy_evidence(
        [
            _strategy("weak", "ready", strategy_score=0.4, regime_fit=0.5),
            _strategy("strong", "ready", strategy_score=0.9, regime_fit=0.7),
            _strategy("bad", "blocked", blockers=["proof_blocked"]),
        ],
        market_context={"regime": "risk_on"},
    )

    assert result["selected_strategy_key"] == "strong"
    assert [x["strategy_key"] for x in result["ranked_strategies"]][:2] == ["strong", "weak"]
    assert "proof_blocked" in result["blockers"]
