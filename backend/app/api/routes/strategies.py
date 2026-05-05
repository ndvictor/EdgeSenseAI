from fastapi import APIRouter, HTTPException

from app.agents.registry import CoreAgentRegistryEntry, list_core_agents
from app.services.edge_signal_rules_service import EdgeSignalRule, list_edge_signal_rules
from app.strategies.registry import (
    StrategyConfig,
    StrategyRegistrySummary,
    get_strategy,
    get_strategy_registry_summary,
    list_active_strategies,
    list_candidate_strategies,
    list_strategies,
    list_strategies_by_status,
)

router = APIRouter()


@router.get("/agents/registry", response_model=list[CoreAgentRegistryEntry])
def get_agents_registry():
    return list_core_agents()


@router.get("/strategies", response_model=list[StrategyConfig])
def get_strategies():
    return list_strategies()


@router.get("/strategies/candidates", response_model=list[StrategyConfig])
def get_strategies_candidates():
    """Get candidate/research strategies only."""
    return list_candidate_strategies()


@router.get("/strategies/active", response_model=list[StrategyConfig])
def get_strategies_active():
    """Get active/approved strategies (excludes candidates)."""
    return list_active_strategies()


@router.get("/strategies/summary", response_model=StrategyRegistrySummary)
def get_strategies_summary():
    """Rollup counts for the in-code strategy registry (Phase 1)."""
    return get_strategy_registry_summary()


@router.get("/strategies/{strategy_key}", response_model=StrategyConfig)
def get_strategy_by_key(strategy_key: str):
    strategy = get_strategy(strategy_key)
    if strategy is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    return strategy


@router.get("/strategies/{strategy_key}/playbook")
def get_strategy_playbook(strategy_key: str):
    """Get strategy playbook with detailed metadata for research/candidate strategies."""
    strategy = get_strategy(strategy_key)
    if strategy is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    
    return {
        "strategy_key": strategy.strategy_key,
        "display_name": strategy.display_name,
        "description": strategy.description,
        "asset_class": strategy.asset_class,
        "timeframe": strategy.timeframe,
        "status": strategy.status,
        "promotion_status": strategy.promotion_status,
        "claim_type": strategy.claim_type,
        "claim_source": strategy.claim_source,
        "live_trading_supported": strategy.live_trading_supported,
        "paper_research_only": strategy.paper_research_only,
        "requires_backtest": strategy.requires_backtest,
        "requires_owner_approval_for_promotion": strategy.requires_owner_approval_for_promotion,
        "disabled_reason": strategy.disabled_reason,
        "best_regimes": strategy.best_regimes,
        "bad_regimes": strategy.bad_regimes,
        "trigger_rules": strategy.trigger_rules,
        "required_data_sources": strategy.required_data_sources,
        "validation_rules": strategy.validation_rules,
        "risk_notes": strategy.risk_notes,
        "risk_rules": strategy.risk_rules,
        "small_account_fit": strategy.small_account_fit,
        "drawdown_risk": strategy.drawdown_risk,
        "pdt_risk": strategy.pdt_risk,
        "core_universe": strategy.core_universe,
        "optional_expansion": strategy.optional_expansion,
        "candidate_universe_examples": strategy.candidate_universe_examples,
        "promotion_requirements": strategy.promotion_requirements,
    }


@router.get("/edge-signal-rules", response_model=list[EdgeSignalRule])
def get_edge_signal_rules():
    return list_edge_signal_rules()
