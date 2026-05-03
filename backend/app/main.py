from datetime import datetime
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent_scorecards import router as agent_scorecards_router
from app.api.routes.ai_ops import router as ai_ops_router
from app.api.routes.auto_run import router as auto_run_router
from app.api.routes.data_quality import router as data_quality_router
from app.api.routes.data_sources import router as data_sources_router
from app.api.routes.decision_workflows import router as decision_workflows_router
from app.api.routes.edge_radar import router as edge_radar_router
from app.api.routes.feature_store import router as feature_store_router
from app.api.routes.historical_analogs import router as historical_analogs_router
from app.api.routes.llm_gateway import router as llm_gateway_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.market_radar import router as market_radar_router
from app.api.routes.market_scanner import router as market_scanner_router
from app.api.routes.memory import router as memory_router
from app.api.routes.model_runs import router as model_runs_router
from app.api.routes.paper_trading_lifecycle import router as paper_trading_lifecycle_router
from app.api.routes.recommendation_lifecycle import router as recommendation_lifecycle_router
from app.api.routes.signal_orchestration import router as signal_orchestration_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.strategy_workflows import router as strategy_workflows_router
from app.api.routes.trade_quality import router as trade_quality_router
from app.api.routes.watchlists import router as watchlists_router
from app.core.settings import settings
from app.data_providers.base import MarketCandlesResponse, MarketSnapshot
from app.data_providers.provider_factory import get_market_data_provider
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, metrics_response
from app.schemas import (
    AccountRiskProfile,
    AccountRiskProfileUpdate,
    AgentStatus,
    CommandCenterResponse,
    EdgeSignalsResponse,
    LiveWatchlistResponse,
    LiveWatchlistSummary,
    SourceDataStatus,
)
from app.services.account_feasibility_service import AccountFeasibilityResult, evaluate_account_feasibility
from app.services.backtesting_service import BacktestingResponse, build_backtesting_summary
from app.services.decision_workflow_service import DecisionWorkflowRunRequest, run_decision_workflow
from app.services.edge_signal_service import build_edge_signals
from app.services.feature_engineering_service import EngineeredFeatures, build_features
from app.services.health_service import get_health_snapshot
from app.services.journal_service import JournalSummary, build_journal_summary
from app.services.live_watchlist_service import build_live_candidates
from app.services.market_regime_service import MarketRegimeResponse, build_market_regime
from app.services.model_lab_service import ModelLabRunRequest, ModelLabRunResponse, run_model_lab_workflow
from app.services.model_pipeline_service import ModelPipelineResult, run_model_pipeline
from app.services.model_status_service import ModelStatusResponse, build_model_status_response
from app.services.risk_engine_service import RiskCheckResult, evaluate_trade_risk

logger = logging.getLogger(__name__)

