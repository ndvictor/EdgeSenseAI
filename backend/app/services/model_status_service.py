from pydantic import BaseModel


class ModelStatus(BaseModel):
    name: str
    category: str
    status: str
    purpose: str
    current_mode: str
    next_step: str


class ModelStatusResponse(BaseModel):
    data_mode: str = "synthetic_prototype"
    live_prediction_enabled: bool = False
    models: list[ModelStatus]


def build_model_status_response() -> ModelStatusResponse:
    return ModelStatusResponse(
        models=[
            ModelStatus(
                name="ARIMAX Directional Forecast",
                category="statistical_forecast",
                status="prototype_contract_ready",
                purpose="Estimate directional movement using returns, volume, and external market context.",
                current_mode="deterministic prototype explanation",
                next_step="Connect candle/volume data and implement rolling forecast service.",
            ),
            ModelStatus(
                name="Kalman Trend Filter",
                category="state_space_filter",
                status="prototype_contract_ready",
                purpose="Detect adaptive trend, pullback quality, and mean-reversion risk.",
                current_mode="deterministic prototype explanation",
                next_step="Add price-state estimation from intraday candles.",
            ),
            ModelStatus(
                name="GARCH Volatility Fit",
                category="volatility_model",
                status="prototype_contract_ready",
                purpose="Estimate volatility fit for stop distance, target sizing, and options risk.",
                current_mode="deterministic prototype explanation",
                next_step="Add realized-volatility features and volatility forecast service.",
            ),
            ModelStatus(
                name="HMM Regime Filter",
                category="regime_model",
                status="prototype_contract_ready",
                purpose="Classify market regime so momentum, breakout, and reversion signals are not treated equally.",
                current_mode="deterministic prototype explanation",
                next_step="Train regime states using index trend, VIX proxy, volatility, and breadth features.",
            ),
            ModelStatus(
                name="XGBoost Meta-Ranker",
                category="machine_learning_ranker",
                status="prototype_contract_ready",
                purpose="Rank candidates using model outputs, feature scores, account fit, liquidity, and reward/risk.",
                current_mode="deterministic prototype explanation",
                next_step="Create labeled training set from backtest outcomes and fit ranker.",
            ),
        ]
    )
