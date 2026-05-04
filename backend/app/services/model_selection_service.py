"""Model Selection & Meta-Model Agent Service.

Implements Step 7 of the Adaptive Agentic Quant Workflow:
- Select scanner models, scoring models, validation models, and model weights
- Based on strategy ranking, market phase, regime, data availability, training status, cost budget
- NO paid LLM calls - deterministic selection only
- Uses central model registry eligibility gates for all scoring model selection
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.model_registry_service import get_model_selection_summary, is_model_eligible_for_active_scoring, skipped_model_record
from app.strategies.registry import StrategyConfig, get_strategy


SCANNER_MODELS = [
    {"key": "vwap_event_scanner", "name": "VWAP Event Scanner", "cost_tier": "cheap", "requires": ["price", "volume"]},
    {"key": "rvol_anomaly_scanner", "name": "RVOL Anomaly Scanner", "cost_tier": "cheap", "requires": ["price", "volume", "history"]},
    {"key": "breakout_retest_scanner", "name": "Breakout/Retest Scanner", "cost_tier": "cheap", "requires": ["price", "candles"]},
    {"key": "spread_liquidity_filter", "name": "Spread/Liquidity Filter", "cost_tier": "cheap", "requires": ["quote", "bid_ask"]},
    {"key": "options_flow_scanner", "name": "Options Flow Scanner", "cost_tier": "standard", "requires": ["options_chain"]},
    {"key": "crypto_momentum_scanner", "name": "Crypto Momentum Scanner", "cost_tier": "cheap", "requires": ["price", "volume", "crypto_compatible"]},
]

VALIDATION_MODELS = [
    {"key": "data_freshness_gate", "name": "Data Freshness Gate", "cost_tier": "free", "availability": "always", "requires": []},
    {"key": "regime_alignment_model", "name": "Regime Alignment Model", "cost_tier": "free", "availability": "always", "requires": ["regime_detection"]},
    {"key": "false_break_filter", "name": "False Break Filter", "cost_tier": "cheap", "availability": "always", "requires": ["price", "volume"]},
    {"key": "risk_gate", "name": "Risk Gate", "cost_tier": "free", "availability": "always", "requires": ["account_risk_config"]},
    {"key": "no_trade_gate", "name": "No-Trade Gate", "cost_tier": "free", "availability": "always", "requires": ["market_phase", "regime"]},
]

META_MODEL = {
    "key": "ensemble_confidence_model_v1",
    "name": "Ensemble Confidence Model V1",
    "cost_tier": "free",
    "availability": "always",
}


class SelectedModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_key: str
    model_name: str
    model_type: Literal["scanner", "scoring", "validation", "meta"]
    selected: bool
    reason: str
    skip_reason: str | None = None
    group: str | None = None
    allowed_for_final_trade_decision: bool = False


class ModelWeights(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    weighted_ranker_v1_weight: float = 0.5
    xgboost_ranker_weight: float = 0.0
    historical_similarity_weight: float = 0.0
    liquidity_model_weight: float = 0.25
    regime_alignment_weight: float = 0.25
    confidence_threshold: float = 0.6


class ModelSelectionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    strategy_key: str
    strategy_family: str | None = None
    market_phase: str
    active_loop: str
    regime: str
    horizon: Literal["day_trade", "swing", "one_month"]
    data_sources_available: list[str] | None = None
    llm_budget_mode: Literal["full", "conservative", "minimal", "disabled"] = "disabled"
    require_trained_models: bool = False


class ModelSelectionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "failed"]
    strategy_key: str
    selected_scanner_models: list[SelectedModel]
    selected_scoring_models: list[SelectedModel]
    selected_validation_models: list[SelectedModel]
    meta_model_weights: ModelWeights
    skipped_models: list[SelectedModel]
    candidate_models: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    untrained_internal_models: list[dict[str, Any]] = Field(default_factory=list)
    blocked_models: list[dict[str, Any]] = Field(default_factory=list)
    llm_validation_policy: Literal["strict", "moderate", "permissive", "disabled"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str = ""
    created_at: str


_LATEST_SELECTION: ModelSelectionResponse | None = None
_SELECTION_HISTORY: list[ModelSelectionResponse] = []


def _check_data_source_available(required: list[str], available: list[str] | None) -> bool:
    if not available:
        basic = ["price", "volume"]
        return all(r in basic for r in required)
    return all(r in available for r in required)


def _select_scanner_models(strategy: StrategyConfig, regime: str, market_phase: str, data_available: list[str] | None) -> list[SelectedModel]:
    selected: list[SelectedModel] = []
    basic_scanners = ["vwap_event_scanner", "rvol_anomaly_scanner"]

    for scanner in SCANNER_MODELS:
        key = scanner["key"]
        requires = scanner["requires"]
        if not _check_data_source_available(requires, data_available):
            selected.append(SelectedModel(model_key=key, model_name=scanner["name"], model_type="scanner", selected=False, reason="Data requirements not met", skip_reason=f"Requires: {requires}"))
            continue
        if strategy.asset_class == "option" and key == "options_flow_scanner":
            selected.append(SelectedModel(model_key=key, model_name=scanner["name"], model_type="scanner", selected=True, reason="Options strategy - options flow scanner selected"))
            continue
        if strategy.asset_class == "crypto" and key == "crypto_momentum_scanner":
            selected.append(SelectedModel(model_key=key, model_name=scanner["name"], model_type="scanner", selected=True, reason="Crypto strategy - crypto momentum scanner selected"))
            continue
        if key in basic_scanners:
            selected.append(SelectedModel(model_key=key, model_name=scanner["name"], model_type="scanner", selected=True, reason="Core scanner - always selected when data available"))
        elif key == "spread_liquidity_filter":
            selected.append(SelectedModel(model_key=key, model_name=scanner["name"], model_type="scanner", selected=_check_data_source_available(["bid_ask"], data_available), reason="Liquidity filter selection is based on bid/ask availability", skip_reason=None if _check_data_source_available(["bid_ask"], data_available) else "Bid/ask data not available"))
        elif key == "breakout_retest_scanner":
            selected.append(SelectedModel(model_key=key, model_name=scanner["name"], model_type="scanner", selected=strategy.timeframe in ["swing", "day_trade"], reason=f"Breakout scanner appropriate for {strategy.timeframe} timeframe", skip_reason=None if strategy.timeframe in ["swing", "day_trade"] else f"Less relevant for {strategy.timeframe} timeframe"))
        else:
            selected.append(SelectedModel(model_key=key, model_name=scanner["name"], model_type="scanner", selected=True, reason="Data available - scanner enabled"))
    return selected


def _select_scoring_models() -> list[SelectedModel]:
    summary = get_model_selection_summary()
    selected: list[SelectedModel] = []
    for model in summary["active_models"]:
        key = model["model_key"]
        eligible = is_model_eligible_for_active_scoring(key)
        selected.append(SelectedModel(
            model_key=key,
            model_name=model["display_name"],
            model_type="scoring",
            selected=eligible,
            reason="Governed model registry marks this model eligible for active research/paper scoring." if eligible else "Model is not eligible for active scoring.",
            skip_reason=None if eligible else model.get("blocked_reason"),
            group=model["group"],
            allowed_for_final_trade_decision=model.get("allowed_for_final_trade_decision", False),
        ))
    return selected


def _registry_skipped_models() -> list[SelectedModel]:
    summary = get_model_selection_summary()
    skipped: list[SelectedModel] = []
    for model in summary["untrained_internal_models"]:
        record = skipped_model_record(model["model_key"], status="not_trained")
        skipped.append(SelectedModel(model_key=model["model_key"], model_name=model["display_name"], model_type="scoring", selected=False, reason=record["reason"], skip_reason=record["next_step"], group=model["group"], allowed_for_final_trade_decision=False))
    for group_models in summary["candidate_models"].values():
        for model in group_models:
            record = skipped_model_record(model["model_key"], status="candidate_not_active")
            skipped.append(SelectedModel(model_key=model["model_key"], model_name=model["display_name"], model_type="scoring", selected=False, reason=record["reason"], skip_reason=record["next_step"], group=model["group"], allowed_for_final_trade_decision=False))
    for model in summary["blocked_models"]:
        record = skipped_model_record(model["model_key"], status="blocked")
        skipped.append(SelectedModel(model_key=model["model_key"], model_name=model["display_name"], model_type="scoring", selected=False, reason=record["reason"], skip_reason=record["next_step"], group=model["group"], allowed_for_final_trade_decision=False))
    return skipped


def _select_validation_models(strategy: StrategyConfig, regime: str, market_phase: str, data_available: list[str] | None) -> list[SelectedModel]:
    selected: list[SelectedModel] = []
    for model in VALIDATION_MODELS:
        key = model["key"]
        requires = model["requires"]
        if key in ["data_freshness_gate", "risk_gate", "no_trade_gate"]:
            selected.append(SelectedModel(model_key=key, model_name=model["name"], model_type="validation", selected=True, reason="Core validation - always enabled"))
            continue
        if not _check_data_source_available(requires, data_available):
            selected.append(SelectedModel(model_key=key, model_name=model["name"], model_type="validation", selected=False, reason="Validation would help", skip_reason=f"Requires: {requires}"))
            continue
        if key == "regime_alignment_model":
            selected.append(SelectedModel(model_key=key, model_name=model["name"], model_type="validation", selected=regime != "unknown", reason="Regime detected - alignment check enabled" if regime != "unknown" else "Would validate regime alignment", skip_reason=None if regime != "unknown" else "Regime unknown - cannot validate alignment"))
            continue
        if key == "false_break_filter":
            selected.append(SelectedModel(model_key=key, model_name=model["name"], model_type="validation", selected="breakout" in strategy.edge_signals, reason="Breakout signals present - false break filter enabled" if "breakout" in strategy.edge_signals else "Available for breakout detection", skip_reason=None if "breakout" in strategy.edge_signals else "No breakout signals in strategy"))
            continue
        selected.append(SelectedModel(model_key=key, model_name=model["name"], model_type="validation", selected=True, reason="Validation model selected"))
    return selected


def _calculate_meta_weights(selected_scoring: list[SelectedModel], strategy: StrategyConfig, regime: str) -> ModelWeights:
    weights = ModelWeights()
    has_weighted = any(m.model_key == "weighted_ranker_v1" and m.selected for m in selected_scoring)
    if not has_weighted:
        weights.weighted_ranker_v1_weight = 0.0
    if regime == "volatility_expansion" and has_weighted:
        weights.liquidity_model_weight += 0.1
        weights.weighted_ranker_v1_weight -= 0.1
    if strategy.asset_class == "option":
        weights.confidence_threshold = 0.7
    # XGBoost remains zero unless the registry eventually makes it eligible and this code is intentionally updated after validation.
    weights.xgboost_ranker_weight = 0.0
    return weights


def _determine_llm_validation_policy(llm_budget_mode: str, strategy: StrategyConfig) -> str:
    if llm_budget_mode == "disabled":
        return "disabled"
    if llm_budget_mode == "minimal":
        return "permissive"
    if llm_budget_mode == "conservative":
        return "moderate"
    if llm_budget_mode == "full":
        return "strict" if strategy.requires_human_approval else "moderate"
    return "disabled"


def run_model_selection(request: ModelSelectionRequest) -> ModelSelectionResponse:
    global _LATEST_SELECTION, _SELECTION_HISTORY
    run_id = f"modelsel-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    strategy = get_strategy(request.strategy_key)
    if not strategy:
        return ModelSelectionResponse(run_id=run_id, status="failed", strategy_key=request.strategy_key, selected_scanner_models=[], selected_scoring_models=[], selected_validation_models=[], meta_model_weights=ModelWeights(), skipped_models=[], llm_validation_policy="disabled", blockers=[f"Strategy '{request.strategy_key}' not found"], reason="Strategy not available", created_at=created_at)

    registry_summary = get_model_selection_summary()
    scanner_models = _select_scanner_models(strategy, request.regime, request.market_phase, request.data_sources_available)
    scoring_models = _select_scoring_models()
    validation_models = _select_validation_models(strategy, request.regime, request.market_phase, request.data_sources_available)
    meta_weights = _calculate_meta_weights(scoring_models, strategy, request.regime)
    llm_policy = _determine_llm_validation_policy(request.llm_budget_mode, strategy)
    skipped = [m for m in scanner_models if not m.selected] + [m for m in scoring_models if not m.selected] + [m for m in validation_models if not m.selected] + _registry_skipped_models()
    selected_count = sum(1 for m in scanner_models + scoring_models + validation_models if m.selected)
    selected_scoring_count = sum(1 for m in scoring_models if m.selected)

    if selected_count == 0:
        status = "failed"
        blockers = ["No models selected - cannot proceed"]
        warnings: list[str] = []
    elif selected_scoring_count == 0:
        status = "partial"
        blockers = []
        warnings = ["No eligible scoring models selected. weighted_ranker_v1 should be the active baseline."]
    else:
        status = "completed"
        blockers = []
        warnings = ["Only registry-eligible scoring models are selected. XGBoost and candidates are skipped unless promoted by governance gates."]

    response = ModelSelectionResponse(
        run_id=run_id,
        status=status,
        strategy_key=request.strategy_key,
        selected_scanner_models=[m for m in scanner_models if m.selected],
        selected_scoring_models=[m for m in scoring_models if m.selected],
        selected_validation_models=[m for m in validation_models if m.selected],
        meta_model_weights=meta_weights,
        skipped_models=skipped,
        candidate_models=registry_summary["candidate_models"],
        untrained_internal_models=registry_summary["untrained_internal_models"],
        blocked_models=registry_summary["blocked_models"],
        llm_validation_policy=llm_policy,
        blockers=blockers,
        warnings=warnings,
        reason=f"Governed model stack selected for {strategy.display_name}",
        created_at=created_at,
    )
    _LATEST_SELECTION = response
    _SELECTION_HISTORY.append(response)
    if len(_SELECTION_HISTORY) > 100:
        _SELECTION_HISTORY = _SELECTION_HISTORY[-100:]
    return response


def get_latest_model_selection() -> ModelSelectionResponse | None:
    return _LATEST_SELECTION


def list_model_selection_history(limit: int = 20) -> list[ModelSelectionResponse]:
    return _SELECTION_HISTORY[-limit:]


def get_model_registry() -> dict:
    return get_model_selection_summary()
