from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class WatchlistItem(BaseModel):
    ticker: str
    asset_class: str = "stock"
    notes: str | None = None


class Watchlist(BaseModel):
    id: str
    name: str
    description: str | None = None
    items: list[WatchlistItem]
    updated_at: str


class WatchlistCreateRequest(BaseModel):
    name: str
    description: str | None = None
    items: list[WatchlistItem] = Field(default_factory=list)


class PaperTrade(BaseModel):
    id: str
    ticker: str
    asset_class: str
    side: str
    status: Literal["planned", "open", "closed", "cancelled"]
    planned_entry: str | None = None
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    exit_price: float | None = None
    quantity: float | None = None
    realized_r: float | None = None
    outcome_label: str = "pending"
    updated_at: str


class PaperTradeCreateRequest(BaseModel):
    ticker: str
    asset_class: str = "stock"
    side: str = "long"
    planned_entry: str | None = None
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    quantity: float | None = None


class RecommendationLifecycleItem(BaseModel):
    id: str
    ticker: str
    action: str
    status: str
    score: float
    probability: float | None = None
    next_step: str
    provenance: list[str]
    updated_at: str


class AgentScorecard(BaseModel):
    agent_key: str
    agent_name: str
    run_count: int
    success_rate: float | None = None
    average_latency_ms: float | None = None
    drift_status: str
    last_run_at: str | None = None
    scorecard_notes: list[str]


class HistoricalAnalog(BaseModel):
    ticker: str
    analog_ticker: str | None = None
    analog_date: str | None = None
    similarity_score: float
    outcome_summary: str
    matching_features: list[str]


class MarketRadarEvent(BaseModel):
    id: str
    ticker: str | None = None
    event_type: str
    severity: str
    title: str
    summary: str
    source: str
    impact_score: float
    detected_at: str


class TradeQualityReview(BaseModel):
    id: str
    ticker: str
    setup_quality: float
    entry_quality: float
    risk_quality: float
    thesis_quality: float
    overall_grade: str
    notes: list[str]


class FeatureStoreRow(BaseModel):
    ticker: str
    timestamp: str
    horizon: str
    data_source: str
    data_quality: str
    technical_score: float | None = None
    momentum_score: float | None = None
    volume_score: float | None = None
    options_score: float | None = None
    sentiment_score: float | None = None
    volatility_score: float | None = None
    macro_score: float | None = None
    regime_score: float | None = None
    liquidity_score: float | None = None
    confidence: float | None = None


class SignalAgentRunRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["AMD", "NVDA", "AAPL", "MSFT", "BTC-USD"])
    horizon: str = "swing"
    data_source: str = "yfinance"
    agents: list[str] = Field(default_factory=lambda: ["technical", "volume", "volatility", "macro_regime"])


class SignalAgentRunResponse(BaseModel):
    run_id: str
    status: str
    feature_rows: list[FeatureStoreRow]
    agents_run: list[str]
    missing_agents: list[str]
    next_step: str


_WATCHLISTS: list[Watchlist] = [
    Watchlist(id="wl-core", name="Core Liquid Watchlist", description="Large liquid symbols for small-account scanning.", items=[WatchlistItem(ticker="AMD"), WatchlistItem(ticker="NVDA"), WatchlistItem(ticker="AAPL"), WatchlistItem(ticker="MSFT"), WatchlistItem(ticker="BTC-USD", asset_class="crypto")], updated_at=datetime.utcnow().isoformat())
]

_PAPER_TRADES: list[PaperTrade] = []


def list_watchlists() -> list[Watchlist]:
    return _WATCHLISTS


def create_watchlist(request: WatchlistCreateRequest) -> Watchlist:
    watchlist = Watchlist(id=f"wl-{len(_WATCHLISTS)+1}", name=request.name, description=request.description, items=request.items, updated_at=datetime.utcnow().isoformat())
    _WATCHLISTS.append(watchlist)
    return watchlist


def add_watchlist_item(watchlist_id: str, item: WatchlistItem) -> Watchlist:
    for watchlist in _WATCHLISTS:
        if watchlist.id == watchlist_id:
            existing = {row.ticker for row in watchlist.items}
            if item.ticker not in existing:
                watchlist.items.append(item)
            watchlist.updated_at = datetime.utcnow().isoformat()
            return watchlist
    raise ValueError("watchlist not found")


def list_paper_trades() -> list[PaperTrade]:
    return _PAPER_TRADES


def create_paper_trade(request: PaperTradeCreateRequest) -> PaperTrade:
    trade = PaperTrade(id=f"pt-{len(_PAPER_TRADES)+1}", ticker=request.ticker.upper(), asset_class=request.asset_class, side=request.side, status="planned", planned_entry=request.planned_entry, entry_price=request.entry_price, stop_price=request.stop_price, target_price=request.target_price, quantity=request.quantity, updated_at=datetime.utcnow().isoformat())
    _PAPER_TRADES.append(trade)
    return trade


def update_paper_trade_status(trade_id: str, status: str, exit_price: float | None = None, outcome_label: str | None = None) -> PaperTrade:
    for trade in _PAPER_TRADES:
        if trade.id == trade_id:
            trade.status = status  # type: ignore[assignment]
            trade.exit_price = exit_price if exit_price is not None else trade.exit_price
            trade.outcome_label = outcome_label or trade.outcome_label
            if trade.entry_price and trade.exit_price and trade.stop_price:
                risk = abs(trade.entry_price - trade.stop_price)
                trade.realized_r = round((trade.exit_price - trade.entry_price) / risk, 2) if risk else None
            trade.updated_at = datetime.utcnow().isoformat()
            return trade
    raise ValueError("paper trade not found")


