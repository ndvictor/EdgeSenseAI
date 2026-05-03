"""No-Trade / Sit-Out Agent Service.

Makes no-trade a first-class decision.
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class NoTradeRequest(BaseModel):
    """Request for no-trade evaluation."""

    model_config = ConfigDict(protected_namespaces=())

    market_phase: str | None = None
    regime: str | None = None
    data_freshness_status: Literal["pass", "degraded", "fail", "unavailable"] | None = None
    model_drift_status: str | None = None
    false_trigger_count: int = Field(default=0, ge=0)
    final_signal_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    risk_status: Literal["approved", "watch_only", "paper_only", "reduce_size", "blocked"] | None = None
    llm_budget_status: Literal["approved", "skipped", "blocked"] | None = None
    buying_power: float | None = None
    account_equity: float | None = None
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class NoTradeResponse(BaseModel):
    """Response from no-trade evaluation."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    decision: Literal["trade_allowed", "watch_only", "no_trade", "reduce_cadence", "preserve_capital"]
    no_trade_reason: str
    severity: Literal["low", "medium", "high"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime


# Constants
FALSE_TRIGGER_THRESHOLD = 3
MIN_BUYING_POWER_RATIO = 0.1  # Need at least 10% of account equity as buying power
MIN_CONFIDENCE_FOR_TRADE = 0.50
MIN_SIGNAL_SCORE_FOR_UNKNOWN_REGIME = 75

# In-memory storage
_LATEST_NO_TRADE: NoTradeResponse | None = None


def evaluate_no_trade(request: NoTradeRequest) -> NoTradeResponse:
    """Evaluate whether to trade or not.

    Rules:
    - If data freshness fail: no_trade.
    - If regime unknown and score < 75: watch_only/no_trade.
    - If risk_status blocked: no_trade.
    - If too many false triggers: reduce_cadence.
    - If buying power too low: preserve_capital.
    - No recommendation output.
    """
    run_id = f"no-trade-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc)
    blockers: list[str] = []
    warnings: list[str] = list(request.warnings)

    # Rule 1: Data freshness fail
    if request.data_freshness_status == "fail":
        return NoTradeResponse(
            run_id=run_id,
            decision="no_trade",
            no_trade_reason="Data freshness check failed. Trading halted until data quality restored.",
            severity="high",
            blockers=["data_freshness_failed"],
            warnings=warnings,
            checked_at=checked_at,
        )

    # Rule 2: Risk status blocked
    if request.risk_status == "blocked":
        return NoTradeResponse(
            run_id=run_id,
            decision="no_trade",
            no_trade_reason="Risk review blocked this trade. Cannot proceed.",
            severity="high",
            blockers=["risk_blocked"],
            warnings=warnings,
            checked_at=checked_at,
        )

    # Rule 3: Too many false triggers
    if request.false_trigger_count >= FALSE_TRIGGER_THRESHOLD:
        return NoTradeResponse(
            run_id=run_id,
            decision="reduce_cadence",
            no_trade_reason=f"{request.false_trigger_count} false triggers detected. Reducing scan cadence to avoid overtrading.",
            severity="medium",
            blockers=[],
            warnings=warnings + [f"False trigger count: {request.false_trigger_count}"],
            checked_at=checked_at,
        )

    # Rule 4: Low buying power
    if request.buying_power is not None and request.account_equity is not None:
        if request.account_equity > 0:
            buying_power_ratio = request.buying_power / request.account_equity
            if buying_power_ratio < MIN_BUYING_POWER_RATIO:
                return NoTradeResponse(
                    run_id=run_id,
                    decision="preserve_capital",
                    no_trade_reason=f"Low buying power: ${request.buying_power:.2f} ({buying_power_ratio*100:.1f}% of equity). Preserving capital.",
                    severity="medium",
                    blockers=["low_buying_power"],
                    warnings=warnings,
                    checked_at=checked_at,
                )

    # Rule 5: Unknown regime with low confidence
    if request.regime in (None, "unknown", "uncertain"):
        if request.final_signal_score is not None and request.final_signal_score < MIN_SIGNAL_SCORE_FOR_UNKNOWN_REGIME:
            return NoTradeResponse(
                run_id=run_id,
                decision="watch_only",
                no_trade_reason=f"Unknown market regime with signal score {request.final_signal_score} below threshold {MIN_SIGNAL_SCORE_FOR_UNKNOWN_REGIME}. Watch and wait.",
                severity="medium",
                blockers=[],
                warnings=warnings + ["Unknown market regime"],
                checked_at=checked_at,
            )

    # Rule 6: Low confidence
    if request.confidence is not None and request.confidence < MIN_CONFIDENCE_FOR_TRADE:
        return NoTradeResponse(
            run_id=run_id,
            decision="watch_only",
            no_trade_reason=f"Confidence {request.confidence:.2f} below minimum {MIN_CONFIDENCE_FOR_TRADE}. Watching for better setup.",
            severity="low",
            blockers=[],
            warnings=warnings + [f"Low confidence: {request.confidence:.2f}"],
            checked_at=checked_at,
        )

    # Rule 7: Risk status watch or paper only
    if request.risk_status in ("watch_only", "paper_only"):
        return NoTradeResponse(
            run_id=run_id,
            decision="watch_only" if request.risk_status == "watch_only" else "trade_allowed",
            no_trade_reason=f"Risk status is {request.risk_status}. {'Watching for confirmation.' if request.risk_status == 'watch_only' else 'Paper trading only allowed.'}",
            severity="low" if request.risk_status == "paper_only" else "medium",
            blockers=[],
            warnings=warnings + [f"Risk status: {request.risk_status}"],
            checked_at=checked_at,
        )

    # All checks passed - trade allowed
    result = NoTradeResponse(
        run_id=run_id,
        decision="trade_allowed",
        no_trade_reason="All no-trade checks passed. Proceeding with trade evaluation.",
        severity="low",
        blockers=[],
        warnings=warnings,
        checked_at=checked_at,
    )

    # Store latest
    global _LATEST_NO_TRADE
    _LATEST_NO_TRADE = result

    return result


def get_latest_no_trade() -> NoTradeResponse | None:
    """Get the latest no-trade evaluation."""
    return _LATEST_NO_TRADE
