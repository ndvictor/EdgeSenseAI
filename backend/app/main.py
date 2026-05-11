from datetime import datetime
import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.api.routes.agent_scorecards import router as agent_scorecards_router
from app.api.routes.agent_validation import router as agent_validation_router
from app.api.routes.ai_ops import router as ai_ops_router
from app.api.routes.auto_run import router as auto_run_router
from app.api.routes.backtesting import router as backtesting_router
from app.api.routes.candidates_status import router as candidates_status_router
from app.api.routes.candidate_universe import router as candidate_universe_router
from app.api.routes.capital_allocation import router as capital_allocation_router
from app.api.routes.journal_outcomes import router as journal_outcomes_router
from app.api.routes.platform_readiness import router as platform_readiness_router
from app.api.routes.final_readiness import router as final_readiness_router
from app.api.routes.integration_checks import router as integration_checks_router
from app.api.routes.lab_inventory import router as lab_inventory_router
from app.api.routes.settings import router as settings_router
from app.api.routes.tracing import router as tracing_router
from app.api.routes.data_freshness import router as data_freshness_router
from app.api.routes.data_quality import router as data_quality_router
from app.api.routes.data_sources import router as data_sources_router
from app.api.routes.data_ingestion import router as data_ingestion_router
from app.api.routes.normalization_status import router as normalization_status_router
from app.api.routes.decision_workflows import router as decision_workflows_router
from app.api.routes.edge_radar import router as edge_radar_router
from app.api.routes.event_scanner_models import router as event_scanner_router
from app.api.routes.feature_store import router as feature_store_router
from app.api.routes.historical_analogs import router as historical_analogs_router
from app.api.routes.historical_similarity import router as historical_similarity_router
from app.api.routes.llm_budget_gate import router as llm_budget_gate_router
from app.api.routes.memory_update import router as memory_update_router
from app.api.routes.model_registry import router as model_registry_router
from app.api.routes.model_strategy_update import router as model_strategy_update_router
from app.api.routes.performance_drift import router as performance_drift_router
from app.api.routes.research_priority import router as research_priority_router
from app.api.routes.llm_gateway import router as llm_gateway_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.market_radar import router as market_radar_router
from app.api.routes.market_regime_model import router as market_regime_model_router
from app.api.routes.market_scanner import router as market_scanner_router
from app.api.routes.memory import router as memory_router
from app.api.routes.meta_model_ensemble import router as meta_model_router
from app.api.routes.model_runs import router as model_runs_router
from app.api.routes.model_selection import router as model_selection_router
from app.api.routes.no_trade import router as no_trade_router
from app.api.routes.paper_autonomy import router as paper_autonomy_router
from app.api.routes.paper_trading_lifecycle import router as paper_trading_lifecycle_router
from app.api.routes.recommendation_lifecycle import router as recommendation_lifecycle_router
from app.api.routes.recommendation_pipeline import router as recommendation_pipeline_router
from app.api.routes.risk_manager import router as risk_manager_router
from app.api.routes.signal_scoring import router as signal_scoring_router
from app.api.routes.runtime import router as runtime_router
from app.api.routes.signal_orchestration import router as signal_orchestration_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.strategy_debate import router as strategy_debate_router
from app.api.routes.strategy_ranking import router as strategy_ranking_router
from app.api.routes.strategy_workflows import router as strategy_workflows_router
from app.api.routes.trade_quality import router as trade_quality_router
from app.api.routes.tradenow import router as tradenow_router
from app.api.routes.execution import router as execution_router
from app.api.routes.workflow_router import router as workflow_router_router
from app.api.routes.session_router import router as session_router_router
from app.api.routes.strategy_eligibility import router as strategy_eligibility_router
from app.api.routes.trigger_rules import router as trigger_rules_router
from app.api.routes.trigger_monitoring import router as trigger_monitoring_router
from app.api.routes.execution_planner import router as execution_planner_router
from app.api.routes.position_monitoring import router as position_monitoring_router
from app.api.routes.close_position import router as close_position_router
from app.api.routes.post_trade_evaluation import router as post_trade_evaluation_router
from app.api.routes.learning_loop import router as learning_loop_router
from app.api.routes.workflow_runbook import router as workflow_runbook_router
from app.api.routes.agent_runtime import router as agent_runtime_router
from app.api.routes.proof_registry import router as proof_registry_router
from app.api.routes.model_evidence import router as model_evidence_router
from app.api.routes.strategy_evidence import router as strategy_evidence_router
from app.api.routes.qlib_integration import router as qlib_integration_router
from app.api.routes.daytrading_v1 import router as daytrading_v1_router
from app.api.routes.workflow_orchestrator import router as workflow_orchestrator_router
from app.api.routes.workflow_governance import router as workflow_governance_router
from app.api.routes.worker_status import router as worker_status_router
from app.api.routes.approval_queue import router as approval_queue_router
from app.api.routes.audit_log import router as audit_log_router
from app.api.routes.workflow_scheduler import router as workflow_scheduler_router
from app.api.routes.universe_discovery import router as universe_discovery_router
from app.api.routes.universe_selection import router as universe_selection_router
from app.api.routes.upper_workflow import router as upper_workflow_router
from app.api.routes.watchlists import router as watchlists_router
from app.api.routes.pipeline_automation import router as pipeline_automation_router
from app.api.routes.promotion_center import router as promotion_center_router
from app.core.effective_runtime import effective_str
from app.core.settings import settings
from app.data_providers.base import MarketCandlesResponse, MarketSnapshot
from app.data_providers.provider_factory import get_market_data_provider
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, metrics_response
from app.schemas import (
    AccountRiskProfile,
    AccountRiskProfileUpdate,
    AgentStatus,
    CommandCenterDataSourceConfirmation,
    CommandCenterResponse,
    EdgeSignalsResponse,
    LiveWatchlistResponse,
    LiveWatchlistSummary,
    SourceDataStatus,
)
from app.services.account_feasibility_service import AccountFeasibilityResult, evaluate_account_feasibility
from app.services.candidate_universe_service import get_candidate_symbols
from app.services.decision_workflow_service import DecisionWorkflowRunRequest, get_latest_decision_workflow_run, run_decision_workflow
from app.services.universe_selection_service import UniverseSelectionRequest, run_universe_selection
from app.services.edge_signal_service import build_edge_signals
from app.services.feature_engineering_service import EngineeredFeatures, build_features
from app.services.health_service import get_health_snapshot
from app.core.runtime_settings_store import load_runtime_settings
from app.services.alpaca_paper_account_service import get_alpaca_paper_snapshot
from app.services.journal_service import JournalSummary, build_journal_summary
from app.services.live_watchlist_service import build_live_candidates
from app.services.market_regime_service import MarketRegimeResponse, build_market_regime
from app.services.model_lab_service import ModelLabRunRequest, ModelLabRunResponse, run_model_lab_workflow
from app.services.model_pipeline_service import ModelPipelineResult, run_model_pipeline
from app.services.model_status_service import ModelStatusResponse, build_model_status_response
from app.services.risk_engine_service import RiskCheckResult, evaluate_trade_risk

