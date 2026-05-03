"""Strategy Ranking Model Service.

Implements Step 6 of the Adaptive Agentic Quant Workflow:
- Numerically rank strategies after debate
- Deterministic scoring based on debate fit_score + adjustments
- Returns active/conditional/disabled status per strategy
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.strategy_debate_service import (
    StrategyArgument,
    StrategyDebateResponse,
    get_latest_strategy_debate,
    run_strategy_debate,
)
from app.strategies.registry import StrategyConfig, get_strategy, list_strategies


class RankedStrategy(BaseModel):
    """A ranked strategy with full metadata."""

    model_config = ConfigDict(protected_namespaces=())

    strategy_key: str
    strategy_family: str
    rank: int = 0
    strategy_score: float = Field(default=50.0, ge=0.0, le=100.0)
    status: Literal["active", "conditional", "disabled"] = "conditional"
    model_stack_hint: list[str] = Field(default_factory=list)
    scanner_needs: list[str] = Field(default_factory=list)
    data_needs: list[str] = Field(default_factory=list)
    reason: str = ""
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StrategyRankingRequest(BaseModel):
    """Request to run strategy ranking."""

    model_config = ConfigDict(protected_namespaces=())

    debate_run_id: str | None = None  # Use latest if not provided
    market_phase: str
    active_loop: str
    regime: str
    horizon: Literal["day_trade", "swing", "one_month"]
    account_equity: float | None = None
    buying_power: float | None = None
    strategy_keys: list[str] | None = None
    source: str | None = None  # Data source availability check


class StrategyRankingResponse(BaseModel):
    """Response from strategy ranking."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "failed"]
    debate_run_id: str | None
    market_phase: str
    active_loop: str
    regime: str
    horizon: str
    ranked_strategies: list[RankedStrategy]
    active_strategies: list[str]
    disabled_strategies: list[str]
    top_strategy_key: str | None
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    created_at: str


# In-memory storage
_LATEST_RANKING: StrategyRankingResponse | None = None
_RANKING_HISTORY: list[StrategyRankingResponse] = []


def _adjust_score_for_market_phase(base_score: float, market_phase: str, strategy: StrategyConfig) -> float:
    """Adjust score based on market phase."""
    adjustments = {
        "market_open_first_30_min": {"stock_day_trading": 10, "crypto_intraday": 10, "stock_swing": -5},
        "pre_market": {"stock_day_trading": 5, "stock_swing": 5, "options_day_trading": -10},
        "market_open": {"stock_swing": 5, "crypto_swing": 5},
        "midday": {"stock_day_trading": -10, "crypto_intraday": -5},
        "power_hour": {"stock_day_trading": 8, "crypto_intraday": 5, "stock_one_month": -5},
        "after_hours": {"stock_swing": -5, "stock_day_trading": -15, "options_swing": -10},
        "market_closed": {"stock_swing": 0, "stock_one_month": 5},  # Favors research/planning
    }

    strategy_family = f"{strategy.asset_class}_{strategy.timeframe}"
    adjustment = adjustments.get(market_phase, {}).get(strategy_family, 0)
    return base_score + adjustment


def _adjust_score_for_regime(base_score: float, regime: str, strategy: StrategyConfig) -> float:
    """Adjust score based on regime."""
    adjustments = {
        "risk_on": {"stock_swing": 15, "crypto_swing": 15, "stock_day_trading": 10, "options_earnings": -10},
        "risk_off": {"stock_swing": 10, "stock_one_month": 5, "crypto_swing": -20, "crypto_intraday": -15},
        "chop": {"stock_swing": -5, "stock_day_trading": -5, "crypto_swing": -10},
        "momentum": {"stock_swing": 15, "crypto_swing": 15, "stock_day_trading": 10, "options_swing": 5},
        "mean_reversion": {"stock_day_trading": 10, "crypto_intraday": 10, "stock_swing": -5},
        "volatility_expansion": {"stock_swing": -10, "stock_day_trading": -20, "options_swing": -10, "crypto_intraday": -10},
        "unknown": {},
    }

    strategy_family = f"{strategy.asset_class}_{strategy.timeframe}"
    adjustment = adjustments.get(regime, {}).get(strategy_family, 0)
    return base_score + adjustment


