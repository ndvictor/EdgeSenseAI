from datetime import datetime

from pydantic import BaseModel


class RegimeFactor(BaseModel):
    name: str
    value: str
    signal: str
    impact: str
    data_source: str = "source_unavailable"
    source_detail: str = "Market regime factor source is not configured."


class MarketRegimeResponse(BaseModel):
    regime_state: str
    confidence: float
    strategy_bias: str
    allowed_strategies: list[str]
    blocked_strategies: list[str]
    factors: list[RegimeFactor]
    notes: list[str]
    data_source: str = "source_unavailable"
    source_type: str = "not_configured"
    source_detail: str = "Market regime provider inputs are not configured."
    provider: str = "none"
    model_used: str = "none"
    llm_used: str = "none"
    agent_used: str = "none"
    calculation_engine: str = "not_configured"
    real_data_used: bool = False
    generated_at: datetime


def build_market_regime(source_type: str = "source_backed") -> MarketRegimeResponse:
    from app.services.market_regime_providers import get_market_regime_provider

    return get_market_regime_provider(source_type).build_regime()
