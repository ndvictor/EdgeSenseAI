"""Model Selection & Meta-Model Agent Service.

Implements Step 7 of the Adaptive Agentic Quant Workflow:
- Select scanner models, scoring models, validation models, and model weights
- Based on strategy ranking, market phase, regime, data availability, training status, cost budget
- NO paid LLM calls - deterministic selection only
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.strategies.registry import StrategyConfig, get_strategy


# Model registry definitions
SCANNER_MODELS = [
    {"key": "vwap_event_scanner", "name": "VWAP Event Scanner", "cost_tier": "cheap", "requires": ["price", "volume"]},
    {"key": "rvol_anomaly_scanner", "name": "RVOL Anomaly Scanner", "cost_tier": "cheap", "requires": ["price", "volume", "history"]},
    {"key": "breakout_retest_scanner", "name": "Breakout/Retest Scanner", "cost_tier": "cheap", "requires": ["price", "candles"]},
    {"key": "spread_liquidity_filter", "name": "Spread/Liquidity Filter", "cost_tier": "cheap", "requires": ["quote", "bid_ask"]},
    {"key": "options_flow_scanner", "name": "Options Flow Scanner", "cost_tier": "standard", "requires": ["options_chain"]},
    {"key": "crypto_momentum_scanner", "name": "Crypto Momentum Scanner", "cost_tier": "cheap", "requires": ["price", "volume", "crypto_compatible"]},
]

SCORING_MODELS = [
    {"key": "weighted_ranker_v1", "name": "Weighted Ranker V1", "cost_tier": "free", "availability": "always", "requires": []},
    {"key": "xgboost_ranker", "name": "XGBoost Ranker", "cost_tier": "cheap", "availability": "not_trained", "requires": ["trained_artifact"]},
    {"key": "logistic_meta_labeler", "name": "Logistic Meta Labeler", "cost_tier": "cheap", "availability": "not_trained", "requires": ["trained_artifact"]},
    {"key": "historical_similarity_model", "name": "Historical Similarity Model", "cost_tier": "cheap", "availability": "not_trained", "requires": ["historical_db", "embeddings"]},
    {"key": "liquidity_model", "name": "Liquidity Model", "cost_tier": "free", "availability": "always", "requires": ["volume", "quote"]},
    {"key": "news_relevance_model", "name": "News Relevance Model", "cost_tier": "llm", "availability": "llm_budget_dependent", "requires": ["news_feed", "llm_budget"]},
    {"key": "options_validation_model", "name": "Options Validation Model", "cost_tier": "standard", "availability": "conditional", "requires": ["options_chain", "greeks"]},
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
    """A selected model with metadata."""

    model_config = ConfigDict(protected_namespaces=())

    model_key: str
    model_name: str
    model_type: Literal["scanner", "scoring", "validation", "meta"]
    selected: bool
    reason: str
    skip_reason: str | None = None


class ModelWeights(BaseModel):
    """Meta-model weights for ensemble scoring."""

    model_config = ConfigDict(protected_namespaces=())

    weighted_ranker_v1_weight: float = 0.5
    xgboost_ranker_weight: float = 0.0
    historical_similarity_weight: float = 0.0
    liquidity_model_weight: float = 0.25
    regime_alignment_weight: float = 0.25
    confidence_threshold: float = 0.6


class ModelSelectionRequest(BaseModel):
    """Request to run model selection."""

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
    """Response from model selection."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "failed"]
    strategy_key: str
    selected_scanner_models: list[SelectedModel]
    selected_scoring_models: list[SelectedModel]
    selected_validation_models: list[SelectedModel]
    meta_model_weights: ModelWeights
    skipped_models: list[SelectedModel]
    llm_validation_policy: Literal["strict", "moderate", "permissive", "disabled"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str = ""
    created_at: str


# In-memory storage
_LATEST_SELECTION: ModelSelectionResponse | None = None
_SELECTION_HISTORY: list[ModelSelectionResponse] = []


def _check_data_source_available(required: list[str], available: list[str] | None) -> bool:
    """Check if required data sources are available."""
    if not available:
        # Assume basic price/volume always available if no specific list
        basic = ["price", "volume"]
        return all(r in basic for r in required)

    return all(r in available for r in required)


def _select_scanner_models(
    strategy: StrategyConfig,
    regime: str,
    market_phase: str,
    data_available: list[str] | None,
) -> list[SelectedModel]:
    """Select appropriate scanner models."""
    selected: list[SelectedModel] = []

    # Always include basic scanners
    basic_scanners = ["vwap_event_scanner", "rvol_anomaly_scanner"]

    for scanner in SCANNER_MODELS:
        key = scanner["key"]
        requires = scanner["requires"]

        # Check data availability
        if not _check_data_source_available(requires, data_available):
            selected.append(SelectedModel(
                model_key=key,
                model_name=scanner["name"],
                model_type="scanner",
                selected=False,
                reason="Data requirements not met",
                skip_reason=f"Requires: {requires}",
            ))
            continue

        # Check asset class compatibility
        if strategy.asset_class == "option":
            if key == "options_flow_scanner":
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=scanner["name"],
                    model_type="scanner",
                    selected=True,
                    reason="Options strategy - options flow scanner selected",
                ))
                continue
            elif key == "crypto_momentum_scanner":
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=scanner["name"],
                    model_type="scanner",
                    selected=False,
                    reason="Incompatible asset class",
                    skip_reason="Options strategy - crypto scanner not applicable",
                ))
                continue

        if strategy.asset_class == "crypto":
            if key == "crypto_momentum_scanner":
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=scanner["name"],
                    model_type="scanner",
                    selected=True,
                    reason="Crypto strategy - crypto momentum scanner selected",
                ))
                continue

        # Select basic scanners for all
        if key in basic_scanners:
            selected.append(SelectedModel(
                model_key=key,
                model_name=scanner["name"],
                model_type="scanner",
                selected=True,
                reason="Core scanner - always selected when data available",
            ))
        elif key == "spread_liquidity_filter":
            # Select if bid/ask available
            if _check_data_source_available(["bid_ask"], data_available):
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=scanner["name"],
                    model_type="scanner",
                    selected=True,
                    reason="Bid/ask data available - liquidity filter enabled",
                ))
            else:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=scanner["name"],
                    model_type="scanner",
                    selected=False,
                    reason="Liquidity filter useful but not required",
                    skip_reason="Bid/ask data not available",
                ))
        elif key == "breakout_retest_scanner":
            # Select based on timeframe
            if strategy.timeframe in ["swing", "day_trade"]:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=scanner["name"],
                    model_type="scanner",
                    selected=True,
                    reason=f"Breakout scanner appropriate for {strategy.timeframe} timeframe",
                ))
            else:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=scanner["name"],
                    model_type="scanner",
                    selected=False,
                    reason="Breakout scanner available",
                    skip_reason=f"Less relevant for {strategy.timeframe} timeframe",
                ))
        else:
            # Other scanners - include if data available
            selected.append(SelectedModel(
                model_key=key,
                model_name=scanner["name"],
                model_type="scanner",
                selected=True,
                reason="Data available - scanner enabled",
            ))

    return selected


