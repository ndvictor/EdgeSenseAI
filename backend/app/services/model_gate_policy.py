from __future__ import annotations

from pydantic import BaseModel, Field


class ModelGateEvidence(BaseModel):
    model_key: str
    model_registered: bool = True
    artifact_exists: bool = False
    artifact_status: str = "missing"
    evaluation_passed: bool = False
    evaluation_status: str = "missing"
    calibration_passed: bool = False
    calibration_status: str = "missing"
    backtest_passed: bool = False
    backtest_status: str = "missing"
    owner_approved: bool = False
    live_scoring_allowed: bool = False
    risk_gate_required: bool = True
    human_approval_required: bool = True
    final_trade_decision_allowed: bool = False


class ModelGateDecision(BaseModel):
    model_key: str
    eligible_for_active_scoring: bool
    blockers: list[str] = Field(default_factory=list)
    next_action: str
    safety_notes: list[str]


def evaluate_model_gate(evidence: ModelGateEvidence) -> ModelGateDecision:
    blockers: list[str] = []

    if not evidence.model_registered:
        blockers.append("model_registered")

    if evidence.model_key != "weighted_ranker_v1":
        if not evidence.artifact_exists:
            blockers.append("artifact_exists")
        if not evidence.evaluation_passed:
            blockers.append("evaluation_passed")
        if not evidence.calibration_passed:
            blockers.append("calibration_passed")
        if not evidence.backtest_passed:
            blockers.append("backtest_passed")
        if not evidence.owner_approved:
            blockers.append("owner_approved")
        if not evidence.live_scoring_allowed:
            blockers.append("live_scoring_allowed")

    if evidence.final_trade_decision_allowed:
        blockers.append("final_trade_decision_allowed_must_be_false")
    if not evidence.risk_gate_required:
        blockers.append("risk_gate_required")
    if not evidence.human_approval_required:
        blockers.append("human_approval_required")

    eligible = len(blockers) == 0
    if evidence.model_key == "weighted_ranker_v1":
        eligible = not evidence.final_trade_decision_allowed and evidence.risk_gate_required and evidence.human_approval_required
        blockers = [] if eligible else blockers

    return ModelGateDecision(
        model_key=evidence.model_key,
        eligible_for_active_scoring=eligible,
        blockers=blockers,
        next_action="Eligible for active research/paper scoring." if eligible else "Resolve all promotion blockers before activation.",
        safety_notes=[
            "No model may make final trade decisions.",
            "Risk gate and human approval remain required.",
            "Eligibility is conservative if evidence is missing.",
        ],
    )
