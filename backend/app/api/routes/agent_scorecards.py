from fastapi import APIRouter

from app.services.platform_workflows import AgentScorecard, get_agent_scorecards

router = APIRouter()


@router.get("/agents/scorecards", response_model=list[AgentScorecard])
def get_scorecards():
    return get_agent_scorecards()
