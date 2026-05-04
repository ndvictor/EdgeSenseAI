"""Strategy Ranking Model Service.

Implements Step 6 of the Adaptive Agentic Quant Workflow:
- Numerically rank strategies after debate
- Deterministic scoring based on debate fit_score + adjustments
- Returns active/conditional/disabled status per strategy
- Separates production-approved strategies from research candidates
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.strategy_debate_service import (
    StrategyArgument,
    StrategyDebateRequest,
    StrategyDebateResponse,
    get_latest_strategy_debate,
    run_strategy_debate,
)
from app.strategies.registry import StrategyConfig, get_strategy


class RankedStrategy(BaseModel):
    """A ranked strategy with full metadata."""

    model_config = ConfigDict(protected_namespaces=())

    strategy_key: str
    strategy_family: str
    rank: int = 0
    strategy_score: float = Field(default=50.0, ge=0.0, le=100.0)
    status: Literal["active", "conditional", "disabled", "research_candidate"] = "conditional"
    model_stack_hint: list[str] = Field(default_factory=list)
    scanner_needs: list[str] = Field(default_factory=list)
    data_needs: list[str] = Field(default_factory=list)
    reason: str = ""
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    research_candidate: bool = False
    production_approved: bool = True


class StrategyRankingRequest(BaseModel):
    """Request to run strategy ranking."""

    model_config = ConfigDict(protected_namespaces=())

    debate_run_id: str | None = None
    market_phase: str
    active_loop: str
    regime: str
    horizon: Literal["day_trade", "swing", "one_month"]
    account_equity: float | None = None
    buying_power: float | None = None
    strategy_keys: list[str] | None = None
    source: str | None = None
    research_mode: bool = False


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
    recommended_active_strategy_keys: list[str] = Field(default_factory=list)
    recommended_research_candidate_keys: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    created_at: str


_LATEST_RANKING: StrategyRankingResponse | None = None
_RANKING_HISTORY: list[StrategyRankingResponse] = []


def _is_research_candidate(strategy: StrategyConfig, argument: StrategyArgument | None = None) -> bool:
    if argument is not None and getattr(argument, "research_candidate", False):
        return True
    return (
        strategy.status == "candidate"
        or strategy.promotion_status == "candidate"
        or strategy.paper_research_only
        or strategy.requires_backtest
        or strategy.requires_owner_approval_for_promotion
    )


def _is_production_approved(strategy: StrategyConfig) -> bool:
    return (
        strategy.status in {"active", "approved"}
        and strategy.promotion_status == "active"
        and not strategy.paper_research_only
        and not strategy.disabled_reason
    )


def _normalize_service_result(result: Any) -> Any:
    """Unwrap accidental tuple returns from service/helper functions.

    The canonical service contract is a response object. This is defensive so a
    tuple-shaped result cannot break upper workflow with missing `.run_id`.
    """
    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, (StrategyDebateResponse, StrategyRankingResponse)):
                return item
        return result[0] if result else None
    return result


def _strategy_family(strategy: StrategyConfig) -> str:
    return f"{strategy.asset_class}_{strategy.timeframe}"


def _adjust_score_for_market_phase(base_score: float, market_phase: str, strategy: StrategyConfig) -> float:
    adjustments = {
        "market_open_first_30_min": {"stock_day_trade": 10, "crypto_intraday": 10, "stock_swing": -5},
        "pre_market": {"stock_day_trade": 5, "stock_swing": 5, "option_day_trade": -10},
        "market_open": {"stock_swing": 5, "crypto_swing": 5},
        "midday": {"stock_day_trade": -10, "crypto_intraday": -5},
        "power_hour": {"stock_day_trade": 8, "crypto_intraday": 5, "stock_one_month": -5},
        "after_hours": {"stock_swing": -5, "stock_day_trade": -15, "option_swing": -10},
        "market_closed": {"stock_swing": 0, "stock_one_month": 5},
    }
    return base_score + adjustments.get(market_phase, {}).get(_strategy_family(strategy), 0)


def _adjust_score_for_regime(base_score: float, regime: str, strategy: StrategyConfig) -> float:
    adjustments = {
        "risk_on": {"stock_swing": 15, "crypto_swing": 15, "stock_day_trade": 10, "option_earnings": -10},
        "risk_off": {"stock_swing": 10, "stock_one_month": 5, "crypto_swing": -20, "crypto_intraday": -15},
        "chop": {"stock_swing": -5, "stock_day_trade": -5, "crypto_swing": -10},
        "momentum": {"stock_swing": 15, "crypto_swing": 15, "stock_day_trade": 10, "option_swing": 5},
        "mean_reversion": {"stock_day_trade": 10, "crypto_intraday": 10, "stock_swing": -5},
        "volatility_expansion": {"stock_swing": -10, "stock_day_trade": -20, "option_swing": -10, "crypto_intraday": -10},
        "unknown": {},
    }
    return base_score + adjustments.get(regime, {}).get(_strategy_family(strategy), 0)


def _adjust_score_for_data_availability(base_score: float, strategy: StrategyConfig, source: str | None) -> float:
    if strategy.asset_class == "option":
        return base_score - 5
    return base_score


def _adjust_score_for_account_constraints(base_score: float, strategy: StrategyConfig, account_equity: float | None, buying_power: float | None) -> float:
    score = base_score
    if account_equity is not None and account_equity < 25000 and strategy.timeframe == "day_trade":
        score -= 10
    if buying_power is not None and buying_power < 5000 and strategy.asset_class == "option":
        score -= 5
    return score


def _calculate_model_stack_hint(strategy: StrategyConfig, score: float) -> list[str]:
    stack = ["weighted_ranker_v1"]
    if score >= 70:
        if "xgboost_ranker" in strategy.required_models or "xgboost_ranker" in strategy.optional_models:
            stack.append("xgboost_ranker_not_trained")
        if "hmm_regime" in strategy.optional_models:
            stack.append("hmm_regime")
    if score >= 60 and "historical_similarity" in strategy.optional_models:
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
    research_candidate: bool,
    production_approved: bool,
    research_mode: bool,
) -> tuple[str, list[str], list[str]]:
    if not allowed:
        return "disabled", [disable_reason or "Strategy disabled"], []
    if research_candidate and not research_mode:
        return "research_candidate", [], ["Research candidate only; not eligible for active production recommendation."]
    if not production_approved and not research_mode:
        return "disabled", ["Strategy is not production-approved."], []
    if score >= 70:
        return "active", [], []
    if score >= 50:
        return "conditional", [], [f"Score {score:.1f} is moderate - use with caution"]
    if score >= 30:
        return "conditional", [], [f"Low score {score:.1f} - review carefully"]
    return "conditional", [], [f"Very low score {score:.1f} - consider avoiding"]


def _resolve_debate(request: StrategyRankingRequest) -> StrategyDebateResponse | None:
    latest = _normalize_service_result(get_latest_strategy_debate())
    if isinstance(latest, StrategyDebateResponse):
        if request.debate_run_id is None or latest.run_id == request.debate_run_id:
            return latest

    return _normalize_service_result(run_strategy_debate(
        StrategyDebateRequest(
            market_phase=request.market_phase,
            active_loop=request.active_loop,
            regime=request.regime,
            horizon=request.horizon,
            account_equity=request.account_equity,
            buying_power=request.buying_power,
            strategy_keys=request.strategy_keys,
            research_mode=request.research_mode,
        )
    ))


def run_strategy_ranking(request: StrategyRankingRequest) -> StrategyRankingResponse:
    """Run strategy ranking based on debate results and additional factors."""
    global _LATEST_RANKING

    run_id = f"rank-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    debate = _resolve_debate(request)

    if not isinstance(debate, StrategyDebateResponse) or not debate.strategy_arguments:
        response = StrategyRankingResponse(
            run_id=run_id,
            status="failed",
            debate_run_id=getattr(debate, "run_id", None),
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
        _LATEST_RANKING = response
        _RANKING_HISTORY.append(response)
        return response

    ranked: list[RankedStrategy] = []
    active_keys: list[str] = []
    disabled_keys: list[str] = []
    research_keys: list[str] = []
    all_warnings: list[str] = []

    for arg in debate.strategy_arguments:
        strategy = get_strategy(arg.strategy_key)
        if not strategy:
            continue

        score = _adjust_score_for_market_phase(arg.fit_score, request.market_phase, strategy)
        score = _adjust_score_for_regime(score, request.regime, strategy)
        score = _adjust_score_for_data_availability(score, strategy, request.source)
        score = _adjust_score_for_account_constraints(score, strategy, request.account_equity, request.buying_power)
        score = max(0.0, min(100.0, score))

        research_candidate = _is_research_candidate(strategy, arg)
        production_approved = _is_production_approved(strategy)
        status, blockers, warnings = _determine_strategy_status(
            score=score,
            allowed=arg.allowed,
            disable_reason=arg.disable_reason,
            research_candidate=research_candidate,
            production_approved=production_approved,
            research_mode=request.research_mode,
        )

        ranked_strategy = RankedStrategy(
            strategy_key=arg.strategy_key,
            strategy_family=arg.strategy_family,
            strategy_score=score,
            status=status,
            model_stack_hint=_calculate_model_stack_hint(strategy, score),
            scanner_needs=strategy.edge_signals,
            data_needs=strategy.required_data_sources,
            reason=arg.bull_case if score >= 50 else arg.bear_case,
            blockers=blockers,
            warnings=warnings,
            research_candidate=research_candidate,
            production_approved=production_approved,
        )
        ranked.append(ranked_strategy)

        if status == "active" and production_approved and not research_candidate:
            active_keys.append(arg.strategy_key)
        elif status == "disabled":
            disabled_keys.append(arg.strategy_key)
        elif research_candidate:
            research_keys.append(arg.strategy_key)

        all_warnings.extend(warnings)

    ranked.sort(key=lambda x: x.strategy_score, reverse=True)
    for index, item in enumerate(ranked):
        item.rank = index + 1

    active_ranked = [item for item in ranked if item.status == "active" and item.production_approved and not item.research_candidate]
    top_strategy = active_ranked[0].strategy_key if active_ranked else None

    if not top_strategy and research_keys:
        all_warnings.append("Only research candidate strategies available; no active strategy selected.")

    all_warnings = sorted(set(all_warnings))
    response = StrategyRankingResponse(
        run_id=run_id,
        status="completed" if ranked and top_strategy else "partial" if ranked else "failed",
        debate_run_id=debate.run_id,
        market_phase=request.market_phase,
        active_loop=request.active_loop,
        regime=request.regime,
        horizon=request.horizon,
        ranked_strategies=ranked,
        active_strategies=active_keys,
        disabled_strategies=disabled_keys,
        top_strategy_key=top_strategy,
        recommended_active_strategy_keys=active_keys,
        recommended_research_candidate_keys=sorted(set(research_keys)),
        warnings=all_warnings,
        blockers=[] if ranked else ["No strategies ranked"],
        created_at=created_at,
    )

    _LATEST_RANKING = response
    _RANKING_HISTORY.append(response)
    if len(_RANKING_HISTORY) > 100:
        del _RANKING_HISTORY[:-100]
    return response


def get_latest_strategy_ranking() -> StrategyRankingResponse | None:
    """Get the most recent strategy ranking."""
    return _LATEST_RANKING


def list_strategy_ranking_history(limit: int = 20) -> list[StrategyRankingResponse]:
    """List recent strategy rankings."""
    return _RANKING_HISTORY[-limit:]


def get_top_strategy_from_ranking() -> str | None:
    """Get top active production strategy key from latest ranking."""
    if not _LATEST_RANKING:
        return None
    return _LATEST_RANKING.top_strategy_key


def get_active_strategies_from_ranking() -> list[str]:
    """Get list of active production strategy keys from latest ranking."""
    if not _LATEST_RANKING:
        return []
    return _LATEST_RANKING.active_strategies
