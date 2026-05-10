from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    frontend_port: int = 3900
    backend_port: int = 8900


class AccountRiskProfile(BaseModel):
    account_mode: Literal["manual", "paper"] = "manual"
    account_equity: float = 1000.0
    buying_power: float = 1000.0
    cash: float = 1000.0
    max_risk_per_trade_percent: float = 1.0
    max_daily_loss_percent: float = 2.0
    max_position_size_percent: float = 10.0
    min_reward_risk_ratio: float = 3.0
    preferred_risk_style: str = "small_risk_high_upside"
    paper_only: bool = True
    source: str = "manual_profile_default"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AccountRiskProfileUpdate(BaseModel):
    account_equity: float | None = None
    buying_power: float | None = None
    cash: float | None = None
    max_risk_per_trade_percent: float | None = None
    max_daily_loss_percent: float | None = None
    max_position_size_percent: float | None = None
    min_reward_risk_ratio: float | None = None
    preferred_risk_style: str | None = None


class AgentStatus(BaseModel):
    name: str
    role: str
    status: str
    status_label: str
    last_checked: datetime = Field(default_factory=datetime.utcnow)


class LiveWatchlistCandidate(BaseModel):
    symbol: str
    asset: str
    asset_class: Literal["stock", "option", "crypto"]
    horizon: str
    trigger: str
    trigger_type: str
    priority_score: int
    trigger_strength: int
    account_fit: str
    account_fit_label: str
    suggested_expression: str
    agent_status: str
    notify_status: str
    notify_label: str
    data_quality: str
    reason: str
    risk_factors: List[str]


class LiveWatchlistSummary(BaseModel):
    triggered_now: int
    high_conviction: int
    alerts_sent_today: int
    average_priority_score: int
    strongest_trigger: str
    auto_refresh_interval: str = "5m"
    notify_enabled: bool = True
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class LiveWatchlistResponse(BaseModel):
    mode: str = "research_notifications_only"
    live_trading_enabled: bool = False
    execution_enabled: bool = False
    summary: LiveWatchlistSummary
    agents: List[AgentStatus]
    candidates: List[LiveWatchlistCandidate]
    disclaimer: str = "No live execution. Research and notifications only."


class EdgeSignal(BaseModel):
    symbol: str
    asset_class: Literal["stock", "option", "crypto"]
    signal_name: str
    signal_type: str
    urgency: Literal["low", "medium", "high", "critical"]
    time_decay: str
    edge_score: int
    confidence: float
    spread_pass: bool
    liquidity_pass: bool
    regime_pass: bool
    account_fit: str
    recommended_action: str
    alert_status: str
    reason: str
    risk_factors: List[str]


class EdgeSignalsResponse(BaseModel):
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    alerts_enabled: bool = True
    account_range: str = "$1K-$10K"
    signals: List[EdgeSignal]
    signal_source_status: str = Field(
        default="no_real_signal_source",
        description="no_real_signal_source until source-backed edge signals are available.",
    )


class ModelVote(BaseModel):
    model: str
    status: Literal["prototype", "active", "disabled"] = "prototype"
    signal: Literal["bullish", "bearish", "neutral", "risk_off"]
    confidence: float
    explanation: str


class PricePlan(BaseModel):
    current_price: float
    buy_zone_low: float
    buy_zone_high: float
    stop_loss: float
    target_price: float
    target_2_price: float | None = None


class RiskPlan(BaseModel):
    position_size_dollars: float
    max_dollar_risk: float
    max_loss_percent: float
    expected_return_percent: float
    reward_risk_ratio: float
    account_fit: str


class TradeRecommendation(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    asset_class: Literal["stock", "option", "crypto"]
    action: Literal["buy", "watch", "avoid"]
    action_label: str
    horizon: Literal["intraday", "day_trade", "swing", "one_month"]
    confidence: float
    final_score: int
    urgency: Literal["low", "medium", "high", "critical"]
    price_plan: PricePlan
    risk_plan: RiskPlan
    model_votes: List[ModelVote]
    final_reason: str
    invalidation_rules: List[str]
    risk_factors: List[str]
    data_mode: Literal["paper", "live", "source_unavailable"] = "source_unavailable"
    execution_enabled: bool = False
    research_only: bool = True


class Recommendation(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    asset_class: Literal["stock", "option", "crypto"]
    horizon: str
    final_decision: str
    final_score: int
    confidence: float
    reward_risk_ratio: float
    account_fit: str
    model_stack: List[str]
    reason: str
    risk_factors: List[str]


class SourceDataStatus(BaseModel):
    symbol: str
    provider: str | None = None
    data_quality: str | None = None
    is_mock: bool = False
    error: str | None = None
    """How snapshots were requested for this candidate (e.g. auto → resolves via MARKET_DATA_PROVIDER)."""
    pipeline_source: str | None = None


class CommandCenterDataSourceConfirmation(BaseModel):
    """Runtime-effective feeds and workflow routing for this Command Center response."""

    market_data_primary: str = "not_configured"
    market_data_fallback_chain: List[str] = Field(default_factory=list)
    universe_selection_source: str = "auto"
    universe_selection_horizon: str = "swing"
    decision_workflow_source: str = "auto"
    decision_workflow_horizon: str = "swing"
    news_enabled: bool = False
    news_primary: str = "none"
    news_fallback_chain: List[str] = Field(default_factory=list)
    account_profile_data_source: str = ""
    universe_run_id: str | None = None
    decision_workflow_run_id: str | None = None
    candidate_seeds: List[str] = Field(default_factory=list)
    symbols_after_universe: List[str] = Field(default_factory=list)


class CommandCenterResponse(BaseModel):
    account_profile: AccountRiskProfile
    top_action: TradeRecommendation | None = None
    top_recommendations: List[Recommendation]
    urgent_edge_alerts: List[EdgeSignal]
    agents: List[AgentStatus]
    source_data_status: List[SourceDataStatus] = Field(default_factory=list)
    dashboard_mode: str = "source_backed"
    cost_usage_message: str = "No cost usage data recorded yet."
    data_source_confirmation: CommandCenterDataSourceConfirmation = Field(
        default_factory=CommandCenterDataSourceConfirmation,
    )