def _adjust_score_for_data_availability(
    base_score: float,
    strategy: StrategyConfig,
    source: str | None,
) -> float:
    """Adjust score based on data source availability."""
    # Simplified - in real implementation check actual provider status
    adjustment = 0

    # Options strategies need options data
    if strategy.asset_class == "option":
        # Would check if options provider configured
        adjustment -= 5  # Slight penalty for complexity

    # Crypto strategies need crypto data
    if strategy.asset_class == "crypto":
        # Would check if crypto provider configured
        pass

    return base_score + adjustment


def _adjust_score_for_account_constraints(
    base_score: float,
    strategy: StrategyConfig,
    account_equity: float | None,
    buying_power: float | None,
) -> float:
    """Adjust score based on account constraints."""
    adjustment = 0

    # Small accounts favor liquid strategies
    if account_equity is not None:
        if account_equity < 25000 and strategy.timeframe == "day_trade":
            # PDT rule consideration
            adjustment -= 10

    # Buying power constraints
    if buying_power is not None:
        if buying_power < 5000 and strategy.asset_class == "option":
            # Limited options buying power
            adjustment -= 5

    return base_score + adjustment


def _calculate_model_stack_hint(strategy: StrategyConfig, score: float) -> list[str]:
    """Determine recommended model stack for strategy."""
    stack = ["weighted_ranker_v1"]  # Always available

    if score >= 70:
        # High confidence - can use more models
        if "xgboost_ranker" in strategy.required_models or "xgboost_ranker" in strategy.optional_models:
            stack.append("xgboost_ranker")
        if "hmm_regime" in strategy.optional_models:
            stack.append("hmm_regime")

    if score >= 60:
        if "historical_similarity" in strategy.optional_models:
            stack.append("historical_similarity_model")

    if strategy.asset_class == "option":
        stack.append("options_validation_model")

    if strategy.asset_class == "crypto":
        stack.append("liquidity_model")

    return stack


def _determine_strategy_status(
    score: float,
    allowed: bool,
    disable_reason: str | None,
) -> tuple[str, list[str], list[str]]:
    """Determine strategy status and any blockers/warnings."""
    if not allowed:
        return "disabled", [disable_reason or "Strategy disabled"], []

    if score >= 70:
        return "active", [], []
    elif score >= 50:
        return "conditional", [], [f"Score {score:.1f} is moderate - use with caution"]
    elif score >= 30:
        return "conditional", [], [f"Low score {score:.1f} - review carefully"]
    else:
        return "conditional", [], [f"Very low score {score:.1f} - consider avoiding"]


