"""Upper Workflow Orchestration Service.

Implements the approved Adaptive Agentic Quant Workflow sequence:
1. Runtime cadence (already exists)
2. Data freshness check
3. Market regime model
4. Strategy debate
5. Strategy ranking
6. Model selection for top active strategy
7. Universe selection/watchlist builder
8. Historical similarity search (optional)
9. Trigger rules build (optional)
10. Event scanner (optional)
11. Signal scoring (optional)
12. Meta-model ensemble (optional)
13. Optional promotion to candidate universe

NO LLMs.
NO default symbols.
Live trading disabled, human approval required.
"""

from datetime import datetime, timezone
import logging
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.candidate_universe_service import add_candidate
from app.services.data_freshness_gate_service import (
    DataFreshnessCheckResponse,
    DataFreshnessCheckRequest,
    run_data_freshness_check,
    get_usable_symbols_from_latest_check,
)
from app.services.event_scanner_models_service import (
    EventScannerMatchedEvent,
    EventScannerRequest,
    EventScannerResponse,
    run_event_scanner,
)
from app.services.historical_similarity_service import (
    HistoricalSimilarityRequest,
    HistoricalSimilarityResponse,
    run_historical_similarity_search,
)
from app.services.market_regime_model_service import (
    MarketRegimeRequest,
    MarketRegimeResponse,
    run_market_regime_model,
)
from app.services.meta_model_ensemble_service import (
    MetaModelEnsembleRequest,
    MetaModelEnsembleResponse,
    run_meta_model_ensemble,
)
from app.services.model_selection_service import (
    ModelSelectionRequest,
    ModelSelectionResponse,
    run_model_selection,
)
from app.services.signal_scoring_service import (
    ScoredSignal,
    SignalScoringRequest,
    SignalScoringResponse,
    run_signal_scoring,
)
from app.services.strategy_debate_service import (
    StrategyDebateRequest,
    StrategyDebateResponse,
    run_strategy_debate,
)
from app.services.strategy_ranking_service import (
    StrategyRankingRequest,
    StrategyRankingResponse,
    run_strategy_ranking,
    get_top_strategy_from_ranking,
)
from app.services.timing_cadence_service import (
    RuntimeCadenceResponse,
    get_runtime_cadence,
)
from app.services.recommendation_pipeline_service import (
    RecommendationPipelineRequest,
    RecommendationPipelineResponse,
    run_recommendation_pipeline,
)
from app.services.tracing_service import trace_event, trace_workflow_step
from app.services.trigger_rules_service import (
    TriggerRuleBuildRequest,
    TriggerRuleBuildResponse,
    run_trigger_rule_build,
)
from app.services.universe_selection_service import (
    UniverseSelectionRequest,
    UniverseSelectionResponse,
    run_universe_selection,
)


class UpperWorkflowRequest(BaseModel):
    """Request to run the upper workflow."""

    model_config = ConfigDict(protected_namespaces=())

    symbols: list[str] = Field(default_factory=list, description="Explicit symbols. NO defaults.")
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    source: Literal["auto", "yfinance", "alpaca", "polygon", "mock"] = "auto"
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    account_equity: float | None = None
    buying_power: float | None = None
    max_risk_per_trade_percent: float | None = None
    allow_mock: bool = False
    promote_to_candidate_universe: bool = False
    min_data_freshness_score: int = 50  # Min score to proceed

    # Optional extended workflow steps (safe defaults)
    build_trigger_rules: bool = True  # Step 8
    run_event_scanner: bool = False   # Step 9 - requires trigger rules
    run_signal_scoring: bool = False  # Step 10 - requires events
    run_meta_model: bool = False      # Step 11 - requires scored signals
    run_recommendation_pipeline: bool = False  # Step 14-19 - requires meta-model signals


