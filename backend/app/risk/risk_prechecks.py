"""Risk precheck orchestration — combines EdgeSense limits with Risk Manager service."""

from __future__ import annotations

from typing import Any, Literal, cast

from app.execution.edgesense_execution_config import EdgeSenseExecutionConfig, load_edgesense_execution_config
from app.execution.risk_state_store import get_daily_loss_pct_used, is_risk_lockout
from app.execution.schemas import PrecheckStepResult
from app.risk.position_sizing import order_notional
from app.services.risk_manager_service import RiskReviewRequest, review_risk


def run_edgesense_risk_precheck(
    *,
    symbol: str,
    asset_class: str,
    side: str,
    quantity: float | None,
    limit_price: float | None,
    stop_loss_price: float | None,
    spread_pct: float | None,
    reference_price: float | None,
    buying_power: float | None,
    equity: float | None,
    confidence: float | None,
    exempt_stop_loss: bool,
    cfg: EdgeSenseExecutionConfig | None = None,
) -> PrecheckStepResult:
    cfg = cfg or load_edgesense_execution_config()
    blockers: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"config": edgesense_public_cfg(cfg)}

    if is_risk_lockout():
        blockers.append("risk_lockout_active")

    daily_used = get_daily_loss_pct_used()
    details["daily_loss_pct_used"] = daily_used
    if daily_used >= cfg.max_daily_loss_pct:
        blockers.append("max_daily_loss_pct_exceeded")

    if spread_pct is not None and spread_pct > cfg.max_spread_pct:
        blockers.append(f"spread_pct_{spread_pct:.3f}_exceeds_max_{cfg.max_spread_pct}")

    if not exempt_stop_loss and stop_loss_price is None:
        blockers.append("stop_loss_required")

    notional = order_notional(quantity, limit_price or reference_price, None)
    if notional is not None and buying_power is not None and notional > buying_power * 1.001:
        blockers.append("order_exceeds_buying_power")

    # Risk manager veto layer (deterministic)
    ac = cast(Literal["stock", "option", "crypto"], asset_class if asset_class in ("stock", "option", "crypto") else "stock")
    rr = review_risk(
        RiskReviewRequest(
            symbol=symbol,
            asset_class=ac,
            current_price=reference_price,
            final_signal_score=65.0 if confidence is None else min(100.0, max(0.0, confidence * 100)),
            confidence=confidence if confidence is not None else 0.75,
            account_equity=equity or 0.0,
            buying_power=buying_power or 0.0,
            max_risk_per_trade_percent=cfg.max_trade_risk_pct,
            max_daily_loss_percent=cfg.max_daily_loss_pct,
            spread_percent=spread_pct,
            data_quality="pass" if reference_price else "unavailable",
        )
    )
    details["risk_manager_status"] = rr.status
    if rr.hard_veto or rr.status == "blocked":
        blockers.extend(rr.veto_reasons or ["risk_manager_blocked"])
    if rr.warnings:
        warnings.extend(rr.warnings)

    return PrecheckStepResult(
        name="risk_precheck",
        passed=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        details=details,
    )


def edgesense_public_cfg(cfg: EdgeSenseExecutionConfig) -> dict[str, Any]:
    return {
        "max_daily_loss_pct": cfg.max_daily_loss_pct,
        "max_trade_risk_pct": cfg.max_trade_risk_pct,
        "max_spread_pct": cfg.max_spread_pct,
        "max_slippage_pct": cfg.max_slippage_pct,
    }
