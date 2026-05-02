from fastapi import APIRouter

from app.orchestration.workflows.small_account_edge_radar import (
    SmallAccountEdgeRadarInput,
    SmallAccountEdgeRadarOutput,
    run_small_account_edge_radar,
)

router = APIRouter()


@router.post("/agents/edge-radar/run", response_model=SmallAccountEdgeRadarOutput)
def post_edge_radar_run(request: SmallAccountEdgeRadarInput):
    return run_small_account_edge_radar(request)
