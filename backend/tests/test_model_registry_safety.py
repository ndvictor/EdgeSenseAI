from fastapi.testclient import TestClient

from app.main import app
from app.services.model_registry_service import (
    get_model,
    get_model_registry,
    get_model_selection_summary,
    is_model_eligible_for_active_scoring,
)
from app.services.model_selection_service import ModelSelectionRequest, run_model_selection

client = TestClient(app)


def test_weighted_ranker_active_and_eligible():
    model = get_model("weighted_ranker_v1")
    assert model is not None
    assert model.group == "active_working_models"
    assert model.status == "active"
    assert model.allowed_for_live_scoring is True
    assert model.allowed_for_final_trade_decision is False
    assert model.requires_risk_gate is True
    assert model.requires_human_approval is True
    assert is_model_eligible_for_active_scoring("weighted_ranker_v1") is True


def test_xgboost_not_trained_and_not_eligible_by_default():
    model = get_model("xgboost_ranker")
    assert model is not None
    assert model.group == "untrained_internal_models"
    assert model.status == "not_trained"
    assert model.trained_artifact_exists is False
    assert model.evaluation_passed is False
    assert model.calibration_passed is False
    assert model.owner_approved is False
    assert model.allowed_for_live_scoring is False
    assert is_model_eligible_for_active_scoring("xgboost_ranker") is False


def test_candidate_models_visible_but_not_eligible():
    registry = get_model_registry()
    candidates = registry["groups"]["candidate_open_source_models"] + registry["groups"]["candidate_pretrained_models"] + registry["groups"]["candidate_statistical_models"]
    assert candidates
    for model in candidates:
        assert model["allowed_for_research_backtesting"] is True
        assert model["allowed_for_live_scoring"] is False
        assert model["allowed_for_final_trade_decision"] is False
        assert is_model_eligible_for_active_scoring(model["model_key"]) is False


def test_no_model_can_make_final_trade_decision():
    registry = get_model_registry()
    assert registry["final_trade_decision_models_count"] == 0
    for model in registry["models"]:
        assert model["allowed_for_final_trade_decision"] is False


def test_model_selection_skips_xgboost_and_candidates():
    response = run_model_selection(ModelSelectionRequest(
        strategy_key="stock_swing",
        market_phase="market_open",
        active_loop="fast_scanning_loop",
        regime="momentum",
        horizon="swing",
        data_sources_available=["price", "volume", "history", "candles", "quote", "bid_ask", "regime_detection", "account_risk_config"],
    ))
    selected_scoring_keys = {model.model_key for model in response.selected_scoring_models}
    skipped_keys = {model.model_key for model in response.skipped_models}
    assert "weighted_ranker_v1" in selected_scoring_keys
    assert "xgboost_ranker" not in selected_scoring_keys
    assert "xgboost_ranker" in skipped_keys
    assert response.meta_model_weights.xgboost_ranker_weight == 0.0


def test_model_selection_summary_product_truth():
    summary = get_model_selection_summary()
    assert summary["product_truth"]["weighted_ranker_v1_active_baseline"] is True
    assert summary["product_truth"]["xgboost_ranker_not_active"] is True
    assert summary["product_truth"]["candidate_models_research_only"] is True
    assert summary["product_truth"]["no_model_final_trade_decision"] is True


def test_model_registry_api_groupings():
    response = client.get("/api/model-registry")
    assert response.status_code == 200
    payload = response.json()
    assert payload["active_model_count"] >= 1
    assert payload["candidate_model_count"] >= 1
    assert payload["untrained_internal_model_count"] >= 1
    assert payload["final_trade_decision_models_count"] == 0


def test_xgboost_eligibility_api():
    response = client.get("/api/model-registry/xgboost_ranker/eligibility")
    assert response.status_code == 200
    payload = response.json()
    assert payload["eligible_for_active_scoring"] is False
    assert "trained_artifact_exists" in payload["missing_requirements"]
    assert "evaluation_passed" in payload["missing_requirements"]
    assert "calibration_passed" in payload["missing_requirements"]
    assert "owner_approved" in payload["missing_requirements"]


def test_model_selection_endpoint_does_not_select_xgboost():
    response = client.post("/api/model-selection/run", json={
        "strategy_key": "stock_swing",
        "market_phase": "market_open",
        "active_loop": "fast_scanning_loop",
        "regime": "momentum",
        "horizon": "swing",
        "data_sources_available": ["price", "volume", "history", "candles", "quote", "bid_ask", "regime_detection", "account_risk_config"],
    })
    assert response.status_code == 200
    payload = response.json()
    selected_scoring = {model["model_key"] for model in payload["selected_scoring_models"]}
    skipped = {model["model_key"] for model in payload["skipped_models"]}
    assert "weighted_ranker_v1" in selected_scoring
    assert "xgboost_ranker" not in selected_scoring
    assert "xgboost_ranker" in skipped
