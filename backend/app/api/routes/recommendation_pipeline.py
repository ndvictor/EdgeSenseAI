"""Recommendation Pipeline API routes."""

from fastapi import APIRouter

from app.services.recommendation_pipeline_service import (
    RecommendationPipelineRequest,
    RecommendationPipelineResponse,
    get_latest_recommendation_pipeline,
    run_recommendation_pipeline,
)

router = APIRouter()


@router.post("/recommendation-pipeline/run", response_model=RecommendationPipelineResponse)
def post_recommendation_pipeline_run(request: RecommendationPipelineRequest):
    """Run the full recommendation pipeline.

    Orchestrates: LLM Budget Gate -> Agent Validation -> Risk Review ->
    No-Trade -> Capital Allocation -> Recommendation.

    No paid LLM calls.
    No live execution.
    Human approval required.
    """
    return run_recommendation_pipeline(request)


@router.get("/recommendation-pipeline/latest", response_model=RecommendationPipelineResponse | dict)
def get_recommendation_pipeline_latest():
    """Get the latest recommendation pipeline run."""
    result = get_latest_recommendation_pipeline()
    if result is None:
        return {"status": "not_found", "message": "No recommendation pipeline run found"}
    return result
