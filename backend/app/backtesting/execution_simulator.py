from __future__ import annotations

from app.backtesting.schemas import ExecutionSimulationCheck, ExecutionSimulationResponse

EXECUTION_CHECK_SPECS: list[tuple[str, str]] = [
    ("simulated_entry_fill", "Simulated entry fill"),
    ("simulated_exit_fill", "Simulated exit fill"),
    ("spread_slippage_model", "Spread/slippage model"),
    ("stop_loss_behavior", "Stop-loss behavior"),
    ("target_before_stop_behavior", "Target-before-stop behavior"),
    ("time_stop_behavior", "Time stop behavior"),
    ("partial_fill_assumption", "Partial fill assumption"),
    ("risk_per_trade_validation", "Risk-per-trade validation"),
    ("max_drawdown_validation", "Max drawdown validation"),
    ("account_survival_validation", "Account survival validation"),
]


def build_not_configured_execution_checks() -> list[ExecutionSimulationCheck]:
    return [
        ExecutionSimulationCheck(
            name=key,
            status="not_configured",
            message="No historical fill model connected.",
        )
        for key, _ in EXECUTION_CHECK_SPECS
    ]


def build_not_configured_execution_response(profile_name: str | None = None) -> ExecutionSimulationResponse:
    return ExecutionSimulationResponse(
        status="not_configured",
        message="Backtesting execution simulation service is not implemented yet.",
        profile_name=profile_name,
        checks=build_not_configured_execution_checks(),
        promotion_gate="contract_ready",
    )
