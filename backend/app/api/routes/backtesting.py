from __future__ import annotations

from fastapi import APIRouter

from app.backtesting.backtest_service import build_not_configured_backtest_run
from app.backtesting.execution_simulator import build_not_configured_execution_response
from app.backtesting.promotion_gate import build_not_configured_promotion
from app.backtesting.risk_validator import build_not_configured_risk_validation
from app.backtesting.schemas import (
    BacktestProfileActionBody,
    BacktestRunResponse,
    ExecutionSimulationResponse,
    PromoteToPaperResponse,
    RiskValidationResponse,
)
from app.services.backtesting_service import BacktestingResponse, build_backtesting_summary

router = APIRouter(prefix="/backtesting", tags=["backtesting"])


@router.get("/summary", response_model=BacktestingResponse)
def get_backtesting_summary() -> BacktestingResponse:
    return build_backtesting_summary()


@router.post("/run", response_model=BacktestRunResponse)
def post_backtesting_run(body: BacktestProfileActionBody) -> BacktestRunResponse:
    """Stub: does not start a real backtest job."""
    return build_not_configured_backtest_run(profile_name=body.profile_name)


@router.post("/simulate-execution", response_model=ExecutionSimulationResponse)
def post_simulate_execution(body: BacktestProfileActionBody) -> ExecutionSimulationResponse:
    """Stub: simulated execution only; no broker orders."""
    return build_not_configured_execution_response(profile_name=body.profile_name)


@router.post("/validate-risk", response_model=RiskValidationResponse)
def post_validate_risk(body: BacktestProfileActionBody) -> RiskValidationResponse:
    """Stub: risk validation against simulated backtest results (not implemented)."""
    return build_not_configured_risk_validation(profile_name=body.profile_name)


@router.post("/promote-to-paper", response_model=PromoteToPaperResponse)
def post_promote_to_paper(body: BacktestProfileActionBody) -> PromoteToPaperResponse:
    """Stub: promotion gate only; does not call Alpaca or any broker."""
    return build_not_configured_promotion(profile_name=body.profile_name)
