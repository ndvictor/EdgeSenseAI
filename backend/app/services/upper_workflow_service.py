"""Upper Workflow Orchestration Service.

Implements the approved Adaptive Agentic Quant Workflow sequence:
1. Runtime cadence (already exists)
2. Data freshness check
3. Market regime model
4. Strategy debate
5. Strategy ranking
6. Model selection for top active strategy
7. Universe selection/watchlist builder
8. Optional promotion to candidate universe

NO LLMs.
NO default symbols.
Live trading disabled, human approval required.
"""

from datetime import datetime, timezone
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
from app.services.market_regime_model_service import (
    MarketRegimeRequest,
    MarketRegimeResponse,
    run_market_regime_model,
)
from app.services.model_selection_service import (
    ModelSelectionRequest,
    ModelSelectionResponse,
    run_model_selection,
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
    status: Literal["completed", "partial", "failed", "blocked"]
    market_phase: str
    active_loop: str
    stages: list[UpperWorkflowStage]
    data_freshness: DataFreshnessCheckResponse | None = None
    regime: MarketRegimeResponse | None = None
    strategy_debate: StrategyDebateResponse | None = None
    strategy_ranking: StrategyRankingResponse | None = None
    model_selection: ModelSelectionResponse | None = None
    universe_selection: UniverseSelectionResponse | None = None
    promoted_candidates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: str
    completed_at: str
    duration_ms: int


# In-memory storage
_LATEST_UPPER_WORKFLOW: UpperWorkflowResponse | None = None
_UPPER_WORKFLOW_HISTORY: list[UpperWorkflowResponse] = []


def run_upper_workflow(request: UpperWorkflowRequest) -> UpperWorkflowResponse:
    """Run the complete upper workflow sequence."""
    global _LATEST_UPPER_WORKFLOW

    run_id = f"upper-{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)
    stages: list[UpperWorkflowStage] = []
    blockers: list[str] = []
    warnings: list[str] = []

    # Require explicit symbols
    if not request.symbols:
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        return UpperWorkflowResponse(
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
        )

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
        return UpperWorkflowResponse(
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
        )

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
                return UpperWorkflowResponse(
                    run_id=run_id,
                    status="blocked",
                    market_phase=market_phase,
                    active_loop=active_loop,
                    stages=stages,
                    data_freshness=freshness,
                    blockers=blockers + ["All symbols blocked by data freshness checks"],
                    warnings=warnings,
                    started_at=started_at.isoformat(),
                    completed_at=completed_at.isoformat(),
                    duration_ms=duration_ms,
                )
        else:
            stages.append(UpperWorkflowStage(
                stage="data_freshness",
                status="completed",
                run_id=freshness.run_id,
                warnings=freshness.warnings,
            ))
            warnings.extend(freshness.warnings)
    except Exception as e:
        stages.append(UpperWorkflowStage(
            stage="data_freshness",
            status="failed",
            blockers=[str(e)],
        ))
        blockers.append(f"Data freshness check failed: {e}")
        freshness = None

    # Get usable symbols after freshness check
    usable_symbols = request.symbols
    if freshness:
        usable_symbols = [r.symbol for r in freshness.results if r.decision in ["usable", "degraded"]]
        if not usable_symbols:
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            return UpperWorkflowResponse(
                run_id=run_id,
                status="blocked",
                market_phase=market_phase,
                active_loop=active_loop,
                stages=stages,
                data_freshness=freshness,
                blockers=blockers + ["No usable symbols after data freshness check"],
                warnings=warnings,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
            )

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
    except Exception as e:
        stages.append(UpperWorkflowStage(
            stage="market_regime",
            status="failed",
            blockers=[str(e)],
        ))
        warnings.append(f"Market regime detection failed: {e}")

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
    except Exception as e:
        stages.append(UpperWorkflowStage(
            stage="strategy_ranking",
            status="failed",
            blockers=[str(e)],
        ))
        warnings.append(f"Strategy ranking failed: {e}")

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
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="universe_selection",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Universe selection failed: {e}")
    else:
        skip_reason = "No usable symbols" if not usable_symbols else "No active strategy"
        stages.append(UpperWorkflowStage(
            stage="universe_selection",
            status="skipped",
            warnings=[f"{skip_reason} - universe selection skipped"],
        ))
        warnings.append(f"Universe selection skipped: {skip_reason}")

    # 8. Optional Promotion to Candidate Universe
    promoted: list[str] = []
    if request.promote_to_candidate_universe and universe and universe.selected_watchlist:
        try:
            for candidate in universe.selected_watchlist:
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

            stages.append(UpperWorkflowStage(
                stage="promote_to_candidates",
                status="completed",
            ))
        except Exception as e:
            stages.append(UpperWorkflowStage(
                stage="promote_to_candidates",
                status="failed",
                blockers=[str(e)],
            ))
            warnings.append(f"Promotion to candidates failed: {e}")
    else:
        if not request.promote_to_candidate_universe:
            stages.append(UpperWorkflowStage(
                stage="promote_to_candidates",
                status="skipped",
                warnings=["promote_to_candidate_universe=false - skipping promotion"],
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
        promoted_candidates=promoted,
        blockers=blockers,
        warnings=list(set(warnings)),  # Deduplicate
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=duration_ms,
    )

    _LATEST_UPPER_WORKFLOW = response
    _UPPER_WORKFLOW_HISTORY.append(response)

    # Keep only last 100
    if len(_UPPER_WORKFLOW_HISTORY) > 100:
        _UPPER_WORKFLOW_HISTORY = _UPPER_WORKFLOW_HISTORY[-100:]

    return response


def get_latest_upper_workflow() -> UpperWorkflowResponse | None:
    """Get the most recent upper workflow run."""
    return _LATEST_UPPER_WORKFLOW


def list_upper_workflow_history(limit: int = 20) -> list[UpperWorkflowResponse]:
    """List recent upper workflow runs."""
    return _UPPER_WORKFLOW_HISTORY[-limit:]