logger = logging.getLogger(__name__)

app = FastAPI(title="EdgeSenseAI Backend", version="0.8.1", docs_url="/docs", redoc_url="/redoc")

_PRODUCTION_ALLOWED_RUNTIME_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/health"),
        ("GET", "/api/platform-readiness/status"),
        ("GET", "/api/final-readiness/status"),
        ("POST", "/api/workflow-orchestrator/run"),
        ("GET", "/api/worker-status/latest"),
        ("POST", "/api/scanner/run"),
        ("GET", "/api/promotion/strategies/status"),
        ("GET", "/api/promotion/models/status"),
        ("GET", "/api/v1/daytrading/status"),
        ("POST", "/api/v1/daytrading/scanner/run"),
        ("GET", "/api/v1/daytrading/scanner/latest"),
        ("GET", "/api/v1/daytrading/workers/latest"),
        ("POST", "/api/v1/daytrading/workflow/run"),
        ("GET", "/api/v1/daytrading/workflow/latest"),
        ("GET", "/api/v1/daytrading/recommendation/latest"),
        ("GET", "/api/v1/daytrading/evidence/strategies"),
        ("GET", "/api/v1/daytrading/evidence/models"),
        ("GET", "/api/v1/daytrading/risk/status"),
        ("GET", "/api/v1/daytrading/execution-boundary"),
        ("GET", "/api/v1/daytrading/contracts/routes"),
        ("GET", "/api/v1/daytrading/paper-autonomy/status"),
        ("GET", "/api/v1/daytrading/paper-autonomy/orders"),
        ("GET", "/api/v1/daytrading/paper-autonomy/positions/open"),
        ("GET", "/api/v1/daytrading/paper-autonomy/positions/closed"),
        ("GET", "/api/v1/daytrading/paper-autonomy/learning/outcomes"),
        ("GET", "/api/v1/daytrading/paper-autonomy/control-tower"),
        ("GET", "/api/v1/daytrading/settings/gates"),
        ("PUT", "/api/v1/daytrading/settings/gates"),
    }
)

