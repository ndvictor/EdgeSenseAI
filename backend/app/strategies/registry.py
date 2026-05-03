from typing import Any, Literal

from pydantic import BaseModel, Field


class StrategyConfig(BaseModel):
    strategy_key: str
    display_name: str
    asset_class: str
    timeframe: str
    description: str
    edge_signals: list[str]
    required_agents: list[str]
    optional_agents: list[str]
    required_models: list[str]
    optional_models: list[str]
    required_data_sources: list[str]
    validation_rules: list[str]
    risk_rules: list[str]
    action_rules: list[str]
    default_weights: dict[str, float]
    auto_run_supported: bool
    live_trading_supported: bool = False
    paper_trading_supported: bool = True
    requires_human_approval: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    # New candidate/research strategy fields (all optional for backward compatibility)
    status: Literal["active", "approved", "candidate", "paused", "rejected"] = "approved"
    promotion_status: Literal["active", "candidate", "testing", "paper_active", "paused", "rejected"] = "active"
    claim_source: str | None = None
    claim_type: Literal["internal", "vendor_claim", "research_note", "backtest", "paper_result"] = "internal"
    best_regimes: list[str] = Field(default_factory=list)
    bad_regimes: list[str] = Field(default_factory=list)
    trigger_rules: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    small_account_fit: bool | None = None
    drawdown_risk: str | None = None
    pdt_risk: bool | None = None
    paper_research_only: bool = False
    requires_backtest: bool = False
    requires_owner_approval_for_promotion: bool = False
    candidate_universe_examples: list[str] = Field(default_factory=list)
    core_universe: list[str] = Field(default_factory=list)
    optional_expansion: list[str] = Field(default_factory=list)
    disabled_reason: str | None = None
    promotion_requirements: list[str] = Field(default_factory=list)


