"""Meta-Model Ensemble API Routes."""

from fastapi import APIRouter

from app.services.meta_model_ensemble_service import (
    MetaModelEnsembleRequest,
    MetaModelEnsembleResponse,
    get_latest_meta_model_ensemble,
    list_meta_model_ensemble_runs,
    promote_passing_signals_to_candidates,
    run_meta_model_ensemble,
)

router = APIRouter()


@router.post("/meta-model/ensemble/run", response_model=MetaModelEnsembleResponse)
def post_meta_model_ensemble_run(request: MetaModelEnsembleRequest):
    """Run meta-model ensemble on scored signals.

    Combines model scores into final signal confidence.
    Pre-recommendation only - no trade decisions.

    NO LLM. NO recommendation.
    """
    return run_meta_model_ensemble(request)


@router.get("/meta-model/ensemble/latest", response_model=MetaModelEnsembleResponse | dict)
def get_latest_meta_model_ensemble_endpoint():
    """Get the most recent meta-model ensemble run."""
    latest = get_latest_meta_model_ensemble()
    if not latest:
        return {"message": "No meta-model ensemble run available", "status": "not_found"}
    return latest


@router.get("/meta-model/ensemble/runs")
def get_meta_model_ensemble_runs(limit: int = 20):
    """List recent meta-model ensemble runs."""
    runs = list_meta_model_ensemble_runs(limit)
    return {
        "runs": runs,
        "count": len(runs),
    }


@router.post("/meta-model/ensemble/promote-passing-to-candidates")
def post_promote_passing_to_candidates(
    include_watch: bool = False,
    min_score: int = 60,
):
    """Promote passing signals from latest ensemble to candidate universe.

    - Pass status signals always promoted
    - Watch status signals promoted only if include_watch=true
    - Must meet min_score threshold
    """
    result = promote_passing_signals_to_candidates(
        include_watch=include_watch,
        min_score=min_score,
    )
    return result
