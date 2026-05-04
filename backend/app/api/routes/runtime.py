"""Runtime API Routes - Timing & Cadence endpoints.

Implements Phase 1 of the Adaptive Agentic Quant Workflow.
"""

from fastapi import APIRouter

from app.services.runtime_speed_policy_service import RuntimeSpeedPolicyResponse, get_runtime_speed_policy
from app.services.timing_cadence_service import (
    RuntimeCadenceResponse,
    RuntimeCadenceSimulateRequest,
    RuntimePhaseResponse,
    get_runtime_cadence,
    get_runtime_phase,
    simulate_cadence_for_time,
)

router = APIRouter()


@router.get("/runtime/phase", response_model=RuntimePhaseResponse)
def get_current_runtime_phase():
    """Get current market phase and timing information.

    Returns deterministic market phase detection based on current US Eastern time.
    """
    return get_runtime_phase()


@router.get("/runtime/cadence", response_model=RuntimeCadenceResponse)
def get_current_runtime_cadence():
    """Get current operational cadence plan.

    Returns the active loop and cadence parameters for the current market phase.
    live_trading_allowed is always false.
    human_approval_required is always true.
    """
    return get_runtime_cadence()


@router.get("/runtime/speed-policy", response_model=RuntimeSpeedPolicyResponse)
def get_speed_policy():
    """Get hot/warm/cold runtime speed policy for operational loops."""
    return get_runtime_speed_policy()


@router.post("/runtime/cadence/simulate", response_model=RuntimeCadenceResponse)
def simulate_cadence(request: RuntimeCadenceSimulateRequest):
    """Simulate cadence plan for a specific time (for testing/backtesting).

    Allows testing different market phases without waiting for the actual time.
    """
    return simulate_cadence_for_time(request)
