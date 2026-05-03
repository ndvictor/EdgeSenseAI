"""Strategy Debate Agent Service.

Implements Step 5 of the Adaptive Agentic Quant Workflow:
- Compare strategy families under current market phase/regime/account constraints
- NO LLM calls - deterministic debate/argument builder
- Returns bull/bear cases, fit scores, allowed/disabled status per strategy
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.strategies.registry import StrategyConfig, get_strategy, list_strategies


class StrategyArgument(BaseModel):
    """Argument for a single strategy."""

    model_config = ConfigDict(protected_namespaces=())

    strategy_key: str
    strategy_family: str
    bull_case: str
    bear_case: str
    fit_score: float = Field(default=50.0, ge=0.0, le=100.0)
    allowed: bool = True
    disable_reason: str | None = None
    required_data_sources: list[str] = Field(default_factory=list)
    model_needs: list[str] = Field(default_factory=list)


class StrategyDebateRequest(BaseModel):
    """Request to run strategy debate."""

    model_config = ConfigDict(protected_namespaces=())

    market_phase: str
    active_loop: str
    regime: str
    horizon: Literal["day_trade", "swing", "one_month"]
    account_equity: float | None = None
    buying_power: float | None = None
    max_risk_per_trade_percent: float | None = None
    strategy_keys: list[str] | None = None  # If None, debate all strategies
    allow_llm: bool = False  # Default false - no LLM debate yet


class StrategyDebateResponse(BaseModel):
    """Response from strategy debate."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "failed"]
    market_phase: str
    active_loop: str
    regime: str
    horizon: str
    strategy_arguments: list[StrategyArgument]
    recommended_strategy_keys: list[str]
    disabled_strategy_keys: list[str]
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    created_at: str


# In-memory storage
_LATEST_DEBATE: StrategyDebateResponse | None = None
_DEBATE_HISTORY: list[StrategyDebateResponse] = []


def _get_strategy_family(strategy: StrategyConfig) -> str:
    """Determine strategy family from strategy config."""
    if strategy.asset_class == "stock":
        return f"stock_{strategy.timeframe}"
    elif strategy.asset_class == "option":
        return f"option_{strategy.timeframe}"
    elif strategy.asset_class == "crypto":
        return f"crypto_{strategy.timeframe}"
    return "unknown"


def _build_bull_case(strategy: StrategyConfig, regime: str, market_phase: str, horizon: str) -> str:
    """Build bull case for a strategy based on conditions."""
    cases = []

    # Regime-based cases
    if regime == "risk_on":
        if strategy.asset_class == "stock":
            cases.append("Risk-on regime favors equity momentum")
        if strategy.timeframe == "swing":
            cases.append("Swing strategies benefit from sustained trends in risk-on")
    elif regime == "momentum":
        if "breakout" in strategy.edge_signals:
            cases.append("Breakout signals perform well in momentum regimes")
        if "momentum" in strategy.strategy_key:
            cases.append("Momentum strategies aligned with regime")
    elif regime == "mean_reversion":
        if "mean_reversion" in strategy.edge_signals:
            cases.append("Mean reversion signals active in sideways markets")

    # Market phase cases
    if market_phase == "market_open_first_30_min" and strategy.timeframe == "day_trade":
        cases.append("Opening volatility provides day trading opportunities")
    elif market_phase == "power_hour" and strategy.timeframe == "day_trade":
        cases.append("Power hour volume supports intraday setups")
    elif market_phase == "pre_market" and strategy.timeframe == "day_trade":
        cases.append("Pre-market planning allows early entry identification")

    # Horizon alignment
    if strategy.timeframe == horizon:
        cases.append(f"Strategy timeframe ({strategy.timeframe}) matches requested horizon ({horizon})")

    # Asset class specific
    if strategy.asset_class == "option" and "volatility" in strategy.required_agents:
        cases.append("Options strategies benefit from volatility awareness")

    if not cases:
        return "Strategy available but no strong alignment with current conditions"

    return "; ".join(cases)


