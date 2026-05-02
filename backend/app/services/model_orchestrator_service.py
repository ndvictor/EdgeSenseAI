from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.feature_store_service import FeatureStoreRow, FeatureStoreRunRequest, run_feature_store_pipeline
from app.services.xgboost_ranker_service import RankerInputRow, run_xgboost_ranker


class ModelRegistryItem(BaseModel):
    key: str
    name: str
    status: str
    should_run_when: list[str]
    data_source: str = "placeholder"


class ModelRunPlanRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["AMD"])
    asset_class: str = "stock"
    horizon: Literal["intraday", "day_trade", "swing", "one_month"] | str = "swing"
    source: str = "auto"
    feature_rows: list[FeatureStoreRow] | None = None


class PlannedModel(BaseModel):
    key: str
    status: str
    should_run: bool
    reason: str
    data_source: str = "placeholder"


class ModelRunPlanResponse(BaseModel):
    data_source: str
    models: list[PlannedModel]
    feature_rows_used: int
    warnings: list[str] = Field(default_factory=list)


class ModelRunRequest(ModelRunPlanRequest):
    pass


class ModelRunResponse(BaseModel):
    status: str
    data_source: str
    plan: ModelRunPlanResponse
    feature_rows: list[FeatureStoreRow]
    results: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)


def _xgboost_installed() -> bool:
    try:
        import xgboost  # noqa: F401

        return True
    except Exception:
        return False


def get_model_registry() -> dict[str, Any]:
    xgboost_available = _xgboost_installed()
    models = [
        ModelRegistryItem(
            key="weighted_ranker",
            name="Weighted Ranker",
            status="available",
            should_run_when=["feature row exists", "data quality is pass or warn"],
            data_source="source_backed",
        ),
        ModelRegistryItem(
            key="xgboost_ranker",
            name="XGBoost Ranker",
            status="available_if_xgboost_installed" if xgboost_available else "unavailable_dependency_missing",
            should_run_when=["xgboost installed", "feature row exists", "sufficient feature fields exist"],
            data_source="source_backed" if xgboost_available else "placeholder",
        ),
        ModelRegistryItem(key="garch_volatility", name="GARCH Volatility", status="placeholder", should_run_when=["sufficient historical candles exist"]),
        ModelRegistryItem(key="hmm_regime", name="HMM Regime", status="placeholder", should_run_when=["regime feature set exists"]),
        ModelRegistryItem(key="arimax_forecast", name="ARIMAX Forecast", status="placeholder", should_run_when=["macro and historical features exist"]),
        ModelRegistryItem(key="kalman_trend_filter", name="Kalman Trend Filter", status="placeholder", should_run_when=["historical candles exist"]),
        ModelRegistryItem(key="finbert_sentiment", name="FinBERT Sentiment", status="placeholder", should_run_when=["news or sentiment events exist"]),
    ]
    return {
        "data_source": "source_backed",
        "models": [model.model_dump() for model in models],
        "available_model_count": len([model for model in models if model.status in {"available", "available_if_xgboost_installed"}]),
        "placeholder_model_count": len([model for model in models if model.status == "placeholder"]),
    }


def _feature_fields_available(row: FeatureStoreRow) -> bool:
    return row.technical_score is not None and row.momentum_score is not None and row.rvol_score is not None


