from __future__ import annotations

from app.backtesting.schemas import BacktestRunResponse


def build_not_configured_backtest_run(profile_name: str | None = None) -> BacktestRunResponse:
    return BacktestRunResponse(
        status="not_configured",
        message="Backtest run orchestration is not implemented yet. No historical run was started.",
        profile_name=profile_name,
        job_id=None,
    )
