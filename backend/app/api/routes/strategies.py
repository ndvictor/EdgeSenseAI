from fastapi import APIRouter, HTTPException

from app.agents.registry import CoreAgentRegistryEntry, list_core_agents
from app.services.edge_signal_rules_service import EdgeSignalRule, list_edge_signal_rules
from app.strategies.registry import StrategyConfig, get_strategy, list_strategies

router = APIRouter()


@router.get("/agents/registry", response_model=list[CoreAgentRegistryEntry])
def get_agents_registry():
    return list_core_agents()


@router.get("/strategies", response_model=list[StrategyConfig])
def get_strategies():
    return list_strategies()


@router.get("/strategies/{strategy_key}", response_model=StrategyConfig)
def get_strategy_by_key(strategy_key: str):
    strategy = get_strategy(strategy_key)
    if strategy is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    return strategy


@router.get("/edge-signal-rules", response_model=list[EdgeSignalRule])
def get_edge_signal_rules():
    return list_edge_signal_rules()