def _build_bear_case(strategy: StrategyConfig, regime: str, market_phase: str, horizon: str) -> str:
    """Build bear case for a strategy based on conditions."""
    cases = []

    # Regime-based risks
    if regime == "risk_off":
        if strategy.auto_run_supported:
            cases.append("Risk-off regime reduces auto-run reliability")
        if strategy.asset_class == "crypto":
            cases.append("Crypto faces headwinds in risk-off environments")
    elif regime == "volatility_expansion":
        if strategy.timeframe == "day_trade":
            cases.append("High volatility increases intraday risk")
        if strategy.live_trading_supported:
            cases.append("Live trading particularly risky in extreme volatility")
    elif regime == "chop":
        if "trend" in strategy.strategy_key or "breakout" in strategy.strategy_key:
            cases.append("Choppy markets frustrate trend/breakout strategies")

    # Market phase risks
    if market_phase == "after_hours" and strategy.timeframe == "day_trade":
        cases.append("After-hours liquidity limits day trading effectiveness")
    elif market_phase == "midday" and strategy.timeframe == "day_trade":
        cases.append("Midday typically lower volume/volatility for intraday")

    # Horizon mismatch
    if strategy.timeframe != horizon:
        cases.append(f"Horizon mismatch: strategy={strategy.timeframe}, requested={horizon}")

    # Asset class specific risks
    if strategy.asset_class == "option":
        cases.append("Options require precise timing and spread management")
    if strategy.asset_class == "crypto":
        cases.append("Crypto carries elevated volatility and gap risk")

    if not cases:
        return "No major concerns, normal market risks apply"

    return "; ".join(cases)


def _calculate_fit_score(
    strategy: StrategyConfig,
    regime: str,
    market_phase: str,
    horizon: str,
    active_loop: str,
) -> float:
    """Calculate strategy fit score (0-100)."""
    score = 50.0  # Neutral starting point

    # Horizon alignment (+15 if match, -10 if mismatch)
    if strategy.timeframe == horizon:
        score += 15
    else:
        score -= 10

    # Regime fit
    regime_scores = {
        "risk_on": {"stock_swing": 20, "stock_day_trading": 15, "crypto_swing": 15, "options_swing": 10},
        "risk_off": {"stock_swing": 10, "stock_one_month": 5, "crypto_swing": -20},
        "chop": {"stock_swing": 0, "stock_day_trading": -5, "crypto_intraday": -10},
        "momentum": {"stock_swing": 15, "crypto_swing": 15, "options_swing": 10},
        "mean_reversion": {"stock_day_trading": 10, "crypto_intraday": 10},
        "volatility_expansion": {"stock_swing": -10, "stock_day_trading": -20, "options_swing": -10},
        "unknown": {},
    }
    strategy_family = _get_strategy_family(strategy)
    score += regime_scores.get(regime, {}).get(strategy_family, 0)

    # Market phase fit
    if market_phase == "market_open_first_30_min" and strategy.timeframe == "day_trade":
        score += 10
    elif market_phase == "pre_market" and strategy.timeframe in ["day_trade", "swing"]:
        score += 5
    elif market_phase == "midday" and strategy.timeframe == "day_trade":
        score -= 10
    elif market_phase == "after_hours":
        score -= 15  # Reduced opportunity set

    # Active loop alignment
    loop_scores = {
        "fast_scanning_loop": {"stock_day_trading": 10, "crypto_intraday": 10},
        "research_backtesting_loop": {"stock_swing": 5, "stock_one_month": 5, "crypto_cycle": 5},
        "reduced_cadence_pruning_loop": {"stock_swing": 0, "stock_day_trading": -10},
    }
    score += loop_scores.get(active_loop, {}).get(strategy_family, 0)

    # Auto-run bonus (if supported and conditions permit)
    if strategy.auto_run_supported and regime not in ["risk_off", "volatility_expansion"]:
        score += 5

    # Cap at 0-100
    return max(0.0, min(100.0, score))


def _is_strategy_allowed(
    strategy: StrategyConfig,
    regime: str,
    market_phase: str,
    fit_score: float,
) -> tuple[bool, str | None]:
    """Determine if strategy is allowed and reason if not."""
    # Always block in extreme volatility for most strategies
    if regime == "volatility_expansion":
        if strategy.timeframe == "day_trade" and strategy.asset_class != "crypto":
            return False, "Day trading blocked in volatility expansion"

    # Block options if insufficient data (simplified check)
    if strategy.asset_class == "option":
        # In real implementation, check if options data provider configured
        pass  # Allow for now, gate at data level

    # Block if fit score extremely low
    if fit_score < 20:
        return False, f"Fit score too low ({fit_score:.1f}) for current conditions"

    # Block auto-run strategies in risk-off unless explicitly supported
    if regime == "risk_off" and strategy.auto_run_supported and strategy.timeframe == "day_trade":
        return False, "Auto day trading blocked in risk-off regime"

    return True, None