_STRATEGIES: list[StrategyConfig] = [
    StrategyConfig(strategy_key="stock_day_trading", display_name="Stock Day Trading", asset_class="stock", timeframe="day_trade", description="Liquid stock intraday setups using technical, RVOL, spread, volatility, and regime context.", edge_signals=["rvol_spike", "mean_reversion_1_5_min", "short_term_momentum", "breakout"], required_agents=["data_quality", "technical_signal", "volume_order_flow", "volatility", "market_regime", "risk_manager", "portfolio_manager"], optional_agents=["macro_news_impact", "cost_controller"], required_models=["weighted_ranker"], optional_models=["xgboost_ranker", "kalman_trend_filter"], required_data_sources=["market_snapshot", "candles", "volume"], validation_rules=["quality_status must not fail", "spread must be available or warn", "volume required"], risk_rules=["paper only", "max risk per trade required", "human approval required"], action_rules=["watch only until risk review passes", "no live execution"], default_weights={"technical": 0.3, "volume": 0.25, "volatility": 0.15, "regime": 0.15, "risk": 0.15}, auto_run_supported=True),
    StrategyConfig(strategy_key="stock_swing", display_name="Stock Swing", asset_class="stock", timeframe="swing", description="Multi-day stock momentum and breakout setups.", edge_signals=["rvol_spike", "short_term_momentum", "breakout", "regime_shift"], required_agents=["data_quality", "technical_signal", "volume_order_flow", "market_regime", "model_orchestrator", "risk_manager", "portfolio_manager"], optional_agents=["macro_news_impact", "backtesting", "cost_controller"], required_models=["weighted_ranker"], optional_models=["xgboost_ranker", "hmm_regime", "arimax_forecast"], required_data_sources=["market_snapshot", "candles"], validation_rules=["quality_status must not fail", "trend and volume features required"], risk_rules=["paper only", "reward/risk minimum"], action_rules=["route through model orchestrator before recommendation"], default_weights={"technical": 0.35, "volume": 0.2, "regime": 0.2, "model": 0.15, "risk": 0.1}, auto_run_supported=True),
    StrategyConfig(strategy_key="stock_one_month", display_name="Stock One Month", asset_class="stock", timeframe="one_month", description="One-month stock positioning with macro/regime and model confirmation.", edge_signals=["etf_stock_lag_pairs", "breakout", "regime_shift"], required_agents=["data_quality", "technical_signal", "market_regime", "macro_news_impact", "model_orchestrator", "risk_manager"], optional_agents=["backtesting", "portfolio_manager"], required_models=["weighted_ranker"], optional_models=["xgboost_ranker", "arimax_forecast", "hmm_regime"], required_data_sources=["market_snapshot", "candles", "macro_optional"], validation_rules=["macro conflicts must be reviewed when present"], risk_rules=["smaller position sizing", "paper only"], action_rules=["human review before paper trade"], default_weights={"technical": 0.25, "macro": 0.25, "regime": 0.2, "model": 0.2, "risk": 0.1}, auto_run_supported=False),
    StrategyConfig(strategy_key="options_day_trading", display_name="Options Day Trading", asset_class="option", timeframe="day_trade", description="Options intraday review emphasizing options flow, spread/liquidity, IV, and underlying confirmation.", edge_signals=["unusual_calls_puts", "advanced_options_flow", "short_term_momentum"], required_agents=["data_quality", "options_flow", "technical_signal", "volatility", "risk_manager", "portfolio_manager"], optional_agents=["volume_order_flow", "cost_controller"], required_models=["weighted_ranker"], optional_models=["xgboost_ranker"], required_data_sources=["underlying_snapshot", "options_chain", "spread"], validation_rules=["options fields required", "spread must pass"], risk_rules=["defined risk only", "paper only"], action_rules=["no market orders", "human approval required"], default_weights={"options_flow": 0.35, "technical": 0.2, "volatility": 0.2, "liquidity": 0.15, "risk": 0.1}, auto_run_supported=False),
    StrategyConfig(strategy_key="options_swing", display_name="Options Swing", asset_class="option", timeframe="swing", description="Options swing setups using underlying trend, IV, spread, and risk-defined structure.", edge_signals=["unusual_calls_puts", "advanced_options_flow", "breakout"], required_agents=["data_quality", "options_flow", "technical_signal", "volatility", "market_regime", "risk_manager"], optional_agents=["macro_news_impact", "portfolio_manager"], required_models=["weighted_ranker"], optional_models=["xgboost_ranker", "hmm_regime"], required_data_sources=["underlying_snapshot", "options_chain", "candles"], validation_rules=["IV and open interest required"], risk_rules=["defined risk only", "paper only"], action_rules=["human approval required"], default_weights={"options_flow": 0.3, "technical": 0.25, "volatility": 0.2, "regime": 0.15, "risk": 0.1}, auto_run_supported=False),
    StrategyConfig(strategy_key="options_earnings", display_name="Options Earnings", asset_class="option", timeframe="earnings", description="Earnings-focused options review with IV, event, and spread controls.", edge_signals=["advanced_options_flow", "unusual_calls_puts", "retail_sentiment_spike"], required_agents=["data_quality", "options_flow", "volatility", "macro_news_impact", "risk_manager"], optional_agents=["portfolio_manager", "cost_controller"], required_models=["weighted_ranker"], optional_models=["finbert_sentiment"], required_data_sources=["options_chain", "earnings_calendar", "news"], validation_rules=["event date required", "options liquidity required"], risk_rules=["paper only", "defined risk only"], action_rules=["human approval required"], default_weights={"options_flow": 0.3, "volatility": 0.3, "event": 0.2, "risk": 0.2}, auto_run_supported=False),
    StrategyConfig(strategy_key="crypto_intraday", display_name="Crypto Intraday", asset_class="crypto", timeframe="intraday", description="Crypto intraday setups using technical, volume/order-flow proxies, volatility, and macro/regime context.", edge_signals=["order_book_imbalance", "rvol_spike", "short_term_momentum", "mean_reversion_1_5_min"], required_agents=["data_quality", "technical_signal", "volume_order_flow", "volatility", "market_regime", "risk_manager", "portfolio_manager"], optional_agents=["macro_news_impact", "cost_controller"], required_models=["weighted_ranker"], optional_models=["xgboost_ranker", "kalman_trend_filter"], required_data_sources=["market_snapshot", "volume", "candles"], validation_rules=["quality_status must not fail", "volume required"], risk_rules=["paper only", "reduced size in high volatility"], action_rules=["watch only before human approval"], default_weights={"technical": 0.3, "volume": 0.25, "volatility": 0.2, "regime": 0.15, "risk": 0.1}, auto_run_supported=True),
    StrategyConfig(strategy_key="crypto_swing", display_name="Crypto Swing", asset_class="crypto", timeframe="swing", description="Crypto swing setups using momentum, volatility, and macro context.", edge_signals=["rvol_spike", "breakout", "regime_shift", "short_term_momentum"], required_agents=["data_quality", "technical_signal", "volume_order_flow", "volatility", "market_regime", "model_orchestrator", "risk_manager"], optional_agents=["macro_news_impact", "portfolio_manager"], required_models=["weighted_ranker"], optional_models=["xgboost_ranker", "hmm_regime"], required_data_sources=["market_snapshot", "candles"], validation_rules=["quality_status must not fail"], risk_rules=["paper only", "volatility sizing"], action_rules=["human approval required"], default_weights={"technical": 0.3, "volume": 0.2, "volatility": 0.2, "regime": 0.2, "risk": 0.1}, auto_run_supported=True),
    StrategyConfig(strategy_key="crypto_cycle", display_name="Crypto Cycle", asset_class="crypto", timeframe="one_month", description="Cycle-aware crypto positioning using regime, macro, trend, and volatility features.", edge_signals=["regime_shift", "breakout", "retail_sentiment_spike"], required_agents=["data_quality", "market_regime", "technical_signal", "macro_news_impact", "model_orchestrator", "risk_manager"], optional_agents=["backtesting", "trade_journal"], required_models=["weighted_ranker"], optional_models=["hmm_regime", "arimax_forecast", "finbert_sentiment"], required_data_sources=["market_snapshot", "macro_optional", "sentiment_optional"], validation_rules=["regime context required"], risk_rules=["paper only", "human approval required"], action_rules=["no live execution"], default_weights={"regime": 0.3, "macro": 0.25, "technical": 0.2, "model": 0.15, "risk": 0.1}, auto_run_supported=False),
    # Candidate Strategies (Research/Testing Only)
    StrategyConfig(
        strategy_key="15_min_liquid_momentum",
        display_name="15-Min Liquid Momentum",
        asset_class="stock",
        timeframe="day_trade",
        description="Short-timeframe momentum strategy on liquid, high-volume stocks/ETFs. Research candidate only.",
        edge_signals=["momentum_continuation", "rvol_spike", "vwap_reclaim"],
        required_agents=["data_quality", "technical_signal", "volume_order_flow", "market_regime", "risk_manager"],
        optional_agents=["cost_controller"],
        required_models=["weighted_ranker"],
        optional_models=["xgboost_ranker"],
        required_data_sources=["live_quotes", "1m_or_5m_candles", "volume", "rvol", "vwap", "spread", "sector_etf_confirmation"],
        validation_rules=["liquidity_pass", "spread_pass", "regime_confirmation"],
        risk_rules=["paper only", "strict_stop_timeout_required", "small_account_spread_slippage_risk"],
        action_rules=["no live execution", "research candidate only"],
        default_weights={"momentum": 0.35, "volume": 0.25, "technical": 0.2, "regime": 0.2},
        auto_run_supported=False,
        status="candidate",
        promotion_status="candidate",
        claim_type="research_note",
        claim_source="public/vendor-inspired AI short-timeframe strategy ideas, not verified performance",
        live_trading_supported=False,
        paper_research_only=True,
        requires_backtest=True,
        requires_owner_approval_for_promotion=True,
        candidate_universe_examples=["NVDA", "AMD", "TSLA", "AAPL", "MSFT", "META", "GOOGL", "QQQ", "SPY", "SOXL"],
        best_regimes=["risk_on", "momentum", "volatility_expansion", "sector_rotation"],
        bad_regimes=["chop", "risk_off", "low_liquidity", "wide_spread"],
        trigger_rules=["price_above_vwap", "rvol_above_threshold", "higher_highs_higher_lows", "sector_index_confirmation", "spread_pass"],
        risk_notes=["high_volatility", "fast_reversals", "avoid_chop", "strict_stop_timeout_required", "small_account_spread_slippage_risk"],
        small_account_fit=True,
        drawdown_risk="high",
        pdt_risk=True,
        promotion_requirements=["backtest_minimum_100_trades", "paper_test_30_days", "sharpe_above_1.0", "owner_approval"],
    ),
    StrategyConfig(
        strategy_key="opening_range_breakout",
        display_name="Opening Range Breakout",
        asset_class="stock",
        timeframe="day_trade",
        description="Trade breakouts from first 5/15/30 minute range after market open. Research candidate only.",
        edge_signals=["breakout", "opening_range_break"],
        required_agents=["data_quality", "technical_signal", "volume_order_flow", "market_regime", "risk_manager"],
        optional_agents=["macro_news_impact"],
        required_models=["weighted_ranker"],
        optional_models=["xgboost_ranker"],
        required_data_sources=["opening_range_high_low", "first_5_15_30_min_candles", "vwap", "volume", "rvol", "spread", "news_catalyst_flag"],
        validation_rules=["first_move_not_overextended", "volume_confirms", "no_wide_spread"],
        risk_rules=["paper only", "strict_freshness_spread_gate_required", "timeout_if_no_follow_through"],
        action_rules=["no live execution", "research candidate only"],
        default_weights={"breakout": 0.4, "volume": 0.3, "technical": 0.2, "regime": 0.1},
        auto_run_supported=False,
        status="candidate",
        promotion_status="candidate",
        claim_type="research_note",
        claim_source="public/vendor-inspired opening range strategy, not verified performance",
        live_trading_supported=False,
        paper_research_only=True,
        requires_backtest=True,
        requires_owner_approval_for_promotion=True,
        best_regimes=["momentum", "risk_on", "volatility_expansion"],
        bad_regimes=["chop", "low_volume", "news_uncertainty_without_confirmation"],
        trigger_rules=["break_above_opening_range_high_with_volume", "retest_holds_above_breakout", "price_above_vwap", "spread_tight"],
        risk_notes=["high_false_breakout_risk", "open_is_noisy", "strict_freshness_spread_gate_required", "timeout_if_no_follow_through"],
        small_account_fit=True,
        drawdown_risk="medium",
        pdt_risk=True,
        promotion_requirements=["backtest_minimum_100_trades", "paper_test_30_days", "win_rate_above_45_percent", "owner_approval"],
    ),
    StrategyConfig(
        strategy_key="double_agent_inverse_etf",
        display_name="Double Agent Inverse ETF",
        asset_class="etf",
        timeframe="swing",
        description="Use regime and trend detection to switch between directional long ETFs/stocks and inverse/hedging ETFs. Research candidate only.",
        edge_signals=["regime_flip", "trend_confirmation", "inverse_etf_momentum"],
        required_agents=["data_quality", "market_regime", "technical_signal", "risk_manager", "portfolio_manager"],
        optional_agents=["macro_news_impact"],
        required_models=["weighted_ranker", "hmm_regime"],
        optional_models=["xgboost_ranker"],
        required_data_sources=["etf_pair_prices", "trend_classification", "volatility_state", "regime_classification", "correlation", "spread_liquidity"],
        validation_rules=["avoid_whipsaw", "require_strong_trend_confirmation", "strict_drawdown_timeout_rules"],
        risk_rules=["paper only", "strong_no_trade_gate_required", "dangerous_for_small_accounts_if_overused"],
        action_rules=["no live execution", "research candidate only", "no_overnight_hold_unless_future_policy_allows"],
        default_weights={"regime": 0.35, "trend": 0.3, "technical": 0.2, "risk": 0.15},
        auto_run_supported=False,
        status="candidate",
        promotion_status="candidate",
        claim_type="research_note",
        claim_source="public/vendor-inspired regime-switching strategy, not verified performance",
        live_trading_supported=False,
        paper_research_only=True,
        requires_backtest=True,
        requires_owner_approval_for_promotion=True,
        candidate_universe_examples=["SOXL", "SOXS", "TQQQ", "SQQQ", "QLD", "QID", "SPY", "SH"],
        best_regimes=["strong_trend", "clear_risk_on", "clear_risk_off", "high_conviction_directional_market"],
        bad_regimes=["chop", "low_conviction", "mixed_sector_signals", "wide_volatility_whipsaw"],
        trigger_rules=["regime_flip_risk_on_risk_off", "trend_confirmation", "inverse_etf_momentum_confirmation"],
        risk_notes=["leveraged_etf_decay", "high_volatility", "whipsaw_risk", "strong_no_trade_gate_required", "dangerous_for_small_accounts_if_overused"],
        small_account_fit=False,
        drawdown_risk="very_high",
        pdt_risk=False,
        promotion_requirements=["backtest_minimum_200_trades", "paper_test_60_days", "sharpe_above_1.2", "drawdown_below_20_percent", "owner_approval"],
    ),
    StrategyConfig(
        strategy_key="tech_quintet_momentum",
        display_name="Tech Quintet Momentum",
        asset_class="stock",
        timeframe="swing",
        description="Focused strategy on highly liquid mega-cap tech names for deeper pattern consistency and lower ticker noise. Research candidate only.",
        edge_signals=["momentum_continuation", "vwap_reclaim", "relative_strength"],
        required_agents=["data_quality", "technical_signal", "volume_order_flow", "market_regime", "risk_manager"],
        optional_agents=["macro_news_impact"],
        required_models=["weighted_ranker"],
        optional_models=["xgboost_ranker"],
        required_data_sources=["price", "volume", "rvol", "vwap", "moving_average_trend", "sector_qqq_confirmation", "spread", "earnings_calendar_flag"],
        validation_rules=["liquidity_pass", "sector_confirmation", "avoid_earnings_surprise_risk"],
        risk_rules=["paper only", "account_exposure_cap_required", "concentration_risk_warning"],
        action_rules=["no live execution", "research candidate only"],
        default_weights={"momentum": 0.35, "relative_strength": 0.25, "volume": 0.2, "technical": 0.2},
        auto_run_supported=False,
        status="candidate",
        promotion_status="candidate",
        claim_type="research_note",
        claim_source="public/vendor-inspired concentrated tech strategy, not verified performance",
        live_trading_supported=False,
        paper_research_only=True,
        requires_backtest=True,
        requires_owner_approval_for_promotion=True,
        core_universe=["AAPL", "MSFT", "NVDA", "META", "GOOGL"],
        optional_expansion=["TSLA", "AMD", "AVGO", "QQQ"],
        best_regimes=["risk_on", "tech_sector_strength", "momentum", "broad_market_support"],
        bad_regimes=["tech_weakness", "risk_off", "high_yield_dollar_pressure", "low_volume_chop"],
        trigger_rules=["vwap_reclaim", "high_volume_breakout", "three_day_momentum_continuation", "qqq_confirmation", "relative_strength_vs_qqq"],
        risk_notes=["concentration_risk", "correlation_risk", "tech_beta_risk", "account_exposure_cap_required"],
        small_account_fit=True,
        drawdown_risk="medium",
        pdt_risk=False,
        promotion_requirements=["backtest_minimum_150_trades", "paper_test_45_days", "sharpe_above_1.0", "max_concurrent_positions_3", "owner_approval"],
    ),
    StrategyConfig(
        strategy_key="options_flow_momentum",
        display_name="Options Flow Momentum",
        asset_class="option",
        timeframe="day_trade",
        description="Use unusual options flow and underlying confirmation to identify short-term directional opportunities. DISABLED - requires options data provider.",
        edge_signals=["unusual_options_flow", "call_put_volume_spike", "iv_rising"],
        required_agents=["data_quality", "options_flow", "technical_signal", "volatility", "risk_manager"],
        optional_agents=["portfolio_manager"],
        required_models=["weighted_ranker"],
        optional_models=["xgboost_ranker"],
        required_data_sources=["option_chain", "option_volume", "open_interest", "implied_volatility", "bid_ask_spread", "underlying_price_trend", "earnings_calendar", "news_catalyst"],
        validation_rules=["underlying_must_confirm", "option_spread_must_pass", "avoid_poor_contract_quality"],
        risk_rules=["paper only", "options_data_quality_required", "no_auto_execution"],
        action_rules=["no live execution", "DISABLED - requires options data provider"],
        default_weights={"options_flow": 0.4, "underlying": 0.25, "volatility": 0.2, "technical": 0.15},
        auto_run_supported=False,
        status="candidate",
        promotion_status="candidate",
        claim_type="research_note",
        claim_source="public/vendor-inspired options flow strategy, not verified performance",
        live_trading_supported=False,
        paper_research_only=True,
        requires_backtest=True,
        requires_owner_approval_for_promotion=True,
        best_regimes=["momentum", "event_catalyst", "volatility_expansion", "strong_underlying_trend"],
        bad_regimes=["wide_option_spreads", "low_open_interest", "low_volume", "iv_crush_risk", "unclear_underlying_direction"],
        trigger_rules=["unusual_call_put_volume", "volume_greater_than_open_interest", "iv_rising", "underlying_confirms_direction", "spread_acceptable"],
        risk_notes=["options_data_quality_required", "wide_spreads_destroy_small_accounts", "no_auto_execution"],
        small_account_fit=False,
        drawdown_risk="high",
        pdt_risk=True,
        disabled_reason="Dedicated options data provider not configured yet",
        promotion_requirements=["options_data_provider_configured", "backtest_minimum_100_trades", "paper_test_30_days", "owner_approval"],
    ),
]


def list_strategies() -> list[StrategyConfig]:
    return _STRATEGIES


def get_strategy(strategy_key: str) -> StrategyConfig | None:
    return next((strategy for strategy in _STRATEGIES if strategy.strategy_key == strategy_key), None)


def list_strategies_by_status(status: str) -> list[StrategyConfig]:
    """List strategies filtered by status (active, approved, candidate, paused, rejected)."""
    return [s for s in _STRATEGIES if s.status == status]


def list_candidate_strategies() -> list[StrategyConfig]:
    """List candidate/research strategies only."""
    return [s for s in _STRATEGIES if s.status == "candidate" or s.promotion_status == "candidate"]


def list_active_strategies() -> list[StrategyConfig]:
    """List active/approved strategies (not candidate)."""
    return [s for s in _STRATEGIES if s.status in ("active", "approved") and s.promotion_status != "candidate"]


def is_strategy_available_for_production(strategy_key: str) -> bool:
    """Check if strategy is available for production use."""
    strategy = get_strategy(strategy_key)
    if not strategy:
        return False
    return (
        strategy.status in ("active", "approved")
        and strategy.promotion_status == "active"
        and strategy.disabled_reason is None
    )
