from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AccountRiskProfile,
    AccountRiskProfileUpdate,
    AgentStatus,
    CommandCenterResponse,
    EdgeSignalsResponse,
    HealthResponse,
    LiveWatchlistResponse,
    LiveWatchlistSummary,
)
from app.services.edge_signal_service import build_edge_signals
from app.services.live_watchlist_service import build_live_candidates
from app.services.model_status_service import ModelStatusResponse, build_model_status_response
from app.services.recommendation_engine_service import (
    build_alternative_recommendations,
    build_top_action_recommendation,
)

app = FastAPI(title="EdgeSenseAI Backend", version="0.2.0")

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
        AgentStatus(name="Recommendation Engine", role="recommendation_engine", status="prototype", status_label="Ranking candidates"),
    ]


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", service="edgesenseai-backend", version="0.2.0")


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
    candidates = build_live_candidates()
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
    return EdgeSignalsResponse(signals=build_edge_signals())


@app.post("/api/edge-signals/scan", response_model=EdgeSignalsResponse)
def scan_edge_signals():
    return get_edge_signals()


@app.get("/api/models/status", response_model=ModelStatusResponse)
def get_model_status():
    return build_model_status_response()


@app.get("/api/command-center", response_model=CommandCenterResponse)
def get_command_center():
    return CommandCenterResponse(
        account_profile=_ACCOUNT_PROFILE,
        top_action=build_top_action_recommendation(),
        top_recommendations=build_alternative_recommendations(),
        urgent_edge_alerts=build_edge_signals(),
        agents=agents(),
    )
