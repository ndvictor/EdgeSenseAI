import pytest

from app.services import model_promotion_service


@pytest.mark.service
def test_promotion_service_uses_fake_evidence_without_fastapi_or_db(monkeypatch):
    monkeypatch.setattr(model_promotion_service, "get_model", lambda key: {"model_key": key})
    monkeypatch.setattr(model_promotion_service, "latest_artifact", lambda key: {"id": "artifact-1", "status": "registered"})
    monkeypatch.setattr(model_promotion_service, "latest_passed_evaluation", lambda key: {"id": "eval-1", "status": "passed", "passed": True})
    monkeypatch.setattr(model_promotion_service, "latest_passed_calibration", lambda key: {"id": "calib-1", "status": "passed", "passed": True})
    monkeypatch.setattr(model_promotion_service, "latest_passed_model_backtest", lambda key: {"id": "bt-1", "status": "passed", "passed": True})
    monkeypatch.setattr(
        model_promotion_service,
        "get_latest_approved_model_promotion",
        lambda key, artifact_id=None: {
            "id": "promo-1",
            "decision": "approved",
            "owner_approved": True,
            "live_scoring_allowed": True,
            "final_trade_decision_allowed": False,
            "risk_gate_required": True,
            "human_approval_required": True,
        },
    )

    status = model_promotion_service.compute_model_gate_status("xgboost_ranker")
    assert status["eligible_for_active_scoring"] is True
    assert status["blockers"] == []
    assert status["final_trade_decision_allowed"] is False


@pytest.mark.service
def test_promotion_service_blocks_fake_final_decision_even_with_evidence(monkeypatch):
    monkeypatch.setattr(model_promotion_service, "get_model", lambda key: {"model_key": key})
    monkeypatch.setattr(model_promotion_service, "latest_artifact", lambda key: {"id": "artifact-1", "status": "registered"})
    monkeypatch.setattr(model_promotion_service, "latest_passed_evaluation", lambda key: {"id": "eval-1", "status": "passed", "passed": True})
    monkeypatch.setattr(model_promotion_service, "latest_passed_calibration", lambda key: {"id": "calib-1", "status": "passed", "passed": True})
    monkeypatch.setattr(model_promotion_service, "latest_passed_model_backtest", lambda key: {"id": "bt-1", "status": "passed", "passed": True})
    monkeypatch.setattr(
        model_promotion_service,
        "get_latest_approved_model_promotion",
        lambda key, artifact_id=None: {
            "id": "promo-1",
            "decision": "approved",
            "owner_approved": True,
            "live_scoring_allowed": True,
            "final_trade_decision_allowed": True,
            "risk_gate_required": True,
            "human_approval_required": True,
        },
    )

    status = model_promotion_service.compute_model_gate_status("xgboost_ranker")
    assert status["eligible_for_active_scoring"] is False
    assert "final_trade_decision_allowed_must_be_false" in status["blockers"]