def run_strategy_debate(request: StrategyDebateRequest) -> StrategyDebateResponse:
    """Run strategy debate based on current conditions."""
    global _LATEST_DEBATE

    run_id = f"debate-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    # Get strategies to debate
    if request.strategy_keys:
        strategies = []
        for key in request.strategy_keys:
            strategy = get_strategy(key)
            if strategy:
                strategies.append(strategy)
    else:
        strategies = list_strategies()

    if not strategies:
        return StrategyDebateResponse(
            run_id=run_id,
            status="failed",
            market_phase=request.market_phase,
            active_loop=request.active_loop,
            regime=request.regime,
            horizon=request.horizon,
            strategy_arguments=[],
            recommended_strategy_keys=[],
            disabled_strategy_keys=[],
            blockers=["No strategies available for debate"],
            warnings=[],
            created_at=created_at,
        )

    # Build arguments for each strategy
    arguments: list[StrategyArgument] = []
    recommended: list[str] = []
    disabled: list[str] = []
    warnings: list[str] = []

    for strategy in strategies:
        fit_score = _calculate_fit_score(
            strategy=strategy,
            regime=request.regime,
            market_phase=request.market_phase,
            horizon=request.horizon,
            active_loop=request.active_loop,
        )

        allowed, disable_reason = _is_strategy_allowed(
            strategy=strategy,
            regime=request.regime,
            market_phase=request.market_phase,
            fit_score=fit_score,
        )

        argument = StrategyArgument(
            strategy_key=strategy.strategy_key,
            strategy_family=_get_strategy_family(strategy),
            bull_case=_build_bull_case(strategy, request.regime, request.market_phase, request.horizon),
            bear_case=_build_bear_case(strategy, request.regime, request.market_phase, request.horizon),
            fit_score=fit_score,
            allowed=allowed,
            disable_reason=disable_reason,
            required_data_sources=strategy.required_data_sources,
            model_needs=strategy.required_models + strategy.optional_models,
        )

        arguments.append(argument)

        if allowed and fit_score >= 50:
            recommended.append(strategy.strategy_key)
        elif not allowed:
            disabled.append(strategy.strategy_key)

    # Warn if no recommended strategies
    if not recommended:
        warnings.append("No strategies recommended for current conditions - review manually")

    # Warn about LLM budget
    if request.allow_llm:
        warnings.append("LLM debate not implemented - using deterministic debate only")

    response = StrategyDebateResponse(
        run_id=run_id,
        status="completed" if arguments else "failed",
        market_phase=request.market_phase,
        active_loop=request.active_loop,
        regime=request.regime,
        horizon=request.horizon,
        strategy_arguments=arguments,
        recommended_strategy_keys=recommended,
        disabled_strategy_keys=disabled,
        warnings=warnings,
        blockers=[],
        created_at=created_at,
    )

    _LATEST_DEBATE = response
    _DEBATE_HISTORY.append(response)

    # Keep only last 100
    if len(_DEBATE_HISTORY) > 100:
        _DEBATE_HISTORY = _DEBATE_HISTORY[-100:]

    return response


def get_latest_strategy_debate() -> StrategyDebateResponse | None:
    """Get the most recent strategy debate."""
    return _LATEST_DEBATE


def list_strategy_debate_history(limit: int = 20) -> list[StrategyDebateResponse]:
    """List recent strategy debates."""
    return _DEBATE_HISTORY[-limit:]


def get_recommended_strategies_from_latest() -> list[str]:
    """Get recommended strategy keys from latest debate."""
    if not _LATEST_DEBATE:
        return []
    return _LATEST_DEBATE.recommended_strategy_keys


def get_top_strategy_from_latest() -> str | None:
    """Get top recommended strategy from latest debate."""
    if not _LATEST_DEBATE or not _LATEST_DEBATE.strategy_arguments:
        return None

    # Find highest fit score that is allowed
    best = None
    best_score = -1
    for arg in _LATEST_DEBATE.strategy_arguments:
        if arg.allowed and arg.fit_score > best_score:
            best = arg
            best_score = arg.fit_score

    return best.strategy_key if best else None
