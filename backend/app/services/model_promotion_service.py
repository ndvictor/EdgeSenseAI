from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.backtest_research_service import latest_passed_model_backtest
from app.services.model_artifact_service import latest_artifact
from app.services.model_calibration_service import latest_passed_calibration
from app.services.model_evaluation_service import latest_passed_evaluation
from app.services.model_registry_service import get_model
from app.services.research_persistence_service import (
    create_model_promotion_review,
    get_latest_approved_model_promotion,
    list_model_promotion_reviews,
)


class ModelPromotionRequest(BaseModel):
    model_key: str
    artifact_id: str | None = None
    evaluation_run_id: str | None = None
    calibration_run_id: str | None = None
    requested_status: str = "active_working_model"
    owner_approved: bool = False
    live_scoring_allowed: bool = False
    reviewed_by: str | None = None
    review_notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelPromotionDecisionRequest(BaseModel):
    reviewed_by: str | None = None
    review_notes: str | None = None
    owner_approved: bool = True
    live_scoring_allowed: bool = False


def compute_model_gate_status(model_key: str) -> dict[str, Any]:
    model = get_model(model_key)
    artifact = latest_artifact(model_key)
    artifact_exists = artifact.get("status") == "registered"
    evaluation = latest_passed_evaluation(model_key)
    evaluation_passed = evaluation.get("passed") is True and evaluation.get("status") == "passed"
    calibration = latest_passed_calibration(model_key)
    calibration_passed = calibration.get("passed") is True and calibration.get("status") == "passed"
    backtest = latest_passed_model_backtest(model_key)
    backtest_passed = backtest.get("passed") is True and backtest.get("status") == "passed"
    promotion = get_latest_approved_model_promotion(model_key, artifact.get("id") if artifact_exists else None)
    owner_approved = bool(promotion and promotion.get("owner_approved") is True and promotion.get("decision") == "approved")
    live_scoring_allowed = bool(promotion and promotion.get("live_scoring_allowed") is True)
    final_trade_decision_allowed = bool(promotion and promotion.get("final_trade_decision_allowed") is True)
    risk_gate_required = True if not promotion else bool(promotion.get("risk_gate_required", True))
    human_approval_required = True if not promotion else bool(promotion.get("human_approval_required", True))

    blockers: list[str] = []
    if not model:
        blockers.append("Model is not registered in static model registry.")
    if model_key != "weighted_ranker_v1":
        if not artifact_exists:
            blockers.append("artifact_exists")
        if not evaluation_passed:
            blockers.append("evaluation_passed")
        if not calibration_passed:
            blockers.append("calibration_passed")
        if not backtest_passed:
            blockers.append("backtest_passed")
        if not owner_approved:
            blockers.append("owner_approved")
        if not live_scoring_allowed:
            blockers.append("live_scoring_allowed")
    if final_trade_decision_allowed:
        blockers.append("final_trade_decision_allowed_must_be_false")
    if not risk_gate_required:
        blockers.append("risk_gate_required")
    if not human_approval_required:
        blockers.append("human_approval_required")

    eligible = len(blockers) == 0
    if model_key == "weighted_ranker_v1":
        eligible = True and not final_trade_decision_allowed and risk_gate_required and human_approval_required
        blockers = [] if eligible else blockers

    return {
        "model_key": model_key,
        "artifact_exists": artifact_exists,
        "artifact_status": artifact.get("status", "missing"),
        "evaluation_passed": evaluation_passed,
        "evaluation_status": evaluation.get("status", "missing"),
        "calibration_passed": calibration_passed,
        "calibration_status": calibration.get("status", "missing"),
        "backtest_passed": backtest_passed,
        "backtest_status": backtest.get("status", "missing"),
        "owner_approved": owner_approved,
        "live_scoring_allowed": live_scoring_allowed,
        "risk_gate_required": risk_gate_required,
        "human_approval_required": human_approval_required,
        "final_trade_decision_allowed": final_trade_decision_allowed,
        "eligible_for_active_scoring": eligible,
        "blockers": blockers,
        "next_action": "Eligible for active research/paper scoring." if eligible else "Resolve all promotion blockers before activation.",
        "safety_notes": ["No model may make final trade decisions.", "Risk gate and human approval remain required.", "Eligibility is conservative if DB evidence is missing."],
    }


def get_model_promotion_eligibility(model_key: str) -> dict[str, Any]:
    return compute_model_gate_status(model_key)


def request_model_promotion(request: ModelPromotionRequest) -> dict[str, Any]:
    gate = compute_model_gate_status(request.model_key)
    payload = request.model_dump()
    payload["decision"] = "approved" if request.owner_approved and not gate["blockers"] else "pending"
    payload["risk_gate_required"] = True
    payload["human_approval_required"] = True
    payload["final_trade_decision_allowed"] = False
    if gate["blockers"]:
        payload["metadata"] = {**payload.get("metadata", {}), "promotion_blockers": gate["blockers"]}
    return create_model_promotion_review(payload)


def list_promotion_reviews(model_key: str | None = None) -> dict[str, Any]:
    return {"data_source": "postgres_or_empty", "reviews": list_model_promotion_reviews(model_key)}


def approve_model_promotion(review_id: str, request: ModelPromotionDecisionRequest) -> dict[str, Any]:
    # Append a new immutable approved review record instead of mutating evidence in place.
    return create_model_promotion_review({
        "id": f"{review_id}-approved",
        "model_key": review_id.split(":")[0] if ":" in review_id else "unknown",
        "requested_status": "active_working_model",
        "decision": "approved",
        "owner_approved": request.owner_approved,
        "live_scoring_allowed": request.live_scoring_allowed,
        "reviewed_by": request.reviewed_by,
        "review_notes": request.review_notes,
        "metadata": {"source_review_id": review_id, "note": "Approval API is evidence-only and does not directly activate a model."},
    })


def reject_model_promotion(review_id: str, request: ModelPromotionDecisionRequest) -> dict[str, Any]:
    return create_model_promotion_review({
        "id": f"{review_id}-rejected",
        "model_key": review_id.split(":")[0] if ":" in review_id else "unknown",
        "requested_status": "active_working_model",
        "decision": "rejected",
        "owner_approved": False,
        "live_scoring_allowed": False,
        "reviewed_by": request.reviewed_by,
        "review_notes": request.review_notes,
        "metadata": {"source_review_id": review_id},
    })
