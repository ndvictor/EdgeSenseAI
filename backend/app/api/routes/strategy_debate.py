"""Strategy Debate API Routes."""

from fastapi import APIRouter

from app.services.strategy_debate_service import (
    StrategyDebateRequest,
    StrategyDebateResponse,
    get_latest_strategy_debate,
    list_strategy_debate_history,
    run_strategy_debate,
)

router = APIRouter()


@router.post("/strategy-debate/run", response_model=StrategyDebateResponse)
def post_strategy_debate_run(request: StrategyDebateRequest):
    """Run strategy debate based on current conditions.

    Compares strategy families under market phase/regime/constraints.
    NO LLM calls - deterministic debate only.
    Returns bull/bear cases, fit scores, allowed/disabled status.
    """
    return run_strategy_debate(request)


@router.get("/strategy-debate/latest", response_model=StrategyDebateResponse | dict)
def get_latest_strategy_debate_endpoint():
    """Get the most recent strategy debate."""
    latest = get_latest_strategy_debate()
    if not latest:
        return {"message": "No strategy debate available", "status": "not_found"}
    return latest
