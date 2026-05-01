from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field


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


class Recommendation(BaseModel):
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


class CommandCenterResponse(BaseModel):
    account_profile: AccountRiskProfile
    top_recommendations: List[Recommendation]
    urgent_edge_alerts: List[EdgeSignal]
    agents: List[AgentStatus]
    cost_usage_message: str = "No cost usage data recorded yet."
