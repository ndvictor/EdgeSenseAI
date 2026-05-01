from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AccountRiskProfile,
    AccountRiskProfileUpdate,
    AgentStatus,
    CommandCenterResponse,
    EdgeSignal,
    EdgeSignalsResponse,
    HealthResponse,
    LiveWatchlistCandidate,
    LiveWatchlistResponse,
    LiveWatchlistSummary,
    Recommendation,
)

app = FastAPI(title="EdgeSenseAI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3900",
        "http://127.0.0.1:3900",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ACCOUNT_PROFILE = AccountRiskProfile()


def agents() -> list[AgentStatus]:
    return [
        AgentStatus(name="Data Quality Agent", role="data_quality", status="ok", status_label="Checking"),
        AgentStatus(name="Edge Signal Agent", role="edge_signals", status="live", status_label="Scanning"),
        AgentStatus(name="Feature Agent", role="feature_engineering", status="ready", status_label="Building features"),
        AgentStatus(name="Risk Agent", role="account_risk", status="checked", status_label="Account checked"),
    ]


def edge_signals() -> list[EdgeSignal]:
    return [
        EdgeSignal(
            symbol="NVDA",
            asset_class="stock",
            signal_name="RVOL + Breakout",
            signal_type="rvol_breakout",
            urgency="high",
            time_decay="5-30 min",
            edge_score=86,
            confidence=0.78,
            spread_pass=True,
            liquidity_pass=True,
            regime_pass=True,
            account_fit="needs_smaller_expression",
            recommended_action="Alert only: direct shares may be too large. Watch pullback or defined-risk option spread.",
            alert_status="sent",
            reason="Volume acceleration and breakout structure are aligned, but account sizing needs routing.",
            risk_factors=["fast signal decay", "gap reversal", "account size mismatch"],
        ),
        EdgeSignal(
            symbol="AMD",
            asset_class="option",
            signal_name="Unusual Options Flow",
            signal_type="unusual_options_flow",
            urgency="medium",
            time_decay="15 min-1 day",
            edge_score=81,
            confidence=0.72,
            spread_pass=True,
            liquidity_pass=True,
            regime_pass=True,
            account_fit="feasible_defined_risk",
            recommended_action="Send to options scanner for IV, OI, spread, theta, and underlying confirmation.",
            alert_status="queued",
            reason="Options activity is elevated and underlying trend is supportive.",
            risk_factors=["IV expansion risk", "flow may be hedge not direction"],
        ),
        EdgeSignal(
            symbol="BTC-USD",
            asset_class="crypto",
            signal_name="Volatility Burst",
            signal_type="crypto_volatility_burst",
            urgency="high",
            time_decay="5-60 min",
            edge_score=83,
            confidence=0.70,
            spread_pass=True,
            liquidity_pass=True,
            regime_pass=False,
            account_fit="risk_review",
            recommended_action="Monitor only until volatility regime stabilizes. Consider fractional spot sizing only.",
            alert_status="watch_only",
            reason="BTC volatility and momentum are elevated, but regime risk is not fully supportive.",
            risk_factors=["liquidation cascade", "weekend liquidity", "macro correlation"],
        ),
    ]


def live_candidates() -> list[LiveWatchlistCandidate]:
    return [
        LiveWatchlistCandidate(
            symbol="NVDA",
            asset="Stock",
            asset_class="stock",
            horizon="day_trade",
            trigger="RVOL Breakout",
            trigger_type="rvol_breakout",
            priority_score=91,
            trigger_strength=94,
            account_fit="needs_smaller_expression",
            account_fit_label="Needs smaller expression",
            suggested_expression="Defined-risk spread or alert-only watch",
            agent_status="agents_reviewing",
            notify_status="pending_alert",
            notify_label="Pending alert",
            data_quality="real",
            reason="Small-account edge signal found. Requires spread, liquidity, and account risk validation.",
            risk_factors=["fast decay", "slippage", "account size mismatch"],
        ),
        LiveWatchlistCandidate(
            symbol="AMD",
            asset="Option / Stock",
            asset_class="option",
            horizon="swing",
            trigger="Options Flow",
            trigger_type="unusual_options_flow",
            priority_score=84,
            trigger_strength=86,
            account_fit="feasible_defined_risk",
            account_fit_label="Feasible defined-risk",
            suggested_expression="Debit spread if IV and spread pass",
            agent_status="confirmed",
            notify_status="alert_queued",
            notify_label="Alert queued",
            data_quality="partial",
            reason="Options flow and underlying momentum align, pending deeper options scanner.",
            risk_factors=["IV risk", "wide spread risk"],
        ),
        LiveWatchlistCandidate(
            symbol="BTC-USD",
            asset="Bitcoin",
            asset_class="crypto",
            horizon="intraday",
            trigger="Volatility Burst",
            trigger_type="crypto_volatility_burst",
            priority_score=82,
            trigger_strength=84,
            account_fit="risk_review",
            account_fit_label="Risk review",
            suggested_expression="Fractional spot or watch-only",
            agent_status="monitoring",
            notify_status="watch_only",
            notify_label="Watch only",
            data_quality="partial",
            reason="Crypto volatility is elevated; risk agent is monitoring before alert escalation.",
            risk_factors=["high volatility", "liquidation risk"],
        ),
    ]


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", service="edgesenseai-backend", version="0.1.0")


@app.get("/api/account-risk/profile", response_model=AccountRiskProfile)
def get_account_risk_profile():
    return _ACCOUNT_PROFILE


@app.put("/api/account-risk/profile", response_model=AccountRiskProfile)
def update_account_risk_profile(update: AccountRiskProfileUpdate):
    global _ACCOUNT_PROFILE
    current = _ACCOUNT_PROFILE.model_copy(deep=True)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(current, field, value)
    current.source = "manual_profile_session"
    current.paper_only = True
    current.last_updated = datetime.utcnow()
    _ACCOUNT_PROFILE = current
    return _ACCOUNT_PROFILE


@app.get("/api/live-watchlist/latest", response_model=LiveWatchlistResponse)
def get_live_watchlist():
    candidates = live_candidates()
    return LiveWatchlistResponse(
        summary=LiveWatchlistSummary(
            triggered_now=18,
            high_conviction=len([c for c in candidates if c.priority_score >= 85]),
            alerts_sent_today=7,
            average_priority_score=int(sum(c.priority_score for c in candidates) / len(candidates)),
            strongest_trigger=candidates[0].trigger,
        ),
        agents=agents(),
        candidates=candidates,
    )


@app.post("/api/live-watchlist/scan", response_model=LiveWatchlistResponse)
def scan_live_watchlist():
    return get_live_watchlist()


@app.get("/api/edge-signals/latest", response_model=EdgeSignalsResponse)
def get_edge_signals():
    return EdgeSignalsResponse(signals=edge_signals())


@app.post("/api/edge-signals/scan", response_model=EdgeSignalsResponse)
def scan_edge_signals():
    return get_edge_signals()


@app.get("/api/command-center", response_model=CommandCenterResponse)
def get_command_center():
    recommendations = [
        Recommendation(
            symbol="AMD",
            asset_class="option",
            horizon="swing",
            final_decision="watch",
            final_score=78,
            confidence=0.72,
            reward_risk_ratio=3.1,
            account_fit="feasible_defined_risk",
            model_stack=["ARIMAX", "GARCH", "HMM", "XGBoost"],
            reason="Options flow and underlying trend are supportive, but IV/spread confirmation is required.",
            risk_factors=["IV risk", "earnings/event risk"],
        ),
        Recommendation(
            symbol="BTC-USD",
            asset_class="crypto",
            horizon="intraday",
            final_decision="risk_review",
            final_score=74,
            confidence=0.68,
            reward_risk_ratio=2.8,
            account_fit="risk_review",
            model_stack=["ARIMAX", "Kalman", "GARCH", "XGBoost"],
            reason="Momentum is strong but volatility regime is elevated for a small account.",
            risk_factors=["liquidation cascade", "volatility spike"],
        ),
    ]
    return CommandCenterResponse(
        account_profile=_ACCOUNT_PROFILE,
        top_recommendations=recommendations,
        urgent_edge_alerts=edge_signals(),
        agents=agents(),
    )
