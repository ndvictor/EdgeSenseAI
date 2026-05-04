import pytest

from app.services.model_gate_policy import ModelGateEvidence, evaluate_model_gate


@pytest.mark.unit
def test_weighted_ranker_active_without_artifact_evidence():
    decision = evaluate_model_gate(ModelGateEvidence(model_key="weighted_ranker_v1"))
    assert decision.eligible_for_active_scoring is True
    assert decision.blockers == []


@pytest.mark.unit
def test_xgboost_blocked_without_all_evidence():
    decision = evaluate_model_gate(ModelGateEvidence(model_key="xgboost_ranker"))
    assert decision.eligible_for_active_scoring is False
    assert "artifact_exists" in decision.blockers
    assert "evaluation_passed" in decision.blockers
    assert "calibration_passed" in decision.blockers
    assert "backtest_passed" in decision.blockers
    assert "owner_approved" in decision.blockers
    assert "live_scoring_allowed" in decision.blockers


@pytest.mark.unit
def test_candidate_can_only_be_eligible_with_all_gates_and_no_final_decision():
    decision = evaluate_model_gate(
        ModelGateEvidence(
            model_key="chronos_bolt_tiny",
            artifact_exists=True,
            artifact_status="registered",
            evaluation_passed=True,
            evaluation_status="passed",
            calibration_passed=True,
            calibration_status="passed",
            backtest_passed=True,
            backtest_status="passed",
            owner_approved=True,
            live_scoring_allowed=True,
            risk_gate_required=True,
            human_approval_required=True,
            final_trade_decision_allowed=False,
        )
    )
    assert decision.eligible_for_active_scoring is True
    assert decision.blockers == []


@pytest.mark.unit
def test_final_trade_decision_allowed_blocks_even_with_all_gates():
    decision = evaluate_model_gate(
        ModelGateEvidence(
            model_key="xgboost_ranker",
            artifact_exists=True,
            evaluation_passed=True,
            calibration_passed=True,
            backtest_passed=True,
            owner_approved=True,
            live_scoring_allowed=True,
            final_trade_decision_allowed=True,
        )
    )
    assert decision.eligible_for_active_scoring is False
    assert "final_trade_decision_allowed_must_be_false" in decision.blockers


@pytest.mark.unit
def test_missing_risk_or_human_gate_blocks_candidate():
    decision = evaluate_model_gate(
        ModelGateEvidence(
            model_key="qlib_research_platform",
            artifact_exists=True,
            evaluation_passed=True,
            calibration_passed=True,
            backtest_passed=True,
            owner_approved=True,
            live_scoring_allowed=True,
            risk_gate_required=False,
            human_approval_required=False,
        )
    )
    assert decision.eligible_for_active_scoring is False
    assert "risk_gate_required" in decision.blockers
    assert "human_approval_required" in decision.blockers
