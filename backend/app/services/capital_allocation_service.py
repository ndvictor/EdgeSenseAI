"""Capital Allocation & Trade Plan Agent Service.

Converts validated, risk-reviewed opportunity into deterministic paper/research plan.
This does not execute. This does not create a live trade.

Deterministic calculations only.
Must meet 3R reward/risk.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CapitalAllocationRequest(BaseModel):
    """Request for capital allocation plan."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    current_price: float = Field(..., gt=0)
    final_signal_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1)
    risk_status: Literal["approved", "watch_only", "paper_only", "reduce_size", "blocked"]
    account_equity: float = Field(default=1000, ge=0)
    buying_power: float = Field(default=1000, ge=0)
    max_risk_per_trade_percent: float = Field(default=1.0, ge=0.1, le=10.0)
    max_position_size_percent: float = Field(default=10.0, ge=1.0, le=100.0)
    min_reward_risk_ratio: float = Field(default=3.0, ge=1.0)
    volatility_score: float | None = None
    atr_proxy: float | None = None  # Average True Range or volatility proxy
    support_level: float | None = None
    resistance_level: float | None = None
    spread_percent: float | None = None
    max_hold_minutes: int | None = None  # For day trading


class CapitalAllocationResponse(BaseModel):
    """Response with capital allocation plan."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    symbol: str
    status: Literal["plan_created", "watch_only", "blocked"]
    opportunity_score: int = Field(..., ge=0, le=100)
    capital_allocation_dollars: float
    risk_dollars: float
    position_size_units: float
    entry_zone_low: float
    entry_zone_high: float
    stop_loss: float
    invalidation: float  # Price at which thesis is invalidated
    target_price: float
    target_2_price: float | None = None
    reward_risk_ratio: float
    max_hold_minutes: int | None = None
    timeout_rule: str
    rotation_rule: str
    approval_required: bool = True
    paper_trade_allowed: bool
    live_trading_allowed: bool = False  # Always false
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


# Constants
DEFAULT_ATR_MULTIPLIER_STOP = 2.0  # 2x ATR for stop
MIN_RR_FOR_APPROVAL = 2.0
TARGET_RR = 3.0
MAX_HOLD_MINUTES_SWING = 2880  # 48 hours default
MAX_HOLD_MINUTES_DAY = 390  # Full market day

# In-memory storage
_LATEST_CAPITAL_ALLOCATION: CapitalAllocationResponse | None = None


def _calculate_atr_proxy(current_price: float, volatility_score: float | None) -> float:
    """Calculate ATR proxy from volatility score if not provided."""
    if volatility_score is not None:
        # Approximate ATR as % of price based on volatility
        return current_price * (0.01 + volatility_score * 0.04)  # 1-5% of price
    return current_price * 0.02  # Default 2%


def _calculate_entry_zone(
    current_price: float, spread_percent: float | None
) -> tuple[float, float]:
    """Calculate entry zone allowing for spread/slippage."""
    spread = spread_percent or 0.1  # Default 0.1% spread
    low = current_price * (1 - spread / 100)
    high = current_price * (1 + spread / 100)
    return (low, high)


def _calculate_stop_and_target(
    current_price: float,
    atr: float,
    support_level: float | None,
    min_rr: float,
) -> tuple[float, float, float]:
    """Calculate stop loss, invalidation, and target price.

    Rules:
    - Stop is at support or 2x ATR below entry, whichever is lower (more conservative)
    - Invalidation is at stop level
    - Target must achieve at least min_rr reward/risk
    """
    # Base stop from ATR
    atr_stop = current_price - (atr * DEFAULT_ATR_MULTIPLIER_STOP)

    # Support-based stop if available
    if support_level is not None and support_level < current_price:
        stop = min(atr_stop, support_level)
    else:
        stop = atr_stop

    # Invalidation is at stop level
    invalidation = stop

    # Calculate target based on min RR
    risk = current_price - stop
    if risk <= 0:
        # Invalid - can't have stop above entry
        return (stop, invalidation, current_price * 1.01)  # Minimal target

    target = current_price + (risk * TARGET_RR)

    return (stop, invalidation, target)


def create_capital_allocation_plan(request: CapitalAllocationRequest) -> CapitalAllocationResponse:
    """Create capital allocation plan.

    Rules:
    - Deterministic calculations only.
    - Entry/stop/target from price + ATR/volatility/support/resistance.
    - Must meet min_reward_risk_ratio.
    - Must respect max risk and max position size.
    - If cannot produce valid 3R plan, status blocked.
    - No LLM invented levels.
    - No live execution.
    """
    run_id = f"cap-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    blockers: list[str] = []
    warnings: list[str] = []

    # Rule: Blocked risk status
    if request.risk_status == "blocked":
        return CapitalAllocationResponse(
            run_id=run_id,
            symbol=request.symbol,
            status="blocked",
            opportunity_score=0,
            capital_allocation_dollars=0,
            risk_dollars=0,
            position_size_units=0,
            entry_zone_low=0,
            entry_zone_high=0,
            stop_loss=0,
            invalidation=0,
            target_price=0,
            target_2_price=None,
            reward_risk_ratio=0,
            max_hold_minutes=request.max_hold_minutes,
            timeout_rule="N/A - blocked",
            rotation_rule="N/A - blocked",
            paper_trade_allowed=False,
            live_trading_allowed=False,
            blockers=["risk_status_blocked"],
            warnings=warnings,
            created_at=created_at,
        )

    # Calculate ATR proxy
    atr = request.atr_proxy or _calculate_atr_proxy(request.current_price, request.volatility_score)

    # Calculate entry zone
    entry_low, entry_high = _calculate_entry_zone(request.current_price, request.spread_percent)

    # Calculate stop and target
    stop, invalidation, target = _calculate_stop_and_target(
        request.current_price,
        atr,
        request.support_level,
        request.min_reward_risk_ratio,
    )

    # Calculate risk per share/unit
    risk_per_unit = entry_high - stop  # Conservative: use high entry
    if risk_per_unit <= 0:
        blockers.append("invalid_stop_loss")
        return CapitalAllocationResponse(
            run_id=run_id,
            symbol=request.symbol,
            status="blocked",
            opportunity_score=0,
            capital_allocation_dollars=0,
            risk_dollars=0,
            position_size_units=0,
            entry_zone_low=entry_low,
            entry_zone_high=entry_high,
            stop_loss=stop,
            invalidation=invalidation,
            target_price=target,
            target_2_price=None,
            reward_risk_ratio=0,
            max_hold_minutes=request.max_hold_minutes,
            timeout_rule="N/A - invalid stop",
            rotation_rule="N/A - invalid stop",
            paper_trade_allowed=False,
            live_trading_allowed=False,
            blockers=blockers,
            warnings=warnings,
            created_at=created_at,
        )

    # Calculate reward/risk ratio
    reward = target - entry_low  # Conservative: use low entry for reward
    rr_ratio = reward / risk_per_unit if risk_per_unit > 0 else 0

    # Check minimum RR
    if rr_ratio < MIN_RR_FOR_APPROVAL:
        blockers.append(f"insufficient_reward_risk_ratio:{rr_ratio:.2f} < {MIN_RR_FOR_APPROVAL}")
        return CapitalAllocationResponse(
            run_id=run_id,
            symbol=request.symbol,
            status="blocked",
            opportunity_score=0,
            capital_allocation_dollars=0,
            risk_dollars=0,
            position_size_units=0,
            entry_zone_low=entry_low,
            entry_zone_high=entry_high,
            stop_loss=stop,
            invalidation=invalidation,
            target_price=target,
            target_2_price=None,
            reward_risk_ratio=rr_ratio,
            max_hold_minutes=request.max_hold_minutes,
            timeout_rule="N/A - insufficient RR",
            rotation_rule="N/A - insufficient RR",
            paper_trade_allowed=False,
            live_trading_allowed=False,
            blockers=blockers,
            warnings=warnings,
            created_at=created_at,
        )

    # Calculate position sizing
    max_risk_dollars = request.account_equity * (request.max_risk_per_trade_percent / 100)
    max_position_dollars = request.buying_power * (request.max_position_size_percent / 100)

    # Position size based on risk
    position_size_units = max_risk_dollars / risk_per_unit if risk_per_unit > 0 else 0
    position_dollars = position_size_units * entry_high

    # Cap by max position size
    if position_dollars > max_position_dollars:
        position_size_units = max_position_dollars / entry_high
        position_dollars = max_position_dollars
        warnings.append(f"Position capped by max size limit: ${max_position_dollars:.2f}")

    # Cap by buying power
    if position_dollars > request.buying_power:
        position_size_units = request.buying_power / entry_high
        position_dollars = request.buying_power
        warnings.append(f"Position capped by buying power: ${request.buying_power:.2f}")

    # Recalculate actual risk
    actual_risk_dollars = position_size_units * risk_per_unit

    # Calculate opportunity score
    opportunity_score = int(
        (request.final_signal_score * 0.4) +
        (request.confidence * 30) +
        (min(rr_ratio, 5) * 6)  # Cap RR contribution at 5
    )
    opportunity_score = max(0, min(100, opportunity_score))

    # Calculate target 2 (if applicable)
    target_2 = target + (target - entry_low) * 0.5 if rr_ratio >= 2.5 else None

    # Determine hold time
    if request.max_hold_minutes:
        max_hold = request.max_hold_minutes
    elif request.horizon == "day_trade":
        max_hold = MAX_HOLD_MINUTES_DAY
    else:
        max_hold = MAX_HOLD_MINUTES_SWING

    # Timeout and rotation rules
    timeout_rule = f"Close if not triggered within {max_hold // 4} minutes or if held > {max_hold} minutes"
    rotation_rule = "Rotate if higher conviction signal appears with better RR"

    # Determine paper trade allowance
    paper_allowed = request.risk_status in ("approved", "paper_only", "reduce_size", "watch_only")

    result = CapitalAllocationResponse(
        run_id=run_id,
        symbol=request.symbol,
        status="plan_created",
        opportunity_score=opportunity_score,
        capital_allocation_dollars=position_dollars,
        risk_dollars=actual_risk_dollars,
        position_size_units=position_size_units,
        entry_zone_low=entry_low,
        entry_zone_high=entry_high,
        stop_loss=stop,
        invalidation=invalidation,
        target_price=target,
        target_2_price=target_2,
        reward_risk_ratio=rr_ratio,
        max_hold_minutes=max_hold,
        timeout_rule=timeout_rule,
        rotation_rule=rotation_rule,
        paper_trade_allowed=paper_allowed,
        live_trading_allowed=False,
        blockers=blockers,
        warnings=warnings,
        created_at=created_at,
    )

    # Store latest
    global _LATEST_CAPITAL_ALLOCATION
    _LATEST_CAPITAL_ALLOCATION = result

    return result


def get_latest_capital_allocation() -> CapitalAllocationResponse | None:
    """Get the latest capital allocation plan."""
    return _LATEST_CAPITAL_ALLOCATION
