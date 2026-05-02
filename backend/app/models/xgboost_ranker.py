from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.services.feature_store_service import FeatureStoreRow
from app.strategies.registry import StrategyConfig


class XGBoostRankerOutput(BaseModel):
    model: str = "xgboost_ranker"
    model_name: str = "xgboost_ranker"
    model_type: str = "supervised_ranker"
    status: str
    prediction_score: float | None = None
    probability_score: float | None = None
    confidence_score: float | None = None
    reason: str
    next_steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data_source: str = "placeholder"
    pricing: None = None
    cost: None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _xgboost_available() -> bool:
    try:
        import xgboost  # noqa: F401

        return True
    except Exception:
        return False


def run_xgboost_ranker_safe(
    feature_row: FeatureStoreRow,
    strategy_config: StrategyConfig,
    artifact_path: str | None = None,
) -> XGBoostRankerOutput:
    if not _xgboost_available():
        return XGBoostRankerOutput(
            status="not_available",
            reason="xgboost package is not installed in this environment.",
            next_steps=["Install xgboost", "Collect labeled outcomes", "Train model", "Save model artifact", "Run walk-forward validation"],
            metadata={"strategy_key": strategy_config.strategy_key, "feature_row_id": feature_row.id},
        )

    artifact = Path(artifact_path or "model_artifacts/xgboost_ranker.json")
    if not artifact.exists():
        return XGBoostRankerOutput(
            status="not_trained",
            reason="xgboost is installed, but no trained model artifact exists for production inference.",
            next_steps=["Collect labeled outcomes", "Train model", "Save model artifact", "Run walk-forward validation"],
            warnings=["Prototype Model Lab XGBoost fits are not used as trained production artifacts."],
            metadata={"strategy_key": strategy_config.strategy_key, "feature_row_id": feature_row.id, "artifact_path": str(artifact)},
        )

    return XGBoostRankerOutput(
        status="not_trained",
        reason="A model artifact path exists, but production artifact loading is not wired in this foundation pass.",
        next_steps=["Validate artifact schema", "Load artifact safely", "Run walk-forward validation", "Register artifact metadata"],
        warnings=["No trained XGBoost prediction was produced."],
        metadata={"strategy_key": strategy_config.strategy_key, "feature_row_id": feature_row.id, "artifact_path": str(artifact)},
    )