def _select_scoring_models(
    strategy: StrategyConfig,
    llm_budget_mode: str,
    require_trained: bool,
    data_available: list[str] | None,
) -> list[SelectedModel]:
    """Select appropriate scoring models."""
    selected: list[SelectedModel] = []

    for model in SCORING_MODELS:
        key = model["key"]
        requires = model["requires"]
        availability = model["availability"]
        cost_tier = model["cost_tier"]

        # Always select weighted_ranker_v1 (free, always available)
        if key == "weighted_ranker_v1":
            selected.append(SelectedModel(
                model_key=key,
                model_name=model["name"],
                model_type="scoring",
                selected=True,
                reason="Always available - deterministic ranker",
            ))
            continue

        # Check LLM budget for news model
        if key == "news_relevance_model":
            if llm_budget_mode in ["full", "conservative"]:
                if _check_data_source_available(requires, data_available):
                    selected.append(SelectedModel(
                        model_key=key,
                        model_name=model["name"],
                        model_type="scoring",
                        selected=True,
                        reason="LLM budget allows news relevance scoring",
                    ))
                else:
                    selected.append(SelectedModel(
                        model_key=key,
                        model_name=model["name"],
                        model_type="scoring",
                        selected=False,
                        reason="News relevance would help",
                        skip_reason="News feed not available",
                    ))
            else:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="scoring",
                    selected=False,
                    reason="LLM-powered model",
                    skip_reason="LLM budget mode prevents use",
                ))
            continue

        # Check options model
        if key == "options_validation_model":
            if strategy.asset_class == "option":
                if _check_data_source_available(requires, data_available):
                    selected.append(SelectedModel(
                        model_key=key,
                        model_name=model["name"],
                        model_type="scoring",
                        selected=True,
                        reason="Options strategy with options data available",
                    ))
                else:
                    selected.append(SelectedModel(
                        model_key=key,
                        model_name=model["name"],
                        model_type="scoring",
                        selected=False,
                        reason="Options validation recommended",
                        skip_reason="Options chain data not available",
                    ))
            else:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="scoring",
                    selected=False,
                    reason="Options-specific model",
                    skip_reason="Not an options strategy",
                ))
            continue

        # Check trained model requirements
        if availability == "not_trained":
            if require_trained:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="scoring",
                    selected=False,
                    reason="ML model not yet trained",
                    skip_reason="require_trained_models=true - skipping untrained model",
                ))
            else:
                # Include but note it's not trained
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="scoring",
                    selected=False,
                    reason="ML model (not trained - skipping)",
                    skip_reason="Model artifact not available",
                ))
            continue

        # Check data requirements
        if not _check_data_source_available(requires, data_available):
            selected.append(SelectedModel(
                model_key=key,
                model_name=model["name"],
                model_type="scoring",
                selected=False,
                reason=f"Would enhance scoring",
                skip_reason=f"Requires: {requires}",
            ))
            continue

        # Default: select if cheap/free and data available
        if cost_tier in ["free", "cheap"]:
            selected.append(SelectedModel(
                model_key=key,
                model_name=model["name"],
                model_type="scoring",
                selected=True,
                reason="Cheap model with data available - selected",
            ))
        else:
            selected.append(SelectedModel(
                model_key=key,
                model_name=model["name"],
                model_type="scoring",
                selected=False,
                reason="Available but more expensive",
                skip_reason="Cost tier higher than current budget allows",
            ))

    return selected


