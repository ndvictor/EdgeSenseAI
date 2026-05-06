"""Portfolio concentration and limits precheck."""

from __future__ import annotations

from typing import Any

from app.execution.edgesense_execution_config import EdgeSenseExecutionConfig, load_edgesense_execution_config
from app.execution.schemas import PrecheckStepResult
from app.risk.portfolio_limits import count_open_positions, symbol_exposure_pct


def run_portfolio_precheck(
    *,
    symbol: str,
    positions: list[Any],
    equity: float | None,
    proposed_additional_notional: float | None,
    cfg: EdgeSenseExecutionConfig | None = None,
) -> PrecheckStepResult:
    cfg = cfg or load_edgesense_execution_config()
    blockers: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {}

    npos = count_open_positions(positions)
    details["open_positions"] = npos
    if npos >= cfg.max_open_positions:
        # allow if adding to existing symbol only? conservative: block at cap
        blockers.append("max_open_positions_reached")

    def _as_dict(p: Any) -> dict[str, Any]:
        if isinstance(p, dict):
            return p
        if hasattr(p, "model_dump"):
            return p.model_dump()
        return {
            "symbol": getattr(p, "symbol", ""),
            "market_value": getattr(p, "market_value", None),
            "qty": getattr(p, "qty", None),
            "current_price": getattr(p, "current_price", None),
        }

    exp = symbol_exposure_pct([_as_dict(p) for p in positions], symbol, equity)
    details["symbol_exposure_pct"] = exp
    if exp is not None and proposed_additional_notional is not None and equity:
        add_pct = (proposed_additional_notional / equity) * 100.0
        if exp + add_pct > cfg.max_symbol_exposure_pct:
            blockers.append("max_symbol_exposure_pct_would_exceed")

    # Correlated / sector concentration: not configured — explicit warning
    warnings.append("sector_correlation_not_configured_provider_data")

    sym_upper = symbol.upper()
    dup = sum(1 for p in positions if str(_as_dict(p).get("symbol") or "").upper() == sym_upper)
    if dup > 0 and proposed_additional_notional:
        warnings.append("duplicate_symbol_already_has_open_position")

    return PrecheckStepResult(
        name="portfolio_precheck",
        passed=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        details=details,
    )
