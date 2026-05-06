from __future__ import annotations

from app.backtesting.schemas import ExecutionSimulationCheck, RiskValidationResponse


def build_not_configured_risk_validation(profile_name: str | None = None) -> RiskValidationResponse:
    checks = [
        ExecutionSimulationCheck(
            name="risk_per_trade",
            status="not_configured",
            message="Risk validation engine not connected.",
        ),
        ExecutionSimulationCheck(
            name="max_drawdown",
            status="not_configured",
            message="Drawdown validator not connected.",
        ),
        ExecutionSimulationCheck(
            name="account_survival",
            status="not_configured",
            message="Account survival model not connected.",
        ),
    ]
    return RiskValidationResponse(
        status="not_configured",
        message="Backtesting risk validation service is not implemented yet.",
        profile_name=profile_name,
        checks=checks,
    )
