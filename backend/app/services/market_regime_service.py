from datetime import datetime

from pydantic import BaseModel


class RegimeFactor(BaseModel):
    name: str
    value: str
    signal: str
    impact: str
    data_source: str = "hardcoded_prototype"
    source_detail: str = "Static placeholder factor from market_regime_service.py"


class MarketRegimeResponse(BaseModel):
    regime_state: str
    confidence: float
    strategy_bias: str
    allowed_strategies: list[str]
    blocked_strategies: list[str]
    factors: list[RegimeFactor]
    notes: list[str]
    data_source: str = "hardcoded_prototype"
    source_type: str = "static_placeholder"
    source_detail: str = "backend/app/services/market_regime_service.py returns static prototype values. No live provider data is used here yet."
    provider: str = "none"
    model_used: str = "none"
    llm_used: str = "none"
    agent_used: str = "none"
    calculation_engine: str = "static_rule_placeholder"
    real_data_used: bool = False
    generated_at: datetime


def build_market_regime(source_type: str = "static_prototype") -> MarketRegimeResponse:
    from app.services.market_regime_providers import get_market_regime_provider

    return get_market_regime_provider(source_type).build_regime()
