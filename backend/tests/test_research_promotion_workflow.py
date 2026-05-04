from fastapi.testclient import TestClient

from app.main import app
from app.services.backtest_research_service import ModelBacktestRunRequest, create_model_backtest_request
from app.services.model_calibration_service import ModelCalibrationRunRequest, create_calibration
from app.services.model_evaluation_service import ModelEvaluationRunRequest, create_evaluation
from app.services.model_promotion_service import compute_model_gate_status
from app.services.model_registry_service import is_model_eligible_for_active_scoring

client = TestClient(app)


def test_xgboost_default_remains_not_active():
    status = compute_model_gate_status("xgboost_ranker")
    assert status["eligible_for_active_scoring"] is False
    assert "artifact_exists" in status["blockers"]
    assert "evaluation_passed" in status["blockers"]
    assert "calibration_passed" in status["blockers"]
    assert "backtest_passed" in status["blockers"]
    assert "owner_approved" in status["blockers"]
    assert is_model_eligible_for_active_scoring("xgboost_ranker") is False


def test_weighted_ranker_remains_active_baseline():
    status = compute_model_gate_status("weighted_ranker_v1")
    assert status["eligible_for_active_scoring"] is True
    assert status["final_trade_decision_allowed"] is False
    assert status["risk_gate_required"] is True
    assert status["human_approval_required"] is True


def test_evaluation_missing_metrics_cannot_pass():
    result = create_evaluation(ModelEvaluationRunRequest(model_key="xgboost_ranker", metrics={}))
    record = result["record"]
    assert record["status"] == "insufficient_data"
    assert record["passed"] is False
    assert "No evaluation metrics provided." in record["failure_reasons"]


def test_calibration_missing_metrics_cannot_pass():
    result = create_calibration(ModelCalibrationRunRequest(model_key="xgboost_ranker", metrics={}))
    record = result["record"]
    assert record["status"] == "insufficient_data"
    assert record["passed"] is False
    assert "No calibration metrics provided." in record["failure_reasons"]


def test_model_backtest_without_symbols_is_blocked():
    result = create_model_backtest_request(ModelBacktestRunRequest(model_key="xgboost_ranker", symbols=[]))
    record = result["record"]
    assert record["status"] == "blocked"
    assert record["passed"] is False
    assert "No explicit symbols or candidate universe provided." in record["failure_reasons"]


def test_model_promotion_status_api_blocks_xgboost_without_evidence():
    response = client.get("/api/model-promotion/status/xgboost_ranker")
    assert response.status_code == 200
    payload = response.json()
    assert payload["eligible_for_active_scoring"] is False
    assert payload["final_trade_decision_allowed"] is False
    assert "artifact_exists" in payload["blockers"]
    assert "evaluation_passed" in payload["blockers"]
    assert "calibration_passed" in payload["blockers"]


def test_research_backtest_api_blocks_missing_symbols():
    response = client.post("/api/backtesting/research/model-backtests", json={"model_key": "xgboost_ranker", "symbols": []})
    assert response.status_code == 200
    payload = response.json()["record"]
    assert payload["status"] == "blocked"
    assert payload["passed"] is False


def test_research_summary_api_available():
    response = client.get("/api/backtesting/research/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "model_backtest_count" in payload
    assert "safety_notes" in payload
