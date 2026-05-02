from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["backend_port"] == 8900
    assert payload["frontend_port"] == 3900


def test_command_center_contains_actionable_top_action():
    response = client.get("/api/command-center")
    assert response.status_code == 200
    payload = response.json()

    top_action = payload["top_action"]
    assert top_action["symbol"]
    assert top_action["action"] in {"buy", "watch", "avoid"}
    assert 0 <= top_action["confidence"] <= 1
    assert top_action["price_plan"]["current_price"] > 0
    assert top_action["price_plan"]["buy_zone_low"] > 0
    assert top_action["price_plan"]["buy_zone_high"] >= top_action["price_plan"]["buy_zone_low"]
    assert top_action["price_plan"]["stop_loss"] > 0
    assert top_action["price_plan"]["target_price"] > top_action["price_plan"]["current_price"]
    assert top_action["risk_plan"]["reward_risk_ratio"] > 0
    assert top_action["model_votes"]
    assert top_action["invalidation_rules"]
    assert top_action["research_only"] is True
    assert top_action["execution_enabled"] is False


def test_model_status_contract():
    response = client.get("/api/models/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["data_mode"] == "synthetic_prototype"
    assert payload["live_prediction_enabled"] is False
    assert len(payload["models"]) >= 5
    model_names = {model["name"] for model in payload["models"]}
    assert "ARIMAX Directional Forecast" in model_names
    assert "Kalman Trend Filter" in model_names
    assert "GARCH Volatility Fit" in model_names
    assert "HMM Regime Filter" in model_names
    assert "XGBoost Meta-Ranker" in model_names


def test_live_watchlist_contract():
    response = client.get("/api/live-watchlist/latest")
    assert response.status_code == 200
    payload = response.json()

    assert payload["live_trading_enabled"] is False
    assert payload["execution_enabled"] is False
    assert payload["summary"]["triggered_now"] >= 0
    assert payload["candidates"]


def test_edge_signals_contract():
    response = client.get("/api/edge-signals/latest")
    assert response.status_code == 200
    payload = response.json()

    assert payload["alerts_enabled"] is True
    assert payload["signals"]
    for signal in payload["signals"]:
        assert 0 <= signal["confidence"] <= 1
        assert signal["recommended_action"]
        assert signal["risk_factors"]


def test_market_snapshots_contract():
    response = client.get("/api/market/snapshots")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["current_price"] > 0
    assert payload[0]["data_mode"] == "synthetic_prototype"


def test_features_contract():
    response = client.get("/api/features/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert 0 <= payload["composite_feature_score"] <= 100
    assert payload["notes"]


def test_model_pipeline_contract():
    response = client.get("/api/model-pipeline/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert payload["features"]["symbol"] == "AMD"
    assert payload["ranker_score"] >= 0
    assert payload["pipeline_notes"]


def test_account_feasibility_contract():
    response = client.get("/api/account-feasibility/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert payload["max_position_size_dollars"] > 0
    assert payload["max_risk_dollars"] > 0
    assert payload["suggested_expression"]


def test_risk_check_contract():
    response = client.get("/api/risk-check/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["reward_risk_ratio"] > 0
    assert payload["max_dollar_risk"] > 0
    assert payload["risk_status"] in {"passed", "blocked_or_review"}