class UpperWorkflowStage(BaseModel):
    """Result of a single workflow stage."""

    stage: str
    status: Literal["completed", "skipped", "failed", "blocked"]
    run_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UpperWorkflowResponse(BaseModel):
    """Response from upper workflow run."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "failed", "blocked", "blocked_by_data_freshness"]
    market_phase: str
    active_loop: str
    stages: list[UpperWorkflowStage]
    data_freshness: DataFreshnessCheckResponse | None = None
    regime: MarketRegimeResponse | None = None
    strategy_debate: StrategyDebateResponse | None = None
    strategy_ranking: StrategyRankingResponse | None = None
    model_selection: ModelSelectionResponse | None = None
    universe_selection: UniverseSelectionResponse | None = None
    trigger_rules: TriggerRuleBuildResponse | None = None
    event_scanner: EventScannerResponse | None = None
    signal_scoring: SignalScoringResponse | None = None
    meta_model_ensemble: MetaModelEnsembleResponse | None = None
    recommendation_pipeline: RecommendationPipelineResponse | None = None
    promoted_candidates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: str
    completed_at: str
    duration_ms: int


# In-memory storage
_LATEST_UPPER_WORKFLOW: UpperWorkflowResponse | None = None
_UPPER_WORKFLOW_HISTORY: list[UpperWorkflowResponse] = []
logger = logging.getLogger(__name__)


def _safe_trace_workflow_step(workflow_name: str, step_name: str, status: str, metadata: dict | None = None) -> None:
    try:
        trace_workflow_step(workflow_name, step_name, status, metadata)
    except Exception as exc:
        logger.warning("Upper workflow trace step failed but workflow will continue: %s", exc)


def _safe_trace_event(*args, **kwargs) -> None:
    try:
        trace_event(*args, **kwargs)
    except Exception as exc:
        logger.warning("Upper workflow trace event failed but workflow will continue: %s", exc)


def _save_upper_workflow_run(response: UpperWorkflowResponse) -> UpperWorkflowResponse:
    global _LATEST_UPPER_WORKFLOW
    _LATEST_UPPER_WORKFLOW = response
    _UPPER_WORKFLOW_HISTORY.append(response)
    if len(_UPPER_WORKFLOW_HISTORY) > 100:
        del _UPPER_WORKFLOW_HISTORY[:-100]
    return response


def run_upper_workflow(request: UpperWorkflowRequest) -> UpperWorkflowResponse:
    """Run the complete upper workflow sequence."""
    global _LATEST_UPPER_WORKFLOW

    run_id = f"upper-{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)
    stages: list[UpperWorkflowStage] = []
    blockers: list[str] = []
    warnings: list[str] = []

    # Trace workflow start
    _safe_trace_workflow_step("upper_workflow", "started", "running", {"run_id": run_id, "symbols_count": len(request.symbols)})

    # Require explicit symbols
    if not request.symbols:
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        return _save_upper_workflow_run(UpperWorkflowResponse(
            run_id=run_id,
            status="blocked",
            market_phase="unknown",
            active_loop="unknown",
            stages=[UpperWorkflowStage(stage="init", status="blocked", blockers=["No symbols provided"])],
            blockers=["Explicit symbols required - no default universe"],
            warnings=[],
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms,
        ))

    # 1. Runtime Cadence
    try:
        cadence = get_runtime_cadence()
        market_phase = cadence.market_phase.value
        active_loop = cadence.active_loop.value
        stages.append(UpperWorkflowStage(
            stage="runtime_cadence",
            status="completed",
            run_id=None,
        ))
    except Exception as e:
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        return _save_upper_workflow_run(UpperWorkflowResponse(
            run_id=run_id,
            status="failed",
            market_phase="unknown",
            active_loop="unknown",
            stages=[UpperWorkflowStage(stage="runtime_cadence", status="failed", blockers=[str(e)])],
            blockers=[f"Runtime cadence failed: {e}"],
            warnings=[],
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms,
        ))

    # 2. Data Freshness Check
    freshness: DataFreshnessCheckResponse | None = None
    try:
        freshness = run_data_freshness_check(DataFreshnessCheckRequest(
            symbols=request.symbols,
            asset_class=request.asset_class,
            source=request.source,
            horizon=request.horizon,
            allow_mock=request.allow_mock,
        ))

        if freshness.status == "fail":
            stages.append(UpperWorkflowStage(
                stage="data_freshness",
                status="blocked",
                run_id=freshness.run_id,
                blockers=freshness.blockers,
                warnings=freshness.warnings,
            ))
            blockers.extend(freshness.blockers)
            warnings.extend(freshness.warnings)

            # Stop here if all data blocked
            if freshness.summary.blocked_count == len(request.symbols):
                completed_at = datetime.now(timezone.utc)
                duration_ms = int((completed_at - started_at).total_seconds() * 1000)
                return _save_upper_workflow_run(UpperWorkflowResponse(
                    run_id=run_id,
                    status="blocked_by_data_freshness",
                    market_phase=market_phase,
                    active_loop=active_loop,
                    stages=stages,
                    data_freshness=freshness,
                    blockers=blockers + ["All symbols blocked by data freshness checks"],
                    warnings=warnings,
                    started_at=started_at.isoformat(),
                    completed_at=completed_at.isoformat(),
                    duration_ms=duration_ms,
                ))
        else:
            stages.append(UpperWorkflowStage(
                stage="data_freshness",
                status="completed",
                run_id=freshness.run_id,
                warnings=freshness.warnings,
            ))
            warnings.extend(freshness.warnings)
            _safe_trace_workflow_step("upper_workflow", "data_freshness", "completed", {"run_id": freshness.run_id})
    except Exception as e:
        stages.append(UpperWorkflowStage(
            stage="data_freshness",
            status="failed",
            blockers=[str(e)],
        ))
        blockers.append(f"Data freshness check failed: {e}")
        warnings.append("Data provider failure blocked upper workflow before strategy/universe/scoring stages. No mock data was used.")
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        return _save_upper_workflow_run(UpperWorkflowResponse(
            run_id=run_id,
            status="blocked_by_data_freshness",
            market_phase=market_phase,
            active_loop=active_loop,
            stages=stages,
            data_freshness=freshness,
            blockers=blockers,
            warnings=warnings,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms,
        ))

    # Get usable symbols after freshness check
    usable_symbols = request.symbols
    if freshness:
        usable_symbols = [r.symbol for r in freshness.results if r.decision in ["usable", "degraded"]]
        if not usable_symbols:
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            return _save_upper_workflow_run(UpperWorkflowResponse(
                run_id=run_id,
                status="blocked_by_data_freshness",
                market_phase=market_phase,
                active_loop=active_loop,
                stages=stages,
                data_freshness=freshness,
                blockers=blockers + ["No usable symbols after data freshness check"],
                warnings=warnings,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
            ))

    # 3. Market Regime Model
    regime: MarketRegimeResponse | None = None
    try:
        regime = run_market_regime_model(MarketRegimeRequest(
            source=request.source,
            horizon=request.horizon,
            allow_mock=request.allow_mock,
        ))

        if regime.status == "fail":
            stages.append(UpperWorkflowStage(
                stage="market_regime",
                status="failed",
                run_id=regime.run_id,
                blockers=regime.blockers,
                warnings=regime.warnings,
            ))
            warnings.extend(regime.warnings)
            # Continue with unknown regime
        else:
            stages.append(UpperWorkflowStage(
                stage="market_regime",
                status="completed",
                run_id=regime.run_id,
                warnings=regime.warnings,
            ))
            warnings.extend(regime.warnings)
            _safe_trace_workflow_step("upper_workflow", "market_regime", "completed", {"regime": regime.regime})
    except Exception as e:
        stages.append(UpperWorkflowStage(
            stage="market_regime",
            status="failed",
            blockers=[str(e)],
        ))
        warnings.append(f"Market regime detection failed: {e}")
        _safe_trace_workflow_step("upper_workflow", "market_regime", "failed")

    regime_value = regime.regime if regime else "unknown"

    # 4. Strategy Debate
    debate: StrategyDebateResponse | None = None
    try:
        debate = run_strategy_debate(StrategyDebateRequest(
            market_phase=market_phase,
            active_loop=active_loop,
            regime=regime_value,
            horizon=request.horizon,
            account_equity=request.account_equity,
            buying_power=request.buying_power,
            max_risk_per_trade_percent=request.max_risk_per_trade_percent,
            allow_llm=False,
        ))

        stages.append(UpperWorkflowStage(
            stage="strategy_debate",
            status="completed",
            run_id=debate.run_id,
            warnings=debate.warnings,
        ))
        warnings.extend(debate.warnings)
    except Exception as e:
        stages.append(UpperWorkflowStage(
            stage="strategy_debate",
            status="failed",
            blockers=[str(e)],
        ))
        warnings.append(f"Strategy debate failed: {e}")

    # 5. Strategy Ranking
    ranking: StrategyRankingResponse | None = None
    try:
        ranking = run_strategy_ranking(StrategyRankingRequest(
            debate_run_id=debate.run_id if debate else None,
            market_phase=market_phase,
            active_loop=active_loop,
            regime=regime_value,
            horizon=request.horizon,
            account_equity=request.account_equity,
            buying_power=request.buying_power,
        ))

        stages.append(UpperWorkflowStage(
            stage="strategy_ranking",
            status="completed" if ranking.status != "failed" else "failed",
            run_id=ranking.run_id,
            warnings=ranking.warnings,
        ))
        warnings.extend(ranking.warnings)
        _safe_trace_workflow_step("upper_workflow", "strategy_ranking", "completed", {"top_strategy": ranking.top_strategy_key})
    except Exception as e:
        stages.append(UpperWorkflowStage(
            stage="strategy_ranking",
            status="failed",
            blockers=[str(e)],
        ))
        warnings.append(f"Strategy ranking failed: {e}")
        _safe_trace_workflow_step("upper_workflow", "strategy_ranking", "failed")

    # 6. Model Selection (for top strategy)
    model_sel: ModelSelectionResponse | None = None
    top_strategy = None
    if ranking and ranking.top_strategy_key:
        top_strategy = ranking.top_strategy_key
        try:
            model_sel = run_model_selection(ModelSelectionRequest(
                strategy_key=top_strategy,
                market_phase=market_phase,
                active_loop=active_loop,
                regime=regime_value,
                horizon=request.horizon,
                llm_budget_mode="disabled",  # Always disabled in upper workflow
                require_trained_models=False,
            ))

            stages.append(UpperWorkflowStage(
                stage="model_selection",
                status="completed" if model_sel.status != "failed" else "failed",
                run_id=model_sel.run_id,
                warnings=model_sel.warnings,
            ))
            warnings.extend(model_sel.warnings)
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="model_selection",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Model selection failed: {e}")
    else:
        stages.append(UpperWorkflowStage(
            stage="model_selection",
            status="skipped",
            warnings=["No top strategy available - model selection skipped"],
        ))
        warnings.append("No active strategy from ranking - model selection skipped")

    # 7. Universe Selection
    universe: UniverseSelectionResponse | None = None
    if usable_symbols and top_strategy:
        try:
            universe = run_universe_selection(UniverseSelectionRequest(
                symbols=usable_symbols,
                asset_class=request.asset_class,
                horizon=request.horizon,
                source=request.source,
                strategy_key=top_strategy,
                max_candidates=25,
                min_score=50,
                account_equity=request.account_equity,
                buying_power=request.buying_power,
                max_risk_per_trade_percent=request.max_risk_per_trade_percent,
                include_mock=request.allow_mock,
                promote_to_candidate_universe=False,  # We handle promotion separately
            ))

            stages.append(UpperWorkflowStage(
                stage="universe_selection",
                status="completed" if universe.status not in ["failed", "no_symbols"] else "failed",
                run_id=universe.run_id,
                warnings=universe.warnings,
            ))
            warnings.extend(universe.warnings)
            _safe_trace_workflow_step("upper_workflow", "universe_selection", "completed", {"candidates_count": len(universe.selected_watchlist) if universe.selected_watchlist else 0})
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="universe_selection",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Universe selection failed: {e}")
            _safe_trace_workflow_step("upper_workflow", "universe_selection", "failed")
    else:
        skip_reason = "No usable symbols" if not usable_symbols else "No active strategy"
        stages.append(UpperWorkflowStage(
            stage="universe_selection",
            status="skipped",
            warnings=[f"{skip_reason} - universe selection skipped"],
        ))
        warnings.append(f"Universe selection skipped: {skip_reason}")

    # 8. Trigger Rules Build (from universe selection candidates)
    trigger_rules: TriggerRuleBuildResponse | None = None
    if request.build_trigger_rules and universe and universe.selected_watchlist:
        try:
            trigger_rules = run_trigger_rule_build(TriggerRuleBuildRequest(
                candidates=universe.selected_watchlist,
                strategy_key=top_strategy,
                horizon=request.horizon,
                market_phase=market_phase,
                active_loop=active_loop,
                source_run_id=run_id,
                use_latest_watchlist=False,  # We already have the candidates
            ))

            stages.append(UpperWorkflowStage(
                stage="trigger_rules",
                status="completed" if trigger_rules.status not in ["no_candidates", "failed"] else "failed",
                run_id=trigger_rules.run_id,
                warnings=trigger_rules.warnings,
            ))
            warnings.extend(trigger_rules.warnings)
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="trigger_rules",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Trigger rules build failed: {e}")
    else:
        skip_reason = "build_trigger_rules=false" if not request.build_trigger_rules else "No universe selection results"
        stages.append(UpperWorkflowStage(
            stage="trigger_rules",
            status="skipped",
            warnings=[skip_reason],
        ))

    # 9. Event Scanner (requires trigger rules or watchlist)
    event_scanner: EventScannerResponse | None = None
    if request.run_event_scanner:
        try:
            event_scanner = run_event_scanner(EventScannerRequest(
                use_latest_watchlist=True,  # Will use trigger rules first
                use_active_trigger_rules=True,
                source=request.source,
                horizon=request.horizon,
                allow_mock=request.allow_mock,
            ))

            stages.append(UpperWorkflowStage(
                stage="event_scanner",
                status="completed" if event_scanner.status not in ["no_symbols", "failed"] else "failed",
                run_id=event_scanner.run_id,
                warnings=event_scanner.warnings,
            ))
            warnings.extend(event_scanner.warnings)
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="event_scanner",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Event scanner failed: {e}")
    else:
        stages.append(UpperWorkflowStage(
            stage="event_scanner",
            status="skipped",
            warnings=["run_event_scanner=false"],
        ))

    # 10. Signal Scoring (requires events)
    signal_scoring: SignalScoringResponse | None = None
    if request.run_signal_scoring and event_scanner and event_scanner.matched_events:
        try:
            signal_scoring = run_signal_scoring(SignalScoringRequest(
                events=event_scanner.matched_events,
                use_latest_events=False,  # We already have them
                source=request.source,
                horizon=request.horizon,
                strategy_key=top_strategy,
                allow_mock=request.allow_mock,
            ))

            stages.append(UpperWorkflowStage(
                stage="signal_scoring",
                status="completed" if signal_scoring.status not in ["no_events", "failed"] else "failed",
                run_id=signal_scoring.run_id,
                warnings=signal_scoring.warnings,
            ))
            warnings.extend(signal_scoring.warnings)
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="signal_scoring",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Signal scoring failed: {e}")
    else:
        skip_reason = "run_signal_scoring=false" if not request.run_signal_scoring else "No events to score"
        stages.append(UpperWorkflowStage(
            stage="signal_scoring",
            status="skipped",
            warnings=[skip_reason],
        ))

    # 11. Meta-Model Ensemble (requires scored signals)
    meta_model_ensemble: MetaModelEnsembleResponse | None = None
    if request.run_meta_model and signal_scoring and signal_scoring.scored_signals:
        try:
            meta_model_ensemble = run_meta_model_ensemble(MetaModelEnsembleRequest(
                scored_signals=signal_scoring.scored_signals,
                use_latest_scored_signals=False,  # We already have them
                regime=regime_value,
                strategy_key=top_strategy,
                horizon=request.horizon,
                promote_to_candidates=False,  # Handle separately
            ))

            stages.append(UpperWorkflowStage(
                stage="meta_model_ensemble",
                status="completed" if meta_model_ensemble.status not in ["no_signals", "failed"] else "failed",
                run_id=meta_model_ensemble.run_id,
                warnings=meta_model_ensemble.warnings,
            ))
            warnings.extend(meta_model_ensemble.warnings)
            _safe_trace_workflow_step("upper_workflow", "meta_model_ensemble", "completed")
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="meta_model_ensemble",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Meta-model ensemble failed: {e}")
            _safe_trace_workflow_step("upper_workflow", "meta_model_ensemble", "failed")
    else:
        skip_reason = "run_meta_model=false" if not request.run_meta_model else "No scored signals"
        stages.append(UpperWorkflowStage(
            stage="meta_model_ensemble",
            status="skipped",
            warnings=[skip_reason],
        ))

    # 12. Optional Promotion to Candidate Universe
    promoted: list[str] = []
    if request.promote_to_candidate_universe:
        # Prefer meta-model signals if available
        signals_to_promote = meta_model_ensemble.ensemble_signals if meta_model_ensemble else []

        if signals_to_promote:
            # Promote passing signals from meta-model
            for signal in signals_to_promote:
                if signal.status == "pass":
                    try:
                        add_candidate(
                            symbol=signal.symbol,
                            source_type="meta_model_ensemble",
                            source_detail=f"upper_workflow:{run_id}",
                            metadata={
                                "final_score": signal.final_signal_score,
                                "confidence": signal.confidence,
                                "strategy_key": signal.strategy_key,
                            },
                        )
                        promoted.append(signal.symbol)
                    except Exception as e:
                        warnings.append(f"Failed to promote {signal.symbol}: {e}")
        elif universe and universe.selected_watchlist:
            # Fall back to universe selection candidates
            for candidate in universe.selected_watchlist:
                try:
                    add_candidate(
                        symbol=candidate.symbol,
                        asset_class=candidate.asset_class,
                        horizon=candidate.horizon,
                        source_type="universe_selection",
                        source_detail=f"upper_workflow:{run_id}",
                        priority_score=int(candidate.universe_score),
                        notes=f"Promoted from upper workflow. Score: {candidate.universe_score:.1f}, Strategy: {candidate.assigned_strategy}",
                    )
                    promoted.append(candidate.symbol)
                except Exception:
                    pass

        if promoted:
            stages.append(UpperWorkflowStage(
                stage="promote_to_candidates",
                status="completed",
            ))
        else:
            stages.append(UpperWorkflowStage(
                stage="promote_to_candidates",
                status="skipped",
                warnings=["No candidates available to promote"],
            ))
    else:
        stages.append(UpperWorkflowStage(
            stage="promote_to_candidates",
            status="skipped",
            warnings=["promote_to_candidate_universe=false - skipping promotion"],
        ))

    # 13. Recommendation Pipeline (optional - requires meta-model signals)
    recommendation_pipeline: RecommendationPipelineResponse | None = None
    if request.run_recommendation_pipeline and meta_model_ensemble and meta_model_ensemble.ensemble_signals:
        try:
            # Use latest ensemble signals
            recommendation_pipeline = run_recommendation_pipeline(RecommendationPipelineRequest(
                use_latest_ensemble=True,
                account_equity=request.account_equity or 1000,
                buying_power=request.buying_power or 1000,
                allow_paid_llm=False,  # Never allow paid LLM in workflow
                dry_run=True,  # Always dry run for safety
            ))

            stages.append(UpperWorkflowStage(
                stage="recommendation_pipeline",
                status="completed" if recommendation_pipeline.status == "recommendation_created" else "failed",
                run_id=recommendation_pipeline.run_id,
                warnings=recommendation_pipeline.warnings,
            ))
            warnings.extend(recommendation_pipeline.warnings)
            _safe_trace_workflow_step("upper_workflow", "recommendation_pipeline", recommendation_pipeline.status)
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="recommendation_pipeline",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Recommendation pipeline failed: {e}")
            _safe_trace_workflow_step("upper_workflow", "recommendation_pipeline", "failed")
    else:
        skip_reason = "run_recommendation_pipeline=false" if not request.run_recommendation_pipeline else "No ensemble signals available"
        stages.append(UpperWorkflowStage(
            stage="recommendation_pipeline",
            status="skipped",
            warnings=[skip_reason],
        ))

    # Determine final status
    failed_stages = [s for s in stages if s.status == "failed"]
    blocked_stages = [s for s in stages if s.status == "blocked"]

    if blocked_stages:
        final_status = "blocked"
    elif failed_stages and len(failed_stages) == len(stages):
        final_status = "failed"
    elif failed_stages:
        final_status = "partial"
    else:
        final_status = "completed"

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    # Trace workflow completion
    _safe_trace_workflow_step("upper_workflow", "completed", final_status, {"duration_ms": duration_ms, "stages_count": len(stages)})

    response = UpperWorkflowResponse(
        run_id=run_id,
        status=final_status,
        market_phase=market_phase,
        active_loop=active_loop,
        stages=stages,
        data_freshness=freshness,
        regime=regime,
        strategy_debate=debate,
        strategy_ranking=ranking,
        model_selection=model_sel,
        universe_selection=universe,
        trigger_rules=trigger_rules,
        event_scanner=event_scanner,
        signal_scoring=signal_scoring,
        meta_model_ensemble=meta_model_ensemble,
        recommendation_pipeline=recommendation_pipeline,
        promoted_candidates=promoted,
        blockers=blockers,
        warnings=list(set(warnings)),  # Deduplicate
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=duration_ms,
    )

    return _save_upper_workflow_run(response)


def get_latest_upper_workflow() -> UpperWorkflowResponse | None:
    """Get the most recent upper workflow run."""
    return _LATEST_UPPER_WORKFLOW


def list_upper_workflow_history(limit: int = 20) -> list[UpperWorkflowResponse]:
    """List recent upper workflow runs."""
    return _UPPER_WORKFLOW_HISTORY[-limit:]
