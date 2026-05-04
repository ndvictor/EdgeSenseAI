from fastapi.testclient import TestClient

from app.main import app
from app.services.market_regime_model_service import (
    MarketRegimeRequest,
    list_market_regime_history,
    run_market_regime_model,
)
from app.services.strategy_debate_service import StrategyDebateRequest, run_strategy_debate
from app.services.strategy_ranking_service import StrategyRankingRequest, run_strategy_ranking
from app.strategies.registry import get_strategy

client = TestClient(app)


def test_market_regime_provider_failure_saves_history_without_unboundlocal(monkeypatch):
    from app.services import market_regime_model_service

    def unavailable_history(*_args, **_kwargs):
        return None

    monkeypatch.setattr(market_regime_model_service, "_get_price_history_safe", unavailable_history)

    response = run_market_regime_model(
        MarketRegimeRequest(
            source="yfinance",
            horizon="swing",
            allow_mock=False,
        )
    )

    assert response.status in {"fail", "warn"}
    assert response.regime == "unknown"
    assert any("SPY" in warning or "QQQ" in warning for warning in response.warnings)
    assert list_market_regime_history(limit=1)[-1].run_id == response.run_id


def test_strategy_debate_separates_research_candidates_from_active_recommendations():
    response = run_strategy_debate(
        StrategyDebateRequest(
            market_phase="market_open",
            active_loop="research_backtesting_loop",
            regime="momentum",
            horizon="swing",
            account_equity=1000,
            buying_power=1000,
            strategy_keys=["stock_swing", "double_agent_inverse_etf", "tech_quintet_momentum", "options_flow_momentum"],
            allow_llm=False,
        )
    )

    assert response.status == "completed"
    assert "stock_swing" in response.recommended_strategy_keys
    assert "stock_swing" in response.recommended_active_strategy_keys
    assert "double_agent_inverse_etf" not in response.recommended_strategy_keys
    assert "tech_quintet_momentum" not in response.recommended_strategy_keys
    assert "options_flow_momentum" not in response.recommended_strategy_keys
    assert "double_agent_inverse_etf" in response.recommended_research_candidate_keys
    assert "tech_quintet_momentum" in response.recommended_research_candidate_keys


def test_strategy_ranking_contract_returns_object_and_active_only_top_strategy():
    debate = run_strategy_debate(
        StrategyDebateRequest(
            market_phase="market_open",
            active_loop="research_backtesting_loop",
            regime="momentum",
            horizon="swing",
            account_equity=1000,
            buying_power=1000,
            strategy_keys=["stock_swing", "double_agent_inverse_etf", "tech_quintet_momentum"],
            allow_llm=False,
        )
    )

    ranking = run_strategy_ranking(
        StrategyRankingRequest(
            debate_run_id=debate.run_id,
            market_phase="market_open",
            active_loop="research_backtesting_loop",
            regime="momentum",
            horizon="swing",
            account_equity=1000,
            buying_power=1000,
        )
    )

    assert ranking.run_id
    assert ranking.ranked_strategies
    assert ranking.active_strategies
    assert ranking.top_strategy_key in ranking.active_strategies
    assert ranking.top_strategy_key == "stock_swing"
    assert "double_agent_inverse_etf" not in ranking.active_strategies
    assert "tech_quintet_momentum" not in ranking.active_strategies
    assert "double_agent_inverse_etf" in ranking.recommended_research_candidate_keys
    assert "tech_quintet_momentum" in ranking.recommended_research_candidate_keys


def test_research_candidate_registry_flags_are_not_production_approved():
    for key in ["double_agent_inverse_etf", "tech_quintet_momentum", "options_flow_momentum"]:
        strategy = get_strategy(key)
        assert strategy is not None
        assert strategy.status == "candidate"
        assert strategy.promotion_status == "candidate"
        assert strategy.live_trading_supported is False
        assert strategy.paper_research_only is True
        assert strategy.requires_owner_approval_for_promotion is True


def test_upper_workflow_1000_account_run_returns_200_without_regime_or_ranking_crash():
    response = client.post(
        "/api/upper-workflow/run",
        json={
            "symbols": ["TSLA", "META", "PLTR", "NVDA", "AMD", "AAPL", "MSFT", "QQQ", "SPY"],
            "source": "auto",
            "horizon": "swing",
            "allow_mock": False,
            "account_equity": 1000,
            "buying_power": 1000,
            "max_risk_per_trade_percent": 1.0,
            "build_trigger_rules": True,
            "run_event_scanner": True,
            "run_signal_scoring": True,
            "run_meta_model": True,
            "run_recommendation_pipeline": True,
            "promote_to_candidate_universe": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"completed", "partial", "blocked_by_data_freshness", "blocked"}
    serialized = str(payload)
    assert "_REGIME_HISTORY" not in serialized
    assert "tuple" not in serialized or "tuple object has no attribute" not in serialized
    if payload.get("strategy_ranking"):
        ranking = payload["strategy_ranking"]
        assert "double_agent_inverse_etf" not in ranking.get("active_strategies", [])
        assert "tech_quintet_momentum" not in ranking.get("active_strategies", [])
        if ranking.get("top_strategy_key"):
            assert ranking["top_strategy_key"] in ranking.get("active_strategies", [])