def get_recommendation_lifecycle() -> list[RecommendationLifecycleItem]:
    now = datetime.utcnow().isoformat()
    return [
        RecommendationLifecycleItem(id="rec-amd-001", ticker="AMD", action="WATCH_SETUP", status="generated", score=84.5, probability=0.68, next_step="wait_for_entry_zone_and_data_quality_pass", provenance=["technical_agent", "volume_agent", "risk_filter"], updated_at=now),
        RecommendationLifecycleItem(id="rec-nvda-001", ticker="NVDA", action="WATCH_ONLY", status="risk_review", score=79.2, probability=0.63, next_step="reduce_position_size_or_wait_for_pullback", provenance=["volume_agent", "macro_regime_agent", "xgboost_supervisor"], updated_at=now),
    ]


def get_agent_scorecards() -> list[AgentScorecard]:
    now = datetime.utcnow().isoformat()
    return [
        AgentScorecard(agent_key="technical", agent_name="Technical Signal Agent", run_count=42, success_rate=0.93, average_latency_ms=120, drift_status="ok", last_run_at=now, scorecard_notes=["Produces momentum and trend features.", "Does not issue final recommendations."]),
        AgentScorecard(agent_key="volume", agent_name="Volume Signal Agent", run_count=42, success_rate=0.9, average_latency_ms=95, drift_status="ok", last_run_at=now, scorecard_notes=["Produces RVOL and volume acceleration features."]),
        AgentScorecard(agent_key="options", agent_name="Options Flow Agent", run_count=0, success_rate=None, average_latency_ms=None, drift_status="not_configured", last_run_at=None, scorecard_notes=["Requires options-chain provider."]),
        AgentScorecard(agent_key="sentiment", agent_name="News Sentiment Agent", run_count=0, success_rate=None, average_latency_ms=None, drift_status="not_configured", last_run_at=None, scorecard_notes=["Requires news provider and sentiment model."]),
    ]


def get_historical_analogs(ticker: str) -> list[HistoricalAnalog]:
    return [
        HistoricalAnalog(ticker=ticker.upper(), analog_ticker=ticker.upper(), analog_date="2025-10-14", similarity_score=0.78, outcome_summary="Momentum continued for three sessions before mean reversion.", matching_features=["high_rvol", "positive_momentum", "risk_on_regime"]),
        HistoricalAnalog(ticker=ticker.upper(), analog_ticker="NVDA", analog_date="2025-08-21", similarity_score=0.71, outcome_summary="Strong opening move required tighter stop due to elevated volatility.", matching_features=["sector_strength", "elevated_volatility", "trend_confirmation"]),
    ]


def get_market_radar_events() -> list[MarketRadarEvent]:
    now = datetime.utcnow().isoformat()
    return [
        MarketRadarEvent(id="radar-001", ticker="NVDA", event_type="volume_acceleration", severity="medium", title="Volume acceleration detected", summary="Volume signal requires confirmation from price and spread quality.", source="volume_agent", impact_score=0.72, detected_at=now),
        MarketRadarEvent(id="radar-002", ticker=None, event_type="market_regime", severity="medium", title="Risk-on regime prototype", summary="Regime signal is currently prototype and should be replaced with SPY/QQQ/VIX pipeline.", source="macro_regime_agent", impact_score=0.64, detected_at=now),
    ]


def get_trade_quality_reviews() -> list[TradeQualityReview]:
    return [
        TradeQualityReview(id="tq-001", ticker="AMD", setup_quality=0.82, entry_quality=0.74, risk_quality=0.88, thesis_quality=0.79, overall_grade="B+", notes=["Setup is strong but requires fresh data quality pass.", "Entry should be limited to planned zone."]),
        TradeQualityReview(id="tq-002", ticker="NVDA", setup_quality=0.78, entry_quality=0.61, risk_quality=0.66, thesis_quality=0.81, overall_grade="B", notes=["High opportunity score but elevated volatility reduces quality."]),
    ]


def run_signal_agents(request: SignalAgentRunRequest) -> SignalAgentRunResponse:
    now = datetime.utcnow().isoformat()
    supported_agents = {"technical", "volume", "volatility", "macro_regime", "liquidity"}
    agents_run = [agent for agent in request.agents if agent in supported_agents]
    missing_agents = [agent for agent in request.agents if agent not in supported_agents]
    rows = []
    for index, symbol in enumerate(request.symbols):
        base = 0.55 + (index * 0.04)
        rows.append(FeatureStoreRow(ticker=symbol.upper(), timestamp=now, horizon=request.horizon, data_source=request.data_source, data_quality="prototype_or_research", technical_score=round(base, 2) if "technical" in agents_run else None, momentum_score=round(base + 0.05, 2) if "technical" in agents_run else None, volume_score=round(base + 0.08, 2) if "volume" in agents_run else None, volatility_score=round(0.45 + index * 0.03, 2) if "volatility" in agents_run else None, macro_score=0.66 if "macro_regime" in agents_run else None, regime_score=0.7 if "macro_regime" in agents_run else None, liquidity_score=0.86 if "liquidity" in agents_run else None, confidence=round(0.62 + index * 0.03, 2)))
    return SignalAgentRunResponse(run_id=f"sig-{int(datetime.utcnow().timestamp())}", status="completed", feature_rows=rows, agents_run=agents_run, missing_agents=missing_agents, next_step="write_feature_rows_to_feature_store_then_run_meta_model")
