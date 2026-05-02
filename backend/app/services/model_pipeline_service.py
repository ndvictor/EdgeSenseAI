from pydantic import BaseModel

from app.data_providers.base import MarketSnapshot
from app.services.feature_engineering_service import EngineeredFeatures, build_features


class ModelPipelineResult(BaseModel):
    symbol: str
    data_mode: str
    features: EngineeredFeatures
    directional_bias: str
    regime_bias: str
    volatility_fit: str
    ranker_score: int
    pipeline_notes: list[str]


def run_model_pipeline(snapshot: MarketSnapshot) -> ModelPipelineResult:
    features = build_features(snapshot)
    directional_bias = "bullish" if features.composite_feature_score >= 75 else "neutral"
    regime_bias = "momentum_allowed" if snapshot.current_price > snapshot.vwap else "mean_reversion_preferred"
    volatility_fit = "acceptable" if 0.2 <= snapshot.volatility_proxy <= 0.5 else "review"
    ranker_score = int((features.composite_feature_score * 0.7) + (features.spread_quality_score * 0.3))

    return ModelPipelineResult(
        symbol=snapshot.symbol,
        data_mode=snapshot.data_mode,
        features=features,
        directional_bias=directional_bias,
        regime_bias=regime_bias,
        volatility_fit=volatility_fit,
        ranker_score=ranker_score,
        pipeline_notes=[
            "Pipeline contract is ready for ARIMAX, Kalman, GARCH, HMM, and XGBoost implementations.",
            "Current outputs are deterministic prototype signals until live market data and trained models are added.",
        ],
    )
