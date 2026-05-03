from fastapi import APIRouter

from app.services.timing_cadence_service import CadenceSimulationRequest, build_cadence_plan, detect_market_phase, simulate_cadence_plan

router = APIRouter()


@router.get('/runtime/phase')
def get_runtime_phase():
    return detect_market_phase()


@router.get('/runtime/cadence')
def get_runtime_cadence():
    return build_cadence_plan()


@router.post('/runtime/cadence/simulate')
def simulate_runtime_cadence(request: CadenceSimulationRequest):
    return simulate_cadence_plan(request)
