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
    weighted = next(result for result in run["model_outputs"] if result.get("model_name") == "weighted_ranker_v1")
    assert weighted["status"] == "completed"
    assert 0 <= weighted["prediction_score"] <= 1
    assert 0 <= weighted["probability_score"] <= 1
    assert weighted["pricing"] is None
    assert weighted["feature_contributions"]
    xgboost_outputs = [result for result in run["model_outputs"] if result.get("model") == "xgboost_ranker"]
    assert xgboost_outputs
    assert xgboost_outputs[0]["status"] in {"not_trained", "not_available"}
    assert all(result["status"] != "completed" for result in run["placeholder_models"])


def test_foundation_routes_preserve_existing_agent_endpoints():
    assert client.post("/api/signal-agents/run", json={"symbols": ["AMD"], "agents": ["technical"]}).status_code == 200
    assert client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["data_quality"]["status"] == "configured"
    assert payload["feature_store"]["status"] == "configured"
    assert payload["model_orchestrator"]["status"] == "configured"


def test_llm_gateway_contracts_and_dry_run_safety(monkeypatch):
    from app.core.settings import settings

    monkeypatch.setattr(settings, "llm_gateway_enable_paid_tests", False)
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

    blocked_paid = client.post(
        "/api/llm-gateway/providers/test",
        json={"provider": "openai", "model": "gpt-4o-mini", "prompt": "safe paid gate test", "allow_paid_call": True},
    )
    assert blocked_paid.status_code == 200
    blocked_payload = blocked_paid.json()
    assert blocked_payload["dry_run"] is True
    assert blocked_payload["status"] == "blocked_by_gateway_policy"

    summary = client.get("/api/ai-ops/summary").json()
    assert summary["llm_gateway"]["data_source"] == "placeholder"
    assert "gateway_status" in summary["llm_gateway"]


def test_edge_radar_records_dry_run_llm_usage():
    response = client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"})
    assert response.status_code == 200
    usage = client.get("/api/llm-gateway/usage")
    assert usage.status_code == 200
    records = usage.json()
    assert any(record["agent"] in {"Risk Manager Agent", "Portfolio Manager Agent", "Cost Controller Agent"} for record in records)
    assert all(record["dry_run"] is True for record in records if record["agent"] in {"Risk Manager Agent", "Portfolio Manager Agent", "Cost Controller Agent"})


def test_agent_strategy_rules_scanner_and_auto_run_contracts():
    agents = client.get("/api/agents/registry")
    assert agents.status_code == 200
    agent_payload = agents.json()
    assert len(agent_payload) >= 14
    assert any(agent["agent_key"] == "data_quality" for agent in agent_payload)

    strategies = client.get("/api/strategies")
    assert strategies.status_code == 200
    strategy_payload = strategies.json()
    assert len(strategy_payload) >= 9
    assert any(strategy["strategy_key"] == "stock_day_trading" for strategy in strategy_payload)

    stock_day = client.get("/api/strategies/stock_day_trading")
    assert stock_day.status_code == 200
    assert stock_day.json()["live_trading_supported"] is False

    rules = client.get("/api/edge-signal-rules")
    assert rules.status_code == 200
    assert any(rule["signal_key"] == "rvol_spike" for rule in rules.json())

    scan = client.post(
        "/api/market-scanner/scan",
        json={"strategy_key": "stock_day_trading", "symbols": ["AMD"], "data_source": "mock", "auto_run": True},
    )
    assert scan.status_code == 200
    scan_payload = scan.json()
    assert scan_payload["strategy_key"] == "stock_day_trading"
    assert scan_payload["recommended_workflow_key"]
    assert scan_payload["safety_state"]["live_trading_enabled"] is False
    assert scan_payload["safety_state"]["require_human_approval"] is True

    auto_status = client.get("/api/auto-run/status")
    assert auto_status.status_code == 200
    assert auto_status.json()["live_trading_enabled"] is False

    updated = client.put("/api/auto-run/status", json={"auto_run_enabled": True, "live_trading_enabled": True})
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["auto_run_enabled"] is True
    assert updated_payload["live_trading_enabled"] is False

    assert client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    assert client.get("/api/llm-gateway/status").status_code == 200
    assert client.get("/api/model-runs/registry").status_code == 200

    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["strategy_registry_count"] >= 9
    assert summary_payload["available_agents_count"] >= 1
    assert summary_payload["market_scanner_status"] == "configured"


