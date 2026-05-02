from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from app.data_providers.provider_factory import get_market_data_provider
from app.services.feature_engineering_service import build_features
from app.services.xgboost_ranker_service import RankerInputRow, RankerRunResult, run_xgboost_ranker


class ModelLabRunRequest(BaseModel):
    data_source: Literal["mock", "yfinance"] = "mock"
    model: Literal["xgboost_ranker", "weighted_ranker"] = "xgboost_ranker"
    symbols: list[str] = Field(default_factory=lambda: ["AMD", "NVDA", "BTC-USD"])
    train_split_percent: int = 70
    test_split_percent: int = 30
    feature_set: Literal["prototype_v1"] = "prototype_v1"


class DatasetSplitSummary(BaseModel):
    total_rows: int
    train_rows: int
    test_rows: int
    train_split_percent: int
    test_split_percent: int


class FeatureRow(BaseModel):
    symbol: str
    asset_class: str
    current_price: float
    feature_score: int
    momentum_score: int
    rvol_score: int
    spread_quality_score: int
    trend_vs_vwap_score: int
    volatility_score: int


class ModelLabRunResponse(BaseModel):
    workflow_status: str
    data_source: str
    model: str
    feature_set: str
    split: DatasetSplitSummary
    features: list[FeatureRow]
    ranker_result: RankerRunResult
    next_steps: list[str]


def run_model_lab_workflow(request: ModelLabRunRequest) -> ModelLabRunResponse:
    provider = get_market_data_provider(request.data_source)
    feature_rows: list[FeatureRow] = []
    ranker_rows: list[RankerInputRow] = []

    for symbol in request.symbols:
        asset_class = "crypto" if "-USD" in symbol else "stock"
        snapshot = provider.get_snapshot(symbol, asset_class=asset_class)
        features = build_features(snapshot)
        feature_rows.append(
            FeatureRow(
                symbol=snapshot.symbol,
                asset_class=snapshot.asset_class,
                current_price=snapshot.current_price,
                feature_score=features.composite_feature_score,
                momentum_score=features.momentum_score,
                rvol_score=features.rvol_score,
                spread_quality_score=features.spread_quality_score,
                trend_vs_vwap_score=features.trend_vs_vwap_score,
                volatility_score=features.volatility_score,
            )
        )
        ranker_rows.append(
            RankerInputRow(
                symbol=snapshot.symbol,
                feature_score=features.composite_feature_score,
                momentum_score=features.momentum_score,
                rvol_score=features.rvol_score,
                spread_quality_score=features.spread_quality_score,
                trend_vs_vwap_score=features.trend_vs_vwap_score,
                volatility_score=features.volatility_score,
            )
        )

    total_rows = len(feature_rows)
    train_rows = int(total_rows * request.train_split_percent / 100)
    test_rows = total_rows - train_rows
    ranker_result = run_xgboost_ranker(ranker_rows)

    return ModelLabRunResponse(
        workflow_status="completed",
        data_source=request.data_source,
        model=request.model,
        feature_set=request.feature_set,
        split=DatasetSplitSummary(
            total_rows=total_rows,
            train_rows=train_rows,
            test_rows=test_rows,
            train_split_percent=request.train_split_percent,
            test_split_percent=request.test_split_percent,
        ),
        features=feature_rows,
        ranker_result=ranker_result,
        next_steps=[
            "Persist feature rows and labels for repeatable training runs.",
            "Replace weak prototype labels with target-before-stop outcomes.",
            "Add train/test date windows rather than row-count split only.",
            "Persist trained XGBoost model artifacts and load them for inference.",
        ],
    )
