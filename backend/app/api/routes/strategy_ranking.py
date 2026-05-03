"""Strategy Ranking API Routes."""

from fastapi import APIRouter

from app.services.strategy_ranking_service import (
    StrategyRankingRequest,
    StrategyRankingResponse,
    get_active_strategies_from_ranking,
    get_latest_strategy_ranking,
    get_top_strategy_from_ranking,
    list_strategy_ranking_history,
    run_strategy_ranking,
)

router = APIRouter()


@router.post("/strategy-ranking/run", response_model=StrategyRankingResponse)
def post_strategy_ranking_run(request: StrategyRankingRequest):
    """Run strategy ranking after debate.

    Numerically ranks strategies based on debate fit_score + adjustments.
    Returns active/conditional/disabled status per strategy.
    """
    return run_strategy_ranking(request)


@router.get("/strategy-ranking/latest", response_model=StrategyRankingResponse | dict)
def get_latest_strategy_ranking_endpoint():
    """Get the most recent strategy ranking."""
    latest = get_latest_strategy_ranking()
    if not latest:
        return {"message": "No strategy ranking available", "status": "not_found"}
    return latest


@router.get("/strategy-ranking/active")
def get_active_strategies():
    """Get list of currently active strategies."""
    return {
        "active_strategies": get_active_strategies_from_ranking(),
        "top_strategy": get_top_strategy_from_ranking(),
    }