def test_market_scanner_records_manual_scan_runs():
    response = client.post(
        "/api/market-scanner/scan",
        json={"strategy_key": "stock_day_trading", "symbols": ["AMD"], "data_source": "mock", "auto_run": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"]
    assert payload["trigger_type"] == "manual"

    runs = client.get("/api/market-scanner/runs")
    assert runs.status_code == 200
    assert any(run["run_id"] == payload["run_id"] for run in runs.json())

    latest = client.get("/api/market-scanner/runs/latest")
    assert latest.status_code == 200
    assert latest.json()["run_id"] == payload["run_id"]

    by_id = client.get(f"/api/market-scanner/runs/{payload['run_id']}")
    assert by_id.status_code == 200
    assert by_id.json()["strategy_key"] == "stock_day_trading"


def test_scheduled_market_scan_respects_auto_run_controls():
    disabled = client.put("/api/auto-run/status", json={"auto_run_enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["live_trading_enabled"] is False

    skipped = client.post("/api/market-scanner/run-scheduled-once")
    assert skipped.status_code == 200
    skipped_payload = skipped.json()
    assert skipped_payload["status"] == "skipped"
    assert skipped_payload["scan_run"]["trigger_type"] == "scheduled"

    enabled = client.put("/api/auto-run/status", json={"auto_run_enabled": True, "live_trading_enabled": True})
    assert enabled.status_code == 200
    enabled_payload = enabled.json()
    assert enabled_payload["auto_run_enabled"] is True
    assert enabled_payload["live_trading_enabled"] is False

    scheduled = client.post("/api/market-scanner/run-scheduled-once")
    assert scheduled.status_code == 200
    scheduled_payload = scheduled.json()
    assert scheduled_payload["status"] == "completed"
    assert scheduled_payload["scan"]["trigger_type"] == "scheduled"
    assert scheduled_payload["scan"]["safety_state"]["live_trading_enabled"] is False

    latest = client.get("/api/market-scanner/runs/latest")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["trigger_type"] == "scheduled"
    assert latest_payload["safety_state"]["live_trading_enabled"] is False

    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["latest_market_scan"]
    assert summary_payload["scan_runs_today"] >= 1
    assert summary_payload["last_scheduled_scan_status"] in {"completed", "skipped"}
    assert summary_payload["scanner_status"] == "configured"


def test_strategy_workflow_run_contract_and_scanner_trigger_safety():
    manual = client.post(
        "/api/strategy-workflows/run",
        json={
            "strategy_key": "stock_day_trading",
            "symbol": "AMD",
            "asset_class": "stock",
            "horizon": "day_trade",
            "matched_signal_key": "rvol_spike",
            "trigger_type": "manual",
            "data_source": "mock",
        },
    )
    assert manual.status_code == 200
    manual_payload = manual.json()
    assert manual_payload["workflow_run_id"]
    assert manual_payload["approval_required"] is True
    assert manual_payload["live_trading_allowed"] is False
    assert manual_payload["recommendation"]["paper_only"] is True

    runs = client.get("/api/strategy-workflows/runs")
    assert runs.status_code == 200
    assert any(run["workflow_run_id"] == manual_payload["workflow_run_id"] for run in runs.json())

    latest = client.get("/api/strategy-workflows/runs/latest")
    assert latest.status_code == 200
    assert latest.json()["workflow_run_id"] == manual_payload["workflow_run_id"]

    client.put("/api/auto-run/status", json={"auto_run_enabled": False})
    skipped = client.post("/api/market-scanner/run-scheduled-once")
    assert skipped.status_code == 200
    assert skipped.json()["scan_run"]["workflow_trigger_status"] == "not_triggered"

    scan = client.post(
        "/api/market-scanner/scan",
        json={
            "strategy_key": "stock_day_trading",
            "symbols": ["COOL"],
            "data_source": "mock",
            "auto_run": False,
            "trigger_workflow": True,
        },
    )
    assert scan.status_code == 200
    scan_payload = scan.json()
    assert "workflow_trigger_status" in scan_payload
    assert scan_payload["workflow_trigger_status"] == "triggered"
    assert scan_payload["workflow_run_id"]
    assert scan_payload["safety_state"]["live_trading_enabled"] is False

    duplicate_scan = client.post(
        "/api/market-scanner/scan",
        json={
            "strategy_key": "stock_day_trading",
            "symbols": ["COOL"],
            "data_source": "mock",
            "auto_run": False,
            "trigger_workflow": True,
        },
    )
    assert duplicate_scan.status_code == 200
    duplicate_payload = duplicate_scan.json()
    assert duplicate_payload["workflow_trigger_status"] == "skipped_cooldown_active"
    assert duplicate_payload["workflow_run_id"] is None
    assert duplicate_payload["cooldown_remaining_seconds"] > 0

    client.put("/api/auto-run/status", json={"auto_run_enabled": True})
    scheduled = client.post("/api/market-scanner/run-scheduled-once")
    assert scheduled.status_code == 200
    scheduled_payload = scheduled.json()
    if scheduled_payload.get("scan", {}).get("should_trigger_workflow"):
        assert scheduled_payload["scan"]["workflow_trigger_status"] in {"triggered", "skipped_cooldown_active"}
        if scheduled_payload["scan"]["workflow_trigger_status"] == "triggered":
            assert scheduled_payload["scan"]["workflow_run_id"]
        else:
            assert scheduled_payload["scan"]["cooldown_remaining_seconds"] > 0

    assert client.post("/api/market-scanner/scan", json={"strategy_key": "stock_day_trading", "symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    assert client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    assert client.get("/api/llm-gateway/status").status_code == 200


def test_memory_and_persistence_fallback_contracts():
    from app.services.embedding_service import embed_text

    first = embed_text("AMD momentum workflow memory")
    second = embed_text("AMD momentum workflow memory")
    assert first.embedding == second.embedding
    assert first.provider == "placeholder"

    created = client.post(
        "/api/memory",
        json={
            "memory_type": "workflow_summary",
            "title": "AMD workflow memory",
            "content": "Weighted ranker completed for AMD in paper research mode.",
            "summary": "AMD paper workflow summary",
            "symbol": "AMD",
            "strategy_key": "stock_day_trading",
            "tags": ["test", "workflow"],
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["memory_id"]
    assert payload["embedding_model"] == "placeholder-hash-embedding"

    recent = client.get("/api/memory/recent")
    assert recent.status_code == 200
    assert any(row["memory_id"] == payload["memory_id"] for row in recent.json())

    search = client.post("/api/memory/search", json={"query": "AMD weighted ranker", "symbol": "AMD"})
    assert search.status_code == 200
    search_payload = search.json()
    assert search_payload["data_source"] in {"postgres_pgvector", "postgres_keyword_fallback", "in_memory_fallback"}
    assert search_payload["results"]

    assert client.get(f"/api/memory/{payload['memory_id']}").status_code == 200
    assert client.get("/health").status_code == 200
    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert "postgres_persistence_status" in summary_payload
    assert "vector_memory_status" in summary_payload
    assert summary_payload["recent_memory_count"] >= 1


def test_upper_workflow_provider_failure_returns_degraded_response(monkeypatch):
    from app.services import upper_workflow_service

    def fail_freshness(_request):
        raise RuntimeError("yfinance throttled: 429 Too Many Requests")

    monkeypatch.setattr(upper_workflow_service, "run_data_freshness_check", fail_freshness)
    response = client.post(
        "/api/upper-workflow/run",
        json={
            "symbols": ["TSLA", "META", "PLTR"],
            "source": "auto",
            "horizon": "swing",
            "allow_mock": False,
            "build_trigger_rules": True,
            "run_event_scanner": True,
            "run_signal_scoring": True,
            "run_meta_model": True,
            "run_recommendation_pipeline": False,
            "promote_to_candidate_universe": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked_by_data_freshness"
    assert payload["blockers"]
    assert any("Data freshness check failed" in blocker for blocker in payload["blockers"])
    assert any("No mock data was used" in warning for warning in payload["warnings"])
    stages = [stage["stage"] for stage in payload["stages"]]
    assert "data_freshness" in stages
    assert "universe_selection" not in stages

    latest = client.get("/api/upper-workflow/latest")
    assert latest.status_code == 200
    assert latest.json()["run_id"] == payload["run_id"]
    history = client.get("/api/upper-workflow/history")
    assert history.status_code == 200
    assert any(run["run_id"] == payload["run_id"] for run in history.json()["runs"])
