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
    assert payload["market_data_provider_priority"]


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "edgesenseai_backend_requests_total" in response.text


def test_data_sources_status_contract():
    response = client.get("/api/data-sources/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_sources"] >= 8
    keys = {source["key"] for source in payload["sources"]}
    assert "yfinance" in keys
    assert "alpaca" in keys
    assert "postgresql" in keys
    assert "redis" in keys


def test_market_data_snapshot_contract():
    response = client.get("/api/market-data/snapshot/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert "data_quality" in payload
    assert "provider_statuses" in payload or payload["data_quality"] in {"real", "unavailable", "not_configured"}


def test_market_data_history_contract():
    response = client.get("/api/market-data/history/AMD?period=5d&interval=1d")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert payload["period"] == "5d"
    assert payload["interval"] == "1d"
    assert "data" in payload


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


def test_model_lab_workflow_contract():
    response = client.post(
        "/api/model-lab/run",
        json={
            "data_source": "mock",
            "model": "xgboost_ranker",
            "symbols": ["AMD", "NVDA", "BTC-USD"],
            "train_split_percent": 70,
            "test_split_percent": 30,
            "feature_set": "prototype_v1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_status"] == "completed"
    assert payload["split"]["total_rows"] == 3
    assert payload["split"]["train_rows"] == 2
    assert payload["features"]
    assert payload["ranker_result"]["scores"]
    assert payload["ranker_result"]["rows_scored"] == 3


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


def test_market_regime_contract():
    response = client.get("/api/market-regime")
    assert response.status_code == 200
    payload = response.json()
    assert payload["regime_state"]
    assert 0 <= payload["confidence"] <= 1
    assert payload["allowed_strategies"]
    assert payload["blocked_strategies"]
    assert payload["factors"]


def test_backtesting_contract():
    response = client.get("/api/backtesting/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "prototype_contract"
    assert payload["profiles"]
    assert payload["profiles"][0]["metrics"]


def test_journal_contract():
    response = client.get("/api/journal/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "prototype_contract"
    assert payload["total_entries"] >= 1
    assert payload["entries"]
    assert payload["next_steps"]


def test_data_quality_contract():
    response = client.get("/api/data-quality/AMD?asset_class=stock&source=mock")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AMD"
    assert payload["quality_status"] in {"pass", "warn", "fail"}
    assert payload["data_source"] in {"demo", "placeholder", "source_backed"}
    assert "missing_fields" in payload
    assert "checked_at" in payload


def test_feature_store_run_contract():
    response = client.post(
        "/api/feature-store/run",
        json={"symbol": "AMD", "asset_class": "stock", "horizon": "swing", "source": "mock"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["storage_mode"] == "in_memory"
    assert payload["row"]["ticker"] == "AMD"
    assert payload["row"]["feature_version"] == "foundation_v1"
    assert payload["quality_report"]["quality_status"] in {"pass", "warn", "fail"}


def test_model_runs_registry_and_run_contract():
    registry_response = client.get("/api/model-runs/registry")
    assert registry_response.status_code == 200
    registry = registry_response.json()
    assert registry["available_model_count"] >= 1
    assert registry["placeholder_model_count"] >= 1
    model_keys = {model["key"] for model in registry["models"]}
    assert "weighted_ranker" in model_keys
    assert "finbert_sentiment" in model_keys

    run_response = client.post(
        "/api/model-runs/run",
        json={"symbols": ["AMD"], "asset_class": "stock", "horizon": "swing", "source": "mock"},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "completed"
    assert run["feature_rows"]
    assert run["plan"]["models"]
    assert any(result["model"] == "weighted_ranker" for result in run["results"])


def test_foundation_routes_preserve_existing_agent_endpoints():
    assert client.post("/api/signal-agents/run", json={"symbols": ["AMD"], "agents": ["technical"]}).status_code == 200
    assert client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["data_quality"]["status"] == "configured"
    assert payload["feature_store"]["status"] == "configured"
    assert payload["model_orchestrator"]["status"] == "configured"


def test_llm_gateway_contracts_and_dry_run_safety():
    assert client.get("/api/llm-gateway/status").status_code == 200
    providers = client.get("/api/llm-gateway/providers")
    assert providers.status_code == 200
    provider_names = {provider["provider"] for provider in providers.json()}
    assert {"openai", "anthropic", "bedrock", "local"}.issubset(provider_names)
    assert client.get("/api/llm-gateway/models").status_code == 200
    assert client.get("/api/llm-gateway/routing-rules").status_code == 200
    assert client.get("/api/llm-gateway/usage").status_code == 200
    costs = client.get("/api/llm-gateway/costs")
    assert costs.status_code == 200
    assert costs.json()["data_source"] == "placeholder"
    assert client.get("/api/llm-gateway/agent-model-map").status_code == 200

    estimate = client.post("/api/llm-gateway/estimate", json={"model": "gpt-4o-mini", "prompt_tokens": 1000, "completion_tokens": 500})
    assert estimate.status_code == 200
    assert estimate.json()["pricing_source"] == "placeholder_estimate"

    test_call = client.post(
        "/api/llm-gateway/test-call",
        json={"provider": "openai", "model": "gpt-4o-mini", "prompt": "safe test", "allow_paid_call": False},
    )
    assert test_call.status_code == 200
    payload = test_call.json()
    assert payload["dry_run"] is True
    assert payload["paid_call_attempted"] is False

    summary = client.get("/api/ai-ops/summary").json()
    assert summary["llm_gateway"]["data_source"] == "placeholder"
    assert "gateway_status" in summary["llm_gateway"]
