"""LLM Budget Gate API routes."""

from fastapi import APIRouter

from app.services.llm_budget_gate_service import (
    LLMBudgetGateRequest,
    LLMBudgetGateResponse,
    evaluate_llm_budget_gate,
    get_latest_llm_budget_gate,
)

router = APIRouter()


@router.post("/llm-budget-gate/evaluate", response_model=LLMBudgetGateResponse)
def post_llm_budget_gate_evaluate(request: LLMBudgetGateRequest):
    """Evaluate whether LLM validation is worth the cost.

    Always defaults to safe mode (no paid calls).
    """
    return evaluate_llm_budget_gate(request)


@router.get("/llm-budget-gate/latest", response_model=LLMBudgetGateResponse | dict)
def get_llm_budget_gate_latest():
    """Get the latest LLM budget gate evaluation."""
    result = get_latest_llm_budget_gate()
    if result is None:
        return {"status": "not_found", "message": "No LLM budget gate evaluation found"}
    return result
