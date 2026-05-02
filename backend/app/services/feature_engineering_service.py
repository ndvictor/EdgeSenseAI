from pydantic import BaseModel

from app.data_providers.base import MarketSnapshot


class EngineeredFeatures(BaseModel):
    symbol: str
    momentum_score: int
    rvol_score: int
    spread_quality_score: int
    trend_vs_vwap_score: int
    volatility_score: int
    composite_feature_score: int
    notes: list[str]


def build_features(snapshot: MarketSnapshot) -> EngineeredFeatures:
    momentum_score = 80 if snapshot.day_change_percent > 1 else 55
    rvol_score = min(95, int(snapshot.relative_volume * 40))
    spread_quality_score = 90 if snapshot.spread_percent <= 0.08 else 60
    trend_vs_vwap_score = 82 if snapshot.current_price > snapshot.vwap else 45
    volatility_score = 75 if 0.2 <= snapshot.volatility_proxy <= 0.5 else 55
    composite = int((momentum_score + rvol_score + spread_quality_score + trend_vs_vwap_score + volatility_score) / 5)

    return EngineeredFeatures(
        symbol=snapshot.symbol,
        momentum_score=momentum_score,
        rvol_score=rvol_score,
        spread_quality_score=spread_quality_score,
        trend_vs_vwap_score=trend_vs_vwap_score,
        volatility_score=volatility_score,
        composite_feature_score=composite,
        notes=[
            "Prototype features derived from normalized mock market snapshot.",
            "Replace with candle, order book, options chain, and regime features when live providers are connected.",
        ],
    )
