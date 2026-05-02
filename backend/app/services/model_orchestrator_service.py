from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.feature_store_service import FeatureStoreRow, get_feature_row_by_id, get_feature_rows_for_symbol
from app.services.model_runner_service import run_selected_models
from app.strategies.registry import StrategyConfig, get_strategy


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
    strategy_key: str | None = None
    feature_row_id: str | None = None
    selected_models: list[str] | None = None
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
    model_outputs: list[dict[str, Any]] = Field(default_factory=list)
    completed_models: list[dict[str, Any]] = Field(default_factory=list)
    blocked_models: list[dict[str, Any]] = Field(default_factory=list)
    placeholder_models: list[dict[str, Any]] = Field(default_factory=list)
    not_trained_models: list[dict[str, Any]] = Field(default_factory=list)
    next_action: str = "Review model outputs with risk filter before recommendation."
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
            should_run_when=["xgboost installed", "feature row exists", "trained model artifact exists", "walk-forward validation complete"],
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
            should_run=bool(has_rows and usable_rows),
            reason="Runs when a feature row exists, quality is pass or warn, and core technical fields are present.",
            data_source="source_backed" if usable_rows else "placeholder",
        ),
        PlannedModel(
            key="xgboost_ranker",
            status="available_if_xgboost_installed" if _xgboost_installed() else "unavailable_dependency_missing",
            should_run=bool(usable_rows and _xgboost_installed()),
            reason="Eligible for wrapper execution when xgboost is installed and feature rows have sufficient fields; inference still requires a trained artifact.",
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


def _strategy_for_request(request: ModelRunRequest) -> StrategyConfig:
    if request.strategy_key:
        strategy = get_strategy(request.strategy_key)
        if strategy:
            return strategy
    fallback_key = "stock_day_trading" if request.horizon == "day_trade" else "stock_swing"
    return get_strategy(fallback_key) or get_strategy("stock_swing")  # type: ignore[return-value]


def _rows_for_request(request: ModelRunRequest) -> list[FeatureStoreRow]:
    if request.feature_rows:
        return request.feature_rows
    if request.feature_row_id:
        row = get_feature_row_by_id(request.feature_row_id)
        return [row] if row else []
    rows: list[FeatureStoreRow] = []
    for symbol in request.symbols:
        symbol_rows = get_feature_rows_for_symbol(symbol)
        if symbol_rows:
            rows.append(symbol_rows[0])
    return rows


def run_model_orchestrator(request: ModelRunRequest) -> ModelRunResponse:
    rows = _rows_for_request(request)
    warnings: list[str] = []
    if not rows:
        plan = plan_model_runs(ModelRunPlanRequest(**request.model_dump(exclude={"feature_rows"}), feature_rows=[]))
        return ModelRunResponse(
            status="blocked",
            data_source="placeholder",
            plan=plan,
            feature_rows=[],
            results=[],
            blocked_models=[{"model": "model_orchestrator", "status": "blocked", "reason": "No feature row exists. Run /api/feature-store/run first or provide feature_row_id.", "data_source": "placeholder"}],
            next_action="Run feature-store pipeline before model execution.",
            warnings=warnings + ["No feature rows available for model execution."],
        )

    plan = plan_model_runs(ModelRunPlanRequest(**request.model_dump(exclude={"feature_rows"}), feature_rows=rows))
    usable_rows = [row for row in rows if row.data_quality in {"pass", "warn"} and _feature_fields_available(row)]
    selected_models = request.selected_models or [model.key for model in plan.models if model.should_run]
    if "weighted_ranker" not in selected_models and usable_rows:
        selected_models.insert(0, "weighted_ranker")
    strategy = _strategy_for_request(request)
    runner_outputs = {"completed_models": [], "blocked_models": [], "placeholder_models": [], "not_trained_models": [], "model_outputs": []}
    for row in usable_rows:
        row_outputs = run_selected_models(row, strategy, selected_models)
        for key, values in row_outputs.items():
            runner_outputs[key].extend(values)

    for model in plan.models:
        if not model.should_run and model.status == "placeholder":
            runner_outputs["placeholder_models"].append({"model": model.key, "model_name": model.key, "status": "placeholder_not_run", "reason": model.reason, "data_source": "placeholder"})

    model_outputs = runner_outputs["model_outputs"] + runner_outputs["placeholder_models"]
    completed = runner_outputs["completed_models"]
    not_trained = runner_outputs["not_trained_models"]
    next_action = "Review weighted_ranker_v1 with risk filter before recommendation." if completed else "Resolve blocked model inputs before treating outputs as actionable."

    return ModelRunResponse(
        status="completed",
        data_source="source_backed" if any(row.data_source == "source_backed" for row in rows) else "placeholder",
        plan=plan,
        feature_rows=rows,
        results=model_outputs,
        model_outputs=model_outputs,
        completed_models=completed,
        blocked_models=runner_outputs["blocked_models"],
        placeholder_models=runner_outputs["placeholder_models"],
        not_trained_models=not_trained,
        next_action=next_action,
        warnings=warnings + plan.warnings,
    )