def plan_model_runs(request: ModelRunPlanRequest) -> ModelRunPlanResponse:
    rows = request.feature_rows or []
    has_rows = bool(rows)
    usable_rows = [row for row in rows if row.data_quality in {"pass", "warn"} and _feature_fields_available(row)]
    has_options = any(row.options_score is not None for row in rows)
    has_sentiment = any(row.sentiment_score is not None for row in rows)
    warnings: list[str] = []
    if not has_rows:
        warnings.append("No feature rows were supplied; run endpoint will build feature rows before scoring.")
    if rows and not usable_rows:
        warnings.append("Feature rows exist, but quality or required feature fields block live scoring.")

    models = [
        PlannedModel(
            key="weighted_ranker",
            status="available",
            should_run=bool(usable_rows),
            reason="Runs when feature rows pass or warn and core technical fields are present.",
            data_source="source_backed" if usable_rows else "placeholder",
        ),
        PlannedModel(
            key="xgboost_ranker",
            status="available_if_xgboost_installed" if _xgboost_installed() else "unavailable_dependency_missing",
            should_run=bool(usable_rows and _xgboost_installed()),
            reason="Runs only when xgboost is installed and feature rows have sufficient fields.",
            data_source="source_backed" if usable_rows and _xgboost_installed() else "placeholder",
        ),
        PlannedModel(key="garch_volatility", status="placeholder", should_run=False, reason="Requires sufficient historical candles.", data_source="placeholder"),
        PlannedModel(key="hmm_regime", status="placeholder", should_run=False, reason="Requires production regime feature set.", data_source="placeholder"),
        PlannedModel(key="arimax_forecast", status="placeholder", should_run=False, reason="Requires macro and historical feature matrix.", data_source="placeholder"),
        PlannedModel(key="kalman_trend_filter", status="placeholder", should_run=False, reason="Requires historical candles.", data_source="placeholder"),
        PlannedModel(key="finbert_sentiment", status="placeholder", should_run=False, reason="Requires news/sentiment inputs." if not has_sentiment else "Sentiment exists but model is placeholder.", data_source="placeholder"),
    ]
    if request.asset_class == "option" and not has_options:
        warnings.append("Options asset class requested, but options feature fields are missing.")
    return ModelRunPlanResponse(
        data_source="source_backed" if any(model.data_source == "source_backed" for model in models) else "placeholder",
        models=models,
        feature_rows_used=len(rows),
        warnings=warnings,
    )


def _run_weighted_ranker(rows: list[FeatureStoreRow]) -> dict[str, Any]:
    scored = sorted(
        [
            {
                "ticker": row.ticker,
                "score": round(
                    float(row.technical_score or 0) * 0.35
                    + float(row.momentum_score or 0) * 0.25
                    + float(row.rvol_score or 0) * 0.15
                    + float(row.liquidity_score or 0) * 0.15
                    + float(row.volatility_score or 0) * 0.10,
                    2,
                ),
                "data_quality": row.data_quality,
            }
            for row in rows
        ],
        key=lambda item: item["score"],
        reverse=True,
    )
    return {
        "model": "weighted_ranker",
        "status": "completed",
        "data_source": "source_backed",
        "scores": [{**item, "rank": index + 1} for index, item in enumerate(scored)],
    }


def run_model_orchestrator(request: ModelRunRequest) -> ModelRunResponse:
    rows = request.feature_rows or []
    warnings: list[str] = []
    if not rows:
        for symbol in request.symbols:
            run = run_feature_store_pipeline(
                FeatureStoreRunRequest(symbol=symbol, asset_class=request.asset_class, horizon=request.horizon, source=request.source)
            )
            rows.append(run.row)
            warnings.extend(run.warnings)

    plan = plan_model_runs(ModelRunPlanRequest(**request.model_dump(exclude={"feature_rows"}), feature_rows=rows))
    usable_rows = [row for row in rows if row.data_quality in {"pass", "warn"} and _feature_fields_available(row)]
    results: list[dict[str, Any]] = []
    if any(model.key == "weighted_ranker" and model.should_run for model in plan.models):
        results.append(_run_weighted_ranker(usable_rows))
    if any(model.key == "xgboost_ranker" and model.should_run for model in plan.models):
        ranker_rows = [
            RankerInputRow(
                symbol=row.ticker,
                feature_score=float(row.technical_score or 0),
                momentum_score=float(row.momentum_score or 0),
                rvol_score=float(row.rvol_score or 0),
                spread_quality_score=float(row.liquidity_score or 0),
                trend_vs_vwap_score=float(row.regime_score or row.technical_score or 0),
                volatility_score=float(row.volatility_score or 0),
            )
            for row in usable_rows
        ]
        results.append({"model": "xgboost_ranker", "status": "completed", "data_source": "source_backed", "result": run_xgboost_ranker(ranker_rows).model_dump()})

    for model in plan.models:
        if not model.should_run and model.status == "placeholder":
            results.append({"model": model.key, "status": "placeholder_not_run", "reason": model.reason, "data_source": "placeholder"})

    return ModelRunResponse(
        status="completed",
        data_source="source_backed" if any(row.data_source == "source_backed" for row in rows) else "placeholder",
        plan=plan,
        feature_rows=rows,
        results=results,
        warnings=warnings + plan.warnings,
    )