def _select_validation_models(
    strategy: StrategyConfig,
    regime: str,
    market_phase: str,
    data_available: list[str] | None,
) -> list[SelectedModel]:
    """Select appropriate validation models."""
    selected: list[SelectedModel] = []

    for model in VALIDATION_MODELS:
        key = model["key"]
        requires = model["requires"]

        # Always select data_freshness_gate and risk_gate
        if key in ["data_freshness_gate", "risk_gate", "no_trade_gate"]:
            selected.append(SelectedModel(
                model_key=key,
                model_name=model["name"],
                model_type="validation",
                selected=True,
                reason="Core validation - always enabled",
            ))
            continue

        # Check data requirements
        if not _check_data_source_available(requires, data_available):
            selected.append(SelectedModel(
                model_key=key,
                model_name=model["name"],
                model_type="validation",
                selected=False,
                reason="Validation would help",
                skip_reason=f"Requires: {requires}",
            ))
            continue

        # Regime alignment model - select if regime detected
        if key == "regime_alignment_model":
            if regime != "unknown":
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="validation",
                    selected=True,
                    reason="Regime detected - alignment check enabled",
                ))
            else:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="validation",
                    selected=False,
                    reason="Would validate regime alignment",
                    skip_reason="Regime unknown - cannot validate alignment",
                ))
            continue

        # False break filter - select for breakout strategies
        if key == "false_break_filter":
            if "breakout" in strategy.edge_signals:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="validation",
                    selected=True,
                    reason="Breakout signals present - false break filter enabled",
                ))
            else:
                selected.append(SelectedModel(
                    model_key=key,
                    model_name=model["name"],
                    model_type="validation",
                    selected=False,
                    reason="Available for breakout detection",
                    skip_reason="No breakout signals in strategy",
                ))
            continue

        # Default: select
        selected.append(SelectedModel(
            model_key=key,
            model_name=model["name"],
            model_type="validation",
            selected=True,
            reason="Validation model selected",
        ))

    return selected


def _calculate_meta_weights(
    selected_scoring: list[SelectedModel],
    strategy: StrategyConfig,
    regime: str,
) -> ModelWeights:
    """Calculate meta-model weights based on selected models."""
    weights = ModelWeights()

    # Check which models are actually selected
    has_xgboost = any(m.model_key == "xgboost_ranker" and m.selected for m in selected_scoring)
    has_historical = any(m.model_key == "historical_similarity_model" and m.selected for m in selected_scoring)
    has_liquidity = any(m.model_key == "liquidity_model" and m.selected for m in selected_scoring)

    # Adjust weights based on availability
    if has_xgboost:
        weights.weighted_ranker_v1_weight = 0.3
        weights.xgboost_ranker_weight = 0.3
        weights.liquidity_model_weight = 0.2
        weights.regime_alignment_weight = 0.2
    elif has_historical:
        weights.weighted_ranker_v1_weight = 0.4
        weights.historical_similarity_weight = 0.2
        weights.liquidity_model_weight = 0.2
        weights.regime_alignment_weight = 0.2
    else:
        # Default: weighted ranker dominant
        weights.weighted_ranker_v1_weight = 0.5
        weights.liquidity_model_weight = 0.25
        weights.regime_alignment_weight = 0.25

    # Adjust for regime
    if regime == "volatility_expansion":
        # Increase liquidity weight in high vol
        weights.liquidity_model_weight += 0.1
        weights.weighted_ranker_v1_weight -= 0.1

    # Adjust for strategy
    if strategy.asset_class == "option":
        # More conservative for options
        weights.confidence_threshold = 0.7

    return weights


