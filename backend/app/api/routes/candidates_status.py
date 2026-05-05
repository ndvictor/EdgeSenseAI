from fastapi import APIRouter

from app.services.candidates_status_service import CandidatesStatusResponse, build_candidates_status

router = APIRouter()


@router.get("/candidates/status", response_model=CandidatesStatusResponse)
def get_candidates_status() -> CandidatesStatusResponse:
    return build_candidates_status()

