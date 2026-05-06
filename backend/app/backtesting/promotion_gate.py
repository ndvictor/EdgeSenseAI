from __future__ import annotations

from app.backtesting.schemas import PromoteToPaperResponse


def build_not_configured_promotion(profile_name: str | None = None) -> PromoteToPaperResponse:
    return PromoteToPaperResponse(
        status="not_configured",
        message="Promotion to paper trading is not available until execution simulation and risk validation are implemented.",
        profile_name=profile_name,
        blocked_reasons=[
            "execution_simulation_not_implemented",
            "risk_validation_not_implemented",
        ],
    )