def run_strategy_ranking(request: StrategyRankingRequest) -> StrategyRankingResponse:
    """Run strategy ranking based on debate results and additional factors."""
    global _LATEST_RANKING

    run_id = f"rank-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    # Get debate results
    debate: StrategyDebateResponse | None = None
    if request.debate_run_id:
        # Find specific debate in history
        for d in get_latest_strategy_debate() or []:
            if isinstance(d, list):
                continue
            if d.run_id == request.debate_run_id:
                debate = d
                break

    if not debate:
        # Run new debate
        debate = run_strategy_debate(
            StrategyDebateRequest(
                market_phase=request.market_phase,
                active_loop=request.active_loop,
                regime=request.regime,
                horizon=request.horizon,
                account_equity=request.account_equity,
                buying_power=request.buying_power,
                strategy_keys=request.strategy_keys,
            )
        )

    if not debate or not debate.strategy_arguments:
        return StrategyRankingResponse(
            run_id=run_id,
            status="failed",
            debate_run_id=debate.run_id if debate else None,
            market_phase=request.market_phase,
            active_loop=request.active_loop,
            regime=request.regime,
            horizon=request.horizon,
            ranked_strategies=[],
            active_strategies=[],
            disabled_strategies=[],
            top_strategy_key=None,
            blockers=["No strategy arguments available from debate"],
            warnings=[],
            created_at=created_at,
        )

    # Rank each strategy
    ranked: list[RankedStrategy] = []
    active_keys: list[str] = []
    disabled_keys: list[str] = []
    all_warnings: list[str] = []

    for arg in debate.strategy_arguments:
        strategy = get_strategy(arg.strategy_key)
        if not strategy:
            continue

        # Start with debate fit_score
        base_score = arg.fit_score

        # Apply adjustments
        score = _adjust_score_for_market_phase(base_score, request.market_phase, strategy)
        score = _adjust_score_for_regime(score, request.regime, strategy)
        score = _adjust_score_for_data_availability(score, strategy, request.source)
        score = _adjust_score_for_account_constraints(score, strategy, request.account_equity, request.buying_power)

        # Cap at 0-100
        score = max(0.0, min(100.0, score))

        # Determine status
        status, blockers, warnings = _determine_strategy_status(score, arg.allowed, arg.disable_reason)

        # Build ranked strategy
        ranked_strategy = RankedStrategy(
            strategy_key=arg.strategy_key,
            strategy_family=arg.strategy_family,
            rank=0,  # Will be set after sorting
            strategy_score=score,
            status=status,
            model_stack_hint=_calculate_model_stack_hint(strategy, score),
            scanner_needs=strategy.edge_signals,
            data_needs=strategy.required_data_sources,
            reason=arg.bull_case if score >= 50 else arg.bear_case,
            blockers=blockers,
            warnings=warnings,
        )

        ranked.append(ranked_strategy)

        if status == "active":
            active_keys.append(arg.strategy_key)
        elif status == "disabled":
            disabled_keys.append(arg.strategy_key)

        all_warnings.extend(warnings)

    # Sort by score descending
    ranked.sort(key=lambda x: x.strategy_score, reverse=True)

    # Assign ranks
    for i, r in enumerate(ranked):
        r.rank = i + 1

    # Determine top strategy
    top_strategy = ranked[0].strategy_key if ranked else None

    # Deduplicate warnings
    all_warnings = list(set(all_warnings))

    response = StrategyRankingResponse(
        run_id=run_id,
        status="completed" if ranked else "failed",
        debate_run_id=debate.run_id,
        market_phase=request.market_phase,
        active_loop=request.active_loop,
        regime=request.regime,
        horizon=request.horizon,
        ranked_strategies=ranked,
        active_strategies=active_keys,
        disabled_strategies=disabled_keys,
        top_strategy_key=top_strategy,
        warnings=all_warnings,
        blockers=[],
        created_at=created_at,
    )

    _LATEST_RANKING = response
    _RANKING_HISTORY.append(response)

    # Keep only last 100
    if len(_RANKING_HISTORY) > 100:
        _RANKING_HISTORY = _RANKING_HISTORY[-100:]

    return response


def get_latest_strategy_ranking() -> StrategyRankingResponse | None:
    """Get the most recent strategy ranking."""
    return _LATEST_RANKING


def list_strategy_ranking_history(limit: int = 20) -> list[StrategyRankingResponse]:
    """List recent strategy rankings."""
    return _RANKING_HISTORY[-limit:]


def get_top_strategy_from_ranking() -> str | None:
    """Get top strategy key from latest ranking."""
    if not _LATEST_RANKING:
        return None
    return _LATEST_RANKING.top_strategy_key


def get_active_strategies_from_ranking() -> list[str]:
    """Get list of active strategy keys from latest ranking."""
    if not _LATEST_RANKING:
        return []
    return _LATEST_RANKING.active_strategies
