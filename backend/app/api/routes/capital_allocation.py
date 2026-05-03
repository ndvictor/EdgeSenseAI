"""Capital Allocation API routes."""

from fastapi import APIRouter

from app.services.capital_allocation_service import (
    CapitalAllocationRequest,
    CapitalAllocationResponse,
    create_capital_allocation_plan,
    get_latest_capital_allocation,
)

router = APIRouter()


@router.post("/capital-allocation/plan", response_model=CapitalAllocationResponse)
def post_capital_allocation_plan(request: CapitalAllocationRequest):
    """Create a capital allocation and trade plan.

    Deterministic calculations only. Must meet 3R reward/risk.
    No live execution.
    """
    return create_capital_allocation_plan(request)


@router.get("/capital-allocation/latest", response_model=CapitalAllocationResponse | dict)
def get_capital_allocation_latest():
    """Get the latest capital allocation plan."""
    result = get_latest_capital_allocation()
    if result is None:
        return {"status": "not_found", "message": "No capital allocation plan found"}
    return result
