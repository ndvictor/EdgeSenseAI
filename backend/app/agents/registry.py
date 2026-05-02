from pydantic import BaseModel, Field


class CoreAgentRegistryEntry(BaseModel):
    agent_key: str
    agent_name: str
    category: str
    purpose: str
    supported_asset_classes: list[str]
    supported_timeframes: list[str]
    required_inputs: list[str]
    output_fields: list[str]
    status: str
    uses_llm: bool
    uses_models: bool
    safe_for_auto_run: bool
    notes: list[str] = Field(default_factory=list)


_AGENTS: list[CoreAgentRegistryEntry] = [
    CoreAgentRegistryEntry(agent_key="data_quality", agent_name="Data Quality Agent", category="data_gate", purpose="Validate provider readiness, freshness, source type, and required market fields.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["market_snapshot"], output_fields=["quality_status", "missing_fields", "blockers", "warnings"], status="available", uses_llm=False, uses_models=False, safe_for_auto_run=True, notes=["Deterministic data gate."]),
    CoreAgentRegistryEntry(agent_key="market_regime", agent_name="Market Regime Agent", category="market_context", purpose="Summarize broad market regime and strategy bias.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["market_context"], output_fields=["regime_state", "confidence", "allowed_strategies"], status="partial", uses_llm=False, uses_models=False, safe_for_auto_run=True, notes=["Current regime service is prototype context."]),
    CoreAgentRegistryEntry(agent_key="edge_signal_scanner", agent_name="Edge Signal Scanner Agent", category="signal_scanning", purpose="Scan watchlists for deterministic edge setup candidates.", supported_asset_classes=["stock", "crypto"], supported_timeframes=["intraday", "day_trade", "swing"], required_inputs=["market_snapshot", "strategy_config"], output_fields=["detected_signals"], status="available", uses_llm=False, uses_models=False, safe_for_auto_run=True, notes=["Research/paper-only scanner."]),
    CoreAgentRegistryEntry(agent_key="technical_signal", agent_name="Technical Signal Agent", category="signal_family", purpose="Create trend, momentum, VWAP, breakout, and mean-reversion features.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["candles", "market_snapshot"], output_fields=["technical_score", "momentum_score", "vwap_confirmation"], status="partial", uses_llm=False, uses_models=False, safe_for_auto_run=True, notes=["Uses existing feature engineering where available."]),
    CoreAgentRegistryEntry(agent_key="volume_order_flow", agent_name="Volume / Order Flow Agent", category="signal_family", purpose="Create RVOL, liquidity, and order-flow proxy features.", supported_asset_classes=["stock", "crypto"], supported_timeframes=["intraday", "day_trade", "swing"], required_inputs=["volume", "average_volume", "bid_ask_spread"], output_fields=["volume_score", "rvol_score", "liquidity_score"], status="partial", uses_llm=False, uses_models=False, safe_for_auto_run=True, notes=["Order book depth is not wired yet."]),
    CoreAgentRegistryEntry(agent_key="options_flow", agent_name="Options Flow Agent", category="signal_family", purpose="Create unusual calls/puts, IV, open-interest, and spread-quality features.", supported_asset_classes=["option"], supported_timeframes=["intraday", "day_trade", "swing", "earnings"], required_inputs=["options_chain", "underlying_snapshot"], output_fields=["options_score", "iv_score", "flow_signal"], status="placeholder", uses_llm=False, uses_models=False, safe_for_auto_run=False, notes=["Requires options-chain provider."]),
    CoreAgentRegistryEntry(agent_key="macro_news_impact", agent_name="Macro / News Impact Agent", category="context", purpose="Create news, event, and macro conflict features.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["news_events", "macro_snapshot"], output_fields=["sentiment_score", "macro_score"], status="placeholder", uses_llm=True, uses_models=True, safe_for_auto_run=False, notes=["Must route through LLM Gateway; no paid calls by default."]),
    CoreAgentRegistryEntry(agent_key="volatility", agent_name="Volatility Agent", category="signal_family", purpose="Create realized/implied volatility and volatility-fit features.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["candles", "options_chain_optional"], output_fields=["volatility_score", "volatility_regime"], status="partial", uses_llm=False, uses_models=True, safe_for_auto_run=True, notes=["GARCH model remains placeholder."]),
    CoreAgentRegistryEntry(agent_key="model_orchestrator", agent_name="Model Orchestrator Agent", category="model_control", purpose="Select eligible models based on features, data quality, and strategy requirements.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["feature_rows", "strategy_config"], output_fields=["model_plan", "model_outputs"], status="available", uses_llm=False, uses_models=True, safe_for_auto_run=True, notes=["Does not run placeholder models as live."]),
    CoreAgentRegistryEntry(agent_key="risk_manager", agent_name="Risk Manager Agent", category="risk", purpose="Apply paper-only account, position, and reward/risk constraints.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["signals", "account_profile"], output_fields=["risk_review", "approval_required"], status="available", uses_llm=True, uses_models=False, safe_for_auto_run=True, notes=["LLM use is dry-run through LLM Gateway."]),
    CoreAgentRegistryEntry(agent_key="portfolio_manager", agent_name="Portfolio Manager Agent", category="portfolio", purpose="Convert risk-reviewed signals into watch-only or paper-review decisions.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["risk_review", "signals"], output_fields=["portfolio_decision"], status="available", uses_llm=True, uses_models=False, safe_for_auto_run=True, notes=["Live trading disabled. Human approval required."]),
    CoreAgentRegistryEntry(agent_key="backtesting", agent_name="Backtesting Agent", category="validation", purpose="Evaluate strategy and feature behavior against historical outcomes.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["day_trade", "swing", "one_month"], required_inputs=["historical_features", "outcome_labels"], output_fields=["backtest_metrics"], status="partial", uses_llm=False, uses_models=True, safe_for_auto_run=False, notes=["Current service is prototype summary."]),
    CoreAgentRegistryEntry(agent_key="trade_journal", agent_name="Trade Journal Agent", category="learning_loop", purpose="Capture paper outcomes and lessons for future labels.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["paper_trade", "outcome"], output_fields=["journal_entry", "labels"], status="partial", uses_llm=True, uses_models=False, safe_for_auto_run=False, notes=["LLM summaries must route through LLM Gateway."]),
    CoreAgentRegistryEntry(agent_key="cost_controller", agent_name="Cost Controller Agent", category="cost", purpose="Estimate and constrain LLM/model orchestration costs.", supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], required_inputs=["planned_calls", "model_plan"], output_fields=["cost_estimate", "budget_status"], status="available", uses_llm=True, uses_models=False, safe_for_auto_run=True, notes=["Dry-run LLM Gateway metadata only by default."]),
]


def list_core_agents() -> list[CoreAgentRegistryEntry]:
    return _AGENTS


def get_core_agent(agent_key: str) -> CoreAgentRegistryEntry | None:
    return next((agent for agent in _AGENTS if agent.agent_key == agent_key), None)


def get_agent_registry_summary() -> dict[str, int]:
    return {
        "total_agents": len(_AGENTS),
        "available_agents_count": len([agent for agent in _AGENTS if agent.status == "available"]),
        "placeholder_agents_count": len([agent for agent in _AGENTS if agent.status == "placeholder"]),
    }