_LEGACY_RUNTIME_DISABLED_PAYLOAD = {
    "status": "disabled",
    "reason": "legacy_runtime_disabled_real_data_only",
    "items": [],
    "symbol": None,
}


def _legacy_runtime_disabled_response(request: Request) -> JSONResponse:
    """Return 410 with the same CORS surface as normal responses.

    `legacy_runtime_disabled_middleware` runs outside `CORSMiddleware`'s response
    path for short-circuited requests; without these headers the browser hides the
    real HTTP status and reports TypeError: Failed to fetch.
    """
    headers: dict[str, str] = {}
    origin = (request.headers.get("origin") or "").strip()
    if origin and origin in settings.cors_origins:
        headers["access-control-allow-origin"] = origin
        headers["access-control-allow-credentials"] = "true"
        headers["vary"] = "Origin"
    return JSONResponse(status_code=410, content=_LEGACY_RUNTIME_DISABLED_PAYLOAD, headers=headers)


def _production_api_allowlist_enabled() -> bool:
    return (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower() == "production"

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


@app.middleware("http")
async def legacy_runtime_disabled_middleware(request, call_next):
    path = request.url.path.rstrip("/") or "/"
    method = request.method.upper()
    if not _production_api_allowlist_enabled() or method == "OPTIONS":
        return await call_next(request)
    if (method, path) in _PRODUCTION_ALLOWED_RUNTIME_ROUTES:
        return await call_next(request)
    return _legacy_runtime_disabled_response(request)


app.include_router(backtesting_router, prefix="/api")
app.include_router(market_data_router, prefix="/api")
app.include_router(data_sources_router, prefix="/api")
app.include_router(data_ingestion_router, prefix="/api")
app.include_router(normalization_status_router, prefix="/api")
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
app.include_router(model_registry_router, prefix="/api")
app.include_router(llm_gateway_router, prefix="/api")
app.include_router(strategies_router, prefix="/api")
app.include_router(strategy_workflows_router, prefix="/api")
app.include_router(market_scanner_router, prefix="/api")
app.include_router(auto_run_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(decision_workflows_router, prefix="/api")
app.include_router(candidate_universe_router, prefix="/api")
app.include_router(candidates_status_router, prefix="/api")
app.include_router(runtime_router, prefix="/api")
app.include_router(universe_discovery_router, prefix="/api")
app.include_router(universe_selection_router, prefix="/api")
app.include_router(data_freshness_router, prefix="/api")
app.include_router(market_regime_model_router, prefix="/api")
app.include_router(strategy_debate_router, prefix="/api")
app.include_router(strategy_ranking_router, prefix="/api")
app.include_router(model_selection_router, prefix="/api")
app.include_router(upper_workflow_router, prefix="/api")
app.include_router(historical_similarity_router, prefix="/api")
app.include_router(trigger_rules_router, prefix="/api")
app.include_router(event_scanner_router, prefix="/api")
app.include_router(signal_scoring_router, prefix="/api")
app.include_router(meta_model_router, prefix="/api")
app.include_router(llm_budget_gate_router, prefix="/api")
app.include_router(agent_validation_router, prefix="/api")
app.include_router(risk_manager_router, prefix="/api")
app.include_router(no_trade_router, prefix="/api")
app.include_router(capital_allocation_router, prefix="/api")
app.include_router(recommendation_pipeline_router, prefix="/api")
app.include_router(journal_outcomes_router, prefix="/api")
app.include_router(performance_drift_router, prefix="/api")
app.include_router(research_priority_router, prefix="/api")
app.include_router(model_strategy_update_router, prefix="/api")
app.include_router(memory_update_router, prefix="/api")
app.include_router(platform_readiness_router, prefix="/api")
app.include_router(final_readiness_router, prefix="/api")
app.include_router(lab_inventory_router, prefix="/api")
app.include_router(integration_checks_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(tracing_router, prefix="/api")
app.include_router(tradenow_router, prefix="/api")
app.include_router(execution_router, prefix="/api")
app.include_router(workflow_router_router, prefix="/api")
app.include_router(session_router_router, prefix="/api")
app.include_router(strategy_eligibility_router, prefix="/api")
app.include_router(trigger_monitoring_router, prefix="/api")
app.include_router(execution_planner_router, prefix="/api")
app.include_router(position_monitoring_router, prefix="/api")
app.include_router(close_position_router, prefix="/api")
app.include_router(post_trade_evaluation_router, prefix="/api")
app.include_router(learning_loop_router, prefix="/api")
app.include_router(paper_autonomy_router, prefix="/api/v1")
app.include_router(workflow_runbook_router, prefix="/api")
app.include_router(agent_runtime_router, prefix="/api")
app.include_router(proof_registry_router, prefix="/api")
app.include_router(model_evidence_router, prefix="/api")
app.include_router(strategy_evidence_router, prefix="/api")
app.include_router(qlib_integration_router, prefix="/api")
app.include_router(workflow_orchestrator_router, prefix="/api")
app.include_router(daytrading_v1_router, prefix="/api/v1")
app.include_router(worker_status_router, prefix="/api")
app.include_router(pipeline_automation_router, prefix="/api")
app.include_router(promotion_center_router, prefix="/api")
app.include_router(workflow_governance_router, prefix="/api")
app.include_router(approval_queue_router, prefix="/api")
app.include_router(audit_log_router, prefix="/api")
app.include_router(workflow_scheduler_router, prefix="/api")

_ACCOUNT_PROFILE = AccountRiskProfile()


def _effective_account_profile() -> AccountRiskProfile:
    """
    Build an account profile from:
    - Alpaca paper snapshot (equity/buying power/cash) when available
    - runtime_settings.json risk thresholds (min RR, max risk, etc.)
    Fallbacks to the legacy in-memory `_ACCOUNT_PROFILE` defaults.
    """
    runtime = load_runtime_settings()

    # Thresholds from runtime settings (with fallback to current profile defaults)
    max_risk_per_trade_percent = float(runtime.get("MAX_RISK_PER_TRADE_PERCENT", _ACCOUNT_PROFILE.max_risk_per_trade_percent))
    max_daily_loss_percent = float(runtime.get("MAX_DAILY_LOSS_PERCENT", _ACCOUNT_PROFILE.max_daily_loss_percent))
    max_position_size_percent = float(runtime.get("MAX_POSITION_SIZE_PERCENT", _ACCOUNT_PROFILE.max_position_size_percent))
    min_reward_risk_ratio = float(runtime.get("MIN_REWARD_RISK_RATIO", _ACCOUNT_PROFILE.min_reward_risk_ratio))

    # Account balances from Alpaca when available
    equity = _ACCOUNT_PROFILE.account_equity
    buying_power = _ACCOUNT_PROFILE.buying_power
    cash = _ACCOUNT_PROFILE.cash
    source = "risk_settings_only"
    try:
        snap = get_alpaca_paper_snapshot()
        if snap.account and snap.status == "connected":
            equity = snap.account.equity or equity
            buying_power = snap.account.buying_power or buying_power
            cash = snap.account.cash or cash
            source = "alpaca_paper+runtime_settings"
    except Exception:
        pass

    return AccountRiskProfile(
        account_mode=_ACCOUNT_PROFILE.account_mode,
        account_equity=float(equity or 0),
        buying_power=float(buying_power or 0),
        cash=float(cash or 0),
        max_risk_per_trade_percent=max_risk_per_trade_percent,
        max_daily_loss_percent=max_daily_loss_percent,
        max_position_size_percent=max_position_size_percent,
        min_reward_risk_ratio=min_reward_risk_ratio,
        preferred_risk_style=_ACCOUNT_PROFILE.preferred_risk_style,
        paper_only=True,
        source=source,
        last_updated=_ACCOUNT_PROFILE.last_updated,
    )


def agents() -> list[AgentStatus]:
    return [
        AgentStatus(name="Data Quality Agent", role="data_quality", status="source_backed", status_label="Checking source quality"),
        AgentStatus(name="Feature Store Agent", role="feature_store", status="source_backed", status_label="Building feature rows"),
        AgentStatus(name="Model Orchestrator", role="model_orchestrator", status="source_backed", status_label="Running eligible models"),
        AgentStatus(name="Risk Agent", role="account_risk", status="checked", status_label="Risk gate required"),
        AgentStatus(name="Recommendation Engine", role="recommendation_engine", status="source_backed", status_label="Waiting for selected candidates"),
    ]


def _command_center_data_source_confirmation(
    effective_profile: AccountRiskProfile,
    *,
    universe_source: str = "auto",
    universe_horizon: str = "swing",
    decision_source: str = "auto",
    decision_horizon: str = "swing",
    universe_run_id: str | None = None,
    decision_run_id: str | None = None,
    candidate_seeds: list[str] | None = None,
    symbols_after_universe: list[str] | None = None,
) -> CommandCenterDataSourceConfirmation:
    """Surface effective runtime feeds (market/news) and workflow routing for auditability."""
    from app.core.effective_runtime import effective_bool, effective_str, news_provider_priority_from_runtime
    from app.services.market_data_service import market_data_provider_priority_from_runtime

    primary = (effective_str("MARKET_DATA_PROVIDER") or "not_configured").lower().strip()
    if primary == "disabled_test_provider":
        primary = "not_configured"
    fallback_chain = [provider for provider in market_data_provider_priority_from_runtime() if provider != "disabled_test_provider"]
    return CommandCenterDataSourceConfirmation(
        market_data_primary=primary,
        market_data_fallback_chain=fallback_chain,
        universe_selection_source=universe_source,
        universe_selection_horizon=universe_horizon,
        decision_workflow_source=decision_source,
        decision_workflow_horizon=decision_horizon,
        news_enabled=bool(effective_bool("NEWS_PROVIDER_ENABLED")),
        news_primary=(effective_str("NEWS_PROVIDER_PRIMARY") or "none").lower().strip(),
        news_fallback_chain=list(news_provider_priority_from_runtime()),
        account_profile_data_source=effective_profile.source,
        universe_run_id=universe_run_id,
        decision_workflow_run_id=decision_run_id,
        candidate_seeds=list(candidate_seeds or []),
        symbols_after_universe=list(symbols_after_universe or []),
    )


def _build_decision_command_center() -> CommandCenterResponse:
    """Build Command Center response - READ ONLY, does not run workflows.

    Uses latest stored workflow run if available. If candidates exist but
    no workflow has been run, shows candidates_ready_not_ranked state.
    """
    # Pull active candidates from candidate universe
    symbols = get_candidate_symbols()
    effective_profile = _effective_account_profile()

    if not symbols:
        # No candidates selected - return no_action state
        return CommandCenterResponse(
            account_profile=effective_profile,
            top_action=None,
            top_recommendations=[],
            urgent_edge_alerts=[],
            agents=agents(),
            source_data_status=[],
            dashboard_mode="no_symbols_selected",
            cost_usage_message="No candidates selected. Run Universe Selection to create a watchlist, or add candidates manually from Stocks, Watchlist, or Scanner.",
            data_source_confirmation=_command_center_data_source_confirmation(effective_profile),
        )

    # Try to use latest stored workflow run (read-only)
    latest_workflow = get_latest_decision_workflow_run()

    if latest_workflow is None:
        # Candidates exist but workflow has not been run
        return CommandCenterResponse(
            account_profile=effective_profile,
            top_action=None,
            top_recommendations=[],
            urgent_edge_alerts=[],
            agents=agents(),
            source_data_status=[],
            dashboard_mode="candidates_ready_not_ranked",
            cost_usage_message=f"{len(symbols)} candidate(s) ready but decision workflow has not been run. Go to Candidates page to run workflow, or run Universe Selection to create a new watchlist.",
            data_source_confirmation=_command_center_data_source_confirmation(
                effective_profile,
                candidate_seeds=symbols,
            ),
        )

    # Use latest stored workflow results
    source_status = [
        SourceDataStatus(
            symbol=candidate.symbol,
            provider=candidate.provider,
            data_quality=candidate.data_quality,
            is_non_real=False,
            error="; ".join(candidate.blockers) if candidate.blockers else None,
            pipeline_source=candidate.source,
        )
        for candidate in latest_workflow.candidates
    ]

    # Check if workflow data is stale (older than 5 minutes)
    from datetime import datetime
    workflow_age_seconds = (datetime.utcnow() - latest_workflow.completed_at).total_seconds() if latest_workflow.completed_at else 0
    is_stale = workflow_age_seconds > 300  # 5 minutes

    stale_message = " (Data may be stale - consider re-running workflow)" if is_stale else ""

    return CommandCenterResponse(
        account_profile=effective_profile,
        top_action=latest_workflow.top_action,
        top_recommendations=latest_workflow.recommendations,
        urgent_edge_alerts=[],
        agents=agents(),
        source_data_status=source_status,
        dashboard_mode=f"decision_workflow:{latest_workflow.status}",
        cost_usage_message=f"Latest workflow {latest_workflow.run_id} completed {int(workflow_age_seconds)}s ago.{stale_message} {len([c for c in latest_workflow.candidates if c.status == 'candidate_ready'])} passed source-backed quality and model thresholds.",
        data_source_confirmation=_command_center_data_source_confirmation(
            effective_profile,
            decision_source=latest_workflow.source,
            decision_horizon=str(latest_workflow.horizon),
            decision_run_id=latest_workflow.run_id,
            candidate_seeds=symbols,
            symbols_after_universe=list(latest_workflow.symbols_requested or []),
        ),
    )


def _run_command_center_workflow() -> CommandCenterResponse:
    """Explicitly run universe selection, then decision workflow on the ranked symbols."""
    raw_seeds = get_candidate_symbols()
    seeds = [
        str(s).strip().upper()
        for s in raw_seeds
        if s and str(s).strip().upper() not in {"", "CANDIDATE_UNIVERSE_EMPTY"}
    ]
    effective_profile = _effective_account_profile()
    max_decision = 5

    if not seeds:
        return CommandCenterResponse(
            account_profile=effective_profile,
            top_action=None,
            top_recommendations=[],
            urgent_edge_alerts=[],
            agents=agents(),
            source_data_status=[],
            dashboard_mode="no_symbols_selected",
            cost_usage_message="No candidates selected. Add symbols from Stocks search, Watchlist, Scanner, or Candidate Universe before ranking.",
            data_source_confirmation=_command_center_data_source_confirmation(effective_profile),
        )

    # Step 1: universe selection (freshness + weighted rank) — same starting point as orchestrator pipeline.
    universe_run_id: str | None = None
    symbols_for_decision = seeds[:max_decision]
    try:
        univ = run_universe_selection(
            UniverseSelectionRequest(
                symbols=seeds[:50],
                asset_class="stock",
                horizon="swing",
                source="auto",
                max_candidates=max_decision,
                min_score=50,
            )
        )
        universe_run_id = univ.run_id
        picked: list[str] = []
        for c in univ.selected_watchlist or []:
            sym = str(getattr(c, "symbol", "") or "").strip().upper()
            if sym and sym != "CANDIDATE_UNIVERSE_EMPTY" and sym not in picked:
                picked.append(sym)
        if len(picked) < max_decision and univ.ranked_candidates:
            for c in univ.ranked_candidates:
                sym = str(getattr(c, "symbol", "") or "").strip().upper()
                if sym and sym != "CANDIDATE_UNIVERSE_EMPTY" and sym not in picked:
                    picked.append(sym)
                if len(picked) >= max_decision:
                    break
        if picked:
            symbols_for_decision = picked[:max_decision]
    except Exception:
        symbols_for_decision = seeds[:max_decision]

    workflow = run_decision_workflow(
        DecisionWorkflowRunRequest(
            symbols=symbols_for_decision,
            asset_class="stock",
            horizon="swing",
            source="auto",
            max_candidates=max_decision,
        ),
        account_profile=effective_profile,
    )

    source_status = [
        SourceDataStatus(
            symbol=candidate.symbol,
            provider=candidate.provider,
            data_quality=candidate.data_quality,
            is_non_real=False,
            error="; ".join(candidate.blockers) if candidate.blockers else None,
            pipeline_source=candidate.source,
        )
        for candidate in workflow.candidates
    ]

    uni_note = f" After universe selection ({universe_run_id})." if universe_run_id else ""
    return CommandCenterResponse(
        account_profile=effective_profile,
        top_action=workflow.top_action,
        top_recommendations=workflow.recommendations,
        urgent_edge_alerts=[],
        agents=agents(),
        source_data_status=source_status,
        dashboard_mode=f"decision_workflow:{workflow.status}",
        cost_usage_message=(
            f"Workflow {workflow.run_id} just completed.{uni_note} "
            f"Decision pass used {len(symbols_for_decision)} symbol(s) post-universe. "
            f"{len([c for c in workflow.candidates if c.status == 'candidate_ready'])} passed source-backed quality and model thresholds."
        ),
        data_source_confirmation=_command_center_data_source_confirmation(
            effective_profile,
            universe_source="auto",
            universe_horizon="swing",
            decision_source=workflow.source,
            decision_horizon=str(workflow.horizon),
            universe_run_id=universe_run_id,
            decision_run_id=workflow.run_id,
            candidate_seeds=seeds,
            symbols_after_universe=list(symbols_for_decision),
        ),
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
    avg_priority = int(sum(c.priority_score for c in candidates) / len(candidates)) if candidates else 0
    strongest_trigger = candidates[0].trigger if candidates else "none"
    return LiveWatchlistResponse(
        mode="no_candidates" if not candidates else "candidate_universe_watch_only",
        live_trading_enabled=False,
        execution_enabled=False,
        summary=LiveWatchlistSummary(
            triggered_now=len(candidates),
            high_conviction=high_conviction,
            alerts_sent_today=alert_count,
            average_priority_score=avg_priority,
            strongest_trigger=strongest_trigger,
        ),
        agents=agents(),
        candidates=candidates,
        disclaimer="Watchlist-only. Rows are sourced from Candidate Universe until live signal engine is connected.",
    )


@app.post("/api/live-watchlist/scan", response_model=LiveWatchlistResponse)
def scan_live_watchlist():
    return get_live_watchlist()


@app.get("/api/edge-signals/latest", response_model=EdgeSignalsResponse)
def get_edge_signals():
    signals = build_edge_signals()
    status = "prototype_demo" if signals else "no_real_signal_source"
    return EdgeSignalsResponse(signals=signals, signal_source_status=status)


@app.post("/api/edge-signals/scan", response_model=EdgeSignalsResponse)
def scan_edge_signals():
    return get_edge_signals()


@app.get("/api/models/status", response_model=ModelStatusResponse)
def get_model_status():
    return build_model_status_response()


@app.get("/api/market/snapshots", response_model=list[MarketSnapshot])
def get_market_snapshots():
    return get_market_data_provider().get_watchlist_snapshots()


def _resolved_market_provider(provider: str | None) -> str:
    """Explicit query param wins; ``auto`` or omitted uses human primary from runtime."""
    if provider and provider.strip():
        p = provider.strip().lower()
        if p != "auto":
            if p == "disabled_test_provider":
                return "not_configured"
            return p
    primary = (effective_str("MARKET_DATA_PROVIDER") or "not_configured").lower().strip()
    return "not_configured" if primary == "disabled_test_provider" else primary


@app.get("/api/market/{symbol}/snapshot", response_model=MarketSnapshot)
def get_market_snapshot(symbol: str, provider: str | None = None):
    asset_class = "crypto" if "-USD" in symbol.upper() else "stock"
    return get_market_data_provider(_resolved_market_provider(provider)).get_snapshot(symbol.upper(), asset_class=asset_class)


@app.get("/api/market/{symbol}/candles", response_model=MarketCandlesResponse)
def get_market_candles(symbol: str, period: str = "1mo", interval: str = "1d", provider: str | None = None):
    asset_class = "crypto" if "-USD" in symbol.upper() else "stock"
    return get_market_data_provider(_resolved_market_provider(provider)).get_candles(
        symbol.upper(), period=period, interval=interval, asset_class=asset_class
    )


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


@app.get("/api/journal/summary", response_model=JournalSummary)
def get_journal_summary():
    return build_journal_summary()


@app.get("/api/command-center", response_model=CommandCenterResponse)
def get_command_center():
    """Get Command Center data - READ ONLY. Does not run workflows.

    Uses latest stored workflow run if available. If candidates exist but
    no workflow has been run, shows candidates_ready_not_ranked state.
    """
    return _build_decision_command_center()


@app.post("/api/command-center/run", response_model=CommandCenterResponse)
def post_command_center_run():
    """Explicitly run decision workflow on candidate universe and return Command Center response."""
    return _run_command_center_workflow()