app = FastAPI(title="EdgeSenseAI Backend", version="0.8.1", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_middleware(request, call_next):
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception("Unhandled error during request processing")
        raise
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        endpoint = getattr(route, "path", None) or request.url.path
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
        REQUEST_COUNT.labels(request.method, endpoint, str(status_code)).inc()


app.include_router(market_data_router, prefix="/api")
app.include_router(data_sources_router, prefix="/api")
app.include_router(watchlists_router, prefix="/api")
app.include_router(paper_trading_lifecycle_router, prefix="/api")
app.include_router(recommendation_lifecycle_router, prefix="/api")
app.include_router(agent_scorecards_router, prefix="/api")
app.include_router(historical_analogs_router, prefix="/api")
app.include_router(market_radar_router, prefix="/api")
app.include_router(trade_quality_router, prefix="/api")
app.include_router(signal_orchestration_router, prefix="/api")
app.include_router(edge_radar_router, prefix="/api")
app.include_router(ai_ops_router, prefix="/api")
app.include_router(data_quality_router, prefix="/api")
app.include_router(feature_store_router, prefix="/api")
app.include_router(model_runs_router, prefix="/api")
app.include_router(llm_gateway_router, prefix="/api")
app.include_router(strategies_router, prefix="/api")
app.include_router(strategy_workflows_router, prefix="/api")
app.include_router(market_scanner_router, prefix="/api")
app.include_router(auto_run_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(decision_workflows_router, prefix="/api")

_ACCOUNT_PROFILE = AccountRiskProfile()
_COMMAND_CENTER_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMD", "BTC-USD"]


def agents() -> list[AgentStatus]:
    return [
        AgentStatus(name="Data Quality Agent", role="data_quality", status="source_backed", status_label="Checking source quality"),
        AgentStatus(name="Feature Store Agent", role="feature_store", status="source_backed", status_label="Building feature rows"),
        AgentStatus(name="Model Orchestrator", role="model_orchestrator", status="source_backed", status_label="Running eligible models"),
        AgentStatus(name="Risk Agent", role="account_risk", status="checked", status_label="Risk gate required"),
        AgentStatus(name="Recommendation Engine", role="recommendation_engine", status="source_backed", status_label="Ranking candidates"),
    ]


def _build_decision_command_center() -> CommandCenterResponse:
    workflow = run_decision_workflow(
        DecisionWorkflowRunRequest(
            symbols=_COMMAND_CENTER_SYMBOLS,
            asset_class="stock",
            horizon="swing",
            source="auto",
            max_candidates=5,
            allow_mock=False,
        ),
        account_profile=_ACCOUNT_PROFILE,
    )
    source_status = [
        SourceDataStatus(
            symbol=candidate.symbol,
            provider=candidate.provider,
            data_quality=candidate.data_quality,
            is_mock=candidate.source == "mock",
            error="; ".join(candidate.blockers) if candidate.blockers else None,
        )
        for candidate in workflow.candidates
    ]
    return CommandCenterResponse(
        account_profile=_ACCOUNT_PROFILE,
        top_action=workflow.top_action,
        top_recommendations=workflow.recommendations,
        urgent_edge_alerts=[],
        agents=agents(),
        source_data_status=source_status,
        dashboard_mode=f"decision_workflow:{workflow.status}",
        cost_usage_message=f"Decision workflow {workflow.run_id} processed {len(workflow.symbols_requested)} symbols through source data, feature store, model orchestrator, and risk-gated watch output.",
    )


@app.get("/")
def root():
    return {"message": "EdgeSenseAI backend running", "product": "EdgeSenseAI", "version": "0.8.1"}


@app.get("/health")
def health():
    return get_health_snapshot()


@app.get("/metrics")
def metrics():
    return metrics_response()


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
    alert_count = len([candidate for candidate in candidates if candidate.notify_status in {"alert_queued", "pending_alert"}])
    high_conviction = len([candidate for candidate in candidates if candidate.priority_score >= 85])
    return LiveWatchlistResponse(
        mode="prototype_candidates_not_live_signals",
        live_trading_enabled=False,
        execution_enabled=False,
        summary=LiveWatchlistSummary(
            triggered_now=len(candidates),
            high_conviction=high_conviction,
            alerts_sent_today=alert_count,
            average_priority_score=int(sum(c.priority_score for c in candidates) / len(candidates)),
            strongest_trigger=candidates[0].trigger,
        ),
        agents=agents(),
        candidates=candidates,
        disclaimer="Prototype candidates only. Not live market-triggered alerts.",
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


@app.get("/api/market/snapshots", response_model=list[MarketSnapshot])
def get_market_snapshots():
    return get_market_data_provider().get_watchlist_snapshots()


@app.get("/api/market/{symbol}/snapshot", response_model=MarketSnapshot)
def get_market_snapshot(symbol: str, provider: str = "mock"):
    asset_class = "crypto" if "-USD" in symbol.upper() else "stock"
    return get_market_data_provider(provider).get_snapshot(symbol.upper(), asset_class=asset_class)


@app.get("/api/market/{symbol}/candles", response_model=MarketCandlesResponse)
def get_market_candles(symbol: str, period: str = "1mo", interval: str = "1d", provider: str = "mock"):
    asset_class = "crypto" if "-USD" in symbol.upper() else "stock"
    return get_market_data_provider(provider).get_candles(symbol.upper(), period=period, interval=interval, asset_class=asset_class)


@app.get("/api/features/{symbol}", response_model=EngineeredFeatures)
def get_features(symbol: str):
    snapshot = get_market_data_provider().get_snapshot(symbol.upper())
    return build_features(snapshot)


@app.get("/api/model-pipeline/{symbol}", response_model=ModelPipelineResult)
def get_model_pipeline(symbol: str):
    snapshot = get_market_data_provider().get_snapshot(symbol.upper())
    return run_model_pipeline(snapshot)


@app.post("/api/model-lab/run", response_model=ModelLabRunResponse)
def run_model_lab(request: ModelLabRunRequest):
    return run_model_lab_workflow(request)


@app.get("/api/account-feasibility/{symbol}", response_model=AccountFeasibilityResult)
def get_account_feasibility(symbol: str):
    snapshot = get_market_data_provider().get_snapshot(symbol.upper())
    return evaluate_account_feasibility(snapshot.symbol, snapshot.current_price, _ACCOUNT_PROFILE)


@app.get("/api/risk-check/{symbol}", response_model=RiskCheckResult)
def get_risk_check(symbol: str):
    snapshot = get_market_data_provider().get_snapshot(symbol.upper())
    entry_price = snapshot.current_price
    stop_loss = entry_price * 0.972
    target_price = entry_price * 1.056
    return evaluate_trade_risk(entry_price, stop_loss, target_price, _ACCOUNT_PROFILE)


@app.get("/api/market-regime", response_model=MarketRegimeResponse)
def get_market_regime():
    return build_market_regime()


@app.get("/api/backtesting/summary", response_model=BacktestingResponse)
def get_backtesting_summary():
    return build_backtesting_summary()


@app.get("/api/journal/summary", response_model=JournalSummary)
def get_journal_summary():
    return build_journal_summary()


@app.get("/api/command-center", response_model=CommandCenterResponse)
def get_command_center():
    return _build_decision_command_center()