def _determine_llm_validation_policy(
    llm_budget_mode: str,
    strategy: StrategyConfig,
) -> str:
    """Determine LLM validation policy based on budget and strategy."""
    if llm_budget_mode == "disabled":
        return "disabled"
    elif llm_budget_mode == "minimal":
        return "permissive"  # Only anomalies trigger review
    elif llm_budget_mode == "conservative":
        return "moderate"
    elif llm_budget_mode == "full":
        return "strict" if strategy.requires_human_approval else "moderate"
    else:
        return "disabled"


def run_model_selection(request: ModelSelectionRequest) -> ModelSelectionResponse:
    """Run model selection for a strategy."""
    global _LATEST_SELECTION

    run_id = f"modelsel-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    # Get strategy
    strategy = get_strategy(request.strategy_key)
    if not strategy:
        return ModelSelectionResponse(
            run_id=run_id,
            status="failed",
            strategy_key=request.strategy_key,
            selected_scanner_models=[],
            selected_scoring_models=[],
            selected_validation_models=[],
            meta_model_weights=ModelWeights(),
            skipped_models=[],
            llm_validation_policy="disabled",
            blockers=[f"Strategy '{request.strategy_key}' not found"],
            warnings=[],
            reason="Strategy not available",
            created_at=created_at,
        )

    # Select models
    scanner_models = _select_scanner_models(
        strategy=strategy,
        regime=request.regime,
        market_phase=request.market_phase,
        data_available=request.data_sources_available,
    )

    scoring_models = _select_scoring_models(
        strategy=strategy,
        llm_budget_mode=request.llm_budget_mode,
        require_trained=request.require_trained_models,
        data_available=request.data_sources_available,
    )

    validation_models = _select_validation_models(
        strategy=strategy,
        regime=request.regime,
        market_phase=request.market_phase,
        data_available=request.data_sources_available,
    )

    # Calculate meta weights
    meta_weights = _calculate_meta_weights(scoring_models, strategy, request.regime)

    # Determine LLM validation policy
    llm_policy = _determine_llm_validation_policy(request.llm_budget_mode, strategy)

    # Build skipped models list
    skipped = (
        [m for m in scanner_models if not m.selected] +
        [m for m in scoring_models if not m.selected] +
        [m for m in validation_models if not m.selected]
    )

    # Count selected
    selected_count = (
        sum(1 for m in scanner_models if m.selected) +
        sum(1 for m in scoring_models if m.selected) +
        sum(1 for m in validation_models if m.selected)
    )

    # Determine status
    if selected_count == 0:
        status = "failed"
        blockers = ["No models selected - cannot proceed"]
    elif sum(1 for m in scoring_models if m.selected) == 0:
        status = "partial"
        blockers = []
        warnings = ["No scoring models selected - weighted_ranker_v1 should always be available"]
    else:
        status = "completed"
        blockers = []
        warnings = []

    response = ModelSelectionResponse(
        run_id=run_id,
        status=status,
        strategy_key=request.strategy_key,
        selected_scanner_models=[m for m in scanner_models if m.selected],
        selected_scoring_models=[m for m in scoring_models if m.selected],
        selected_validation_models=[m for m in validation_models if m.selected],
        meta_model_weights=meta_weights,
        skipped_models=skipped,
        llm_validation_policy=llm_policy,
        blockers=blockers,
        warnings=warnings,
        reason=f"Model stack selected for {strategy.display_name}",
        created_at=created_at,
    )

    _LATEST_SELECTION = response
    _SELECTION_HISTORY.append(response)

    # Keep only last 100
    if len(_SELECTION_HISTORY) > 100:
        _SELECTION_HISTORY = _SELECTION_HISTORY[-100:]

    return response


def get_latest_model_selection() -> ModelSelectionResponse | None:
    """Get the most recent model selection."""
    return _LATEST_SELECTION


def list_model_selection_history(limit: int = 20) -> list[ModelSelectionResponse]:
    """List recent model selections."""
    return _SELECTION_HISTORY[-limit:]


def get_model_registry() -> dict:
    """Get the model registry for reference."""
    return {
        "scanner_models": SCANNER_MODELS,
        "scoring_models": SCORING_MODELS,
        "validation_models": VALIDATION_MODELS,
        "meta_model": META_MODEL,
    }
