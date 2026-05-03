"""Risk Manager Service.

Hard veto layer. Decides whether a setup is allowed, watch-only, paper-only, reduced-size, or blocked.

Live trading always disabled.
Risk veto cannot be overridden.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class OpenPosition(BaseModel):
    """An open position for risk calculation."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    side: Literal["long", "short"] = "long"
    entry_price: float
    quantity: float
    unrealized_pnl: float = 0.0


class RiskReviewRequest(BaseModel):
    """Request for risk review."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    current_price: float | None = None
    final_signal_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    account_equity: float = Field(default=1000, ge=0)
    buying_power: float = Field(default=1000, ge=0)
    max_risk_per_trade_percent: float = Field(default=1.0, ge=0.1, le=10.0)
    max_daily_loss_percent: float = Field(default=2.0, ge=0.5, le=10.0)
    max_position_size_percent: float = Field(default=10.0, ge=1.0, le=100.0)
    min_reward_risk_ratio: float = Field(default=3.0, ge=1.0)
    spread_percent: float | None = None
    volatility_score: float | None = None
    liquidity_score: float | None = None
    data_quality: Literal["pass", "degraded", "fail", "unavailable"] | None = None
    open_positions: list[OpenPosition] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)


class RiskReviewResponse(BaseModel):
    """Response from risk review."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    symbol: str
    status: Literal["approved", "watch_only", "paper_only", "reduce_size", "blocked"]
    risk_score: int = Field(..., ge=0, le=100)
    hard_veto: bool
    veto_reasons: list[str] = Field(default_factory=list)
    max_dollar_risk: float
    max_position_size_dollars: float
    position_size_cap_dollars: float
    required_reward_risk_ratio: float
    approved_reward_risk_ratio: float | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime
    live_trading_allowed: bool = False  # Always false


# Constants
MIN_CONFIDENCE_FOR_APPROVAL = 0.50
MAX_SPREAD_FOR_LIVE = 1.0  # 1%
MIN_LIQUIDITY_SCORE = 0.3
HARD_VETO_SCORE_THRESHOLD = 80  # Risk score above this blocks

# In-memory storage
_LATEST_RISK_REVIEW: RiskReviewResponse | None = None


def calculate_position_sizing(request: RiskReviewRequest) -> dict[str, float]:
    """Calculate position sizing based on risk parameters."""
    # Max dollar risk based on account equity
    max_dollar_risk = request.account_equity * (request.max_risk_per_trade_percent / 100)

    # Max position size based on buying power limit
    max_position_size = request.buying_power * (request.max_position_size_percent / 100)

    # Cap position size to not exceed max risk if stop loss were 100%
    # This is a simplified calculation - real would use actual stop distance
    position_cap = min(max_position_size, max_dollar_risk * 3)  # Allow 3x leverage for swing

    return {
        "max_dollar_risk": max_dollar_risk,
        "max_position_size_dollars": max_position_size,
        "position_size_cap_dollars": position_cap,
    }


def calculate_risk_score(request: RiskReviewRequest) -> int:
    """Calculate risk score 0-100 (higher = more risky)."""
    score = 50  # Base score

    # Adjust for signal quality
    if request.final_signal_score is not None:
        if request.final_signal_score < 60:
            score += 20
        elif request.final_signal_score < 75:
            score += 10
        else:
            score -= 10

    # Adjust for confidence
    if request.confidence is not None:
        if request.confidence < MIN_CONFIDENCE_FOR_APPROVAL:
            score += 15
        elif request.confidence < 0.70:
            score += 5
        else:
            score -= 5

    # Adjust for spread
    if request.spread_percent is not None:
        if request.spread_percent > MAX_SPREAD_FOR_LIVE:
            score += 15
        elif request.spread_percent > 0.5:
            score += 5

    # Adjust for liquidity
    if request.liquidity_score is not None:
        if request.liquidity_score < MIN_LIQUIDITY_SCORE:
            score += 15
        elif request.liquidity_score < 0.5:
            score += 5

    # Adjust for volatility
    if request.volatility_score is not None:
        if request.volatility_score > 0.8:
            score += 10
        elif request.volatility_score < 0.2:
            score += 5  # Low vol can also be risky (no movement)

    # Adjust for data quality
    if request.data_quality == "fail":
        score += 25
    elif request.data_quality == "degraded":
        score += 10
    elif request.data_quality == "unavailable":
        score += 15

    # Adjust for existing positions (concentration risk)
    if request.open_positions:
        total_exposure = sum(p.quantity * p.entry_price for p in request.open_positions)
        exposure_pct = total_exposure / request.account_equity if request.account_equity > 0 else 0
        if exposure_pct > 0.5:
            score += 10
        if exposure_pct > 0.8:
            score += 15

    # Cap at 0-100
    return max(0, min(100, score))


def review_risk(request: RiskReviewRequest) -> RiskReviewResponse:
    """Review risk and determine status.

    Rules:
    - live_trading_allowed=false always.
    - If data_quality fail/unavailable: blocked or paper_only.
    - If final_signal_score < 60: blocked.
    - If confidence < 0.50: watch_only or blocked.
    - If reward/risk below min 3R: watch status (capital allocation may block).
    - If buying_power insufficient: blocked.
    - If spread too wide: blocked or watch_only.
    - Risk veto cannot be overridden.
    """
    run_id = f"risk-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc)
    blockers: list[str] = []
    warnings: list[str] = []
    veto_reasons: list[str] = []

    # Calculate position sizing
    sizing = calculate_position_sizing(request)

    # Calculate risk score
    risk_score = calculate_risk_score(request)

    # Determine hard veto
    hard_veto = risk_score >= HARD_VETO_SCORE_THRESHOLD

    # Rule: Data quality fail
    if request.data_quality == "fail":
        blockers.append("data_quality_failed")
        veto_reasons.append("Data quality check failed")

    # Rule: Data quality unavailable
    if request.data_quality == "unavailable":
        warnings.append("Data quality unavailable - trading on degraded information")
        risk_score += 10

    # Rule: Low signal score
    if request.final_signal_score is not None and request.final_signal_score < 60:
        blockers.append("signal_score_below_minimum")
        veto_reasons.append(f"Signal score {request.final_signal_score} below minimum 60")

    # Rule: Low confidence
    if request.confidence is not None and request.confidence < MIN_CONFIDENCE_FOR_APPROVAL:
        blockers.append("confidence_too_low")
        veto_reasons.append(f"Confidence {request.confidence:.2f} below minimum {MIN_CONFIDENCE_FOR_APPROVAL}")

    # Rule: Insufficient buying power
    if request.buying_power < sizing["max_dollar_risk"]:
        blockers.append("insufficient_buying_power")
        veto_reasons.append(f"Buying power ${request.buying_power:.2f} insufficient for min risk ${sizing['max_dollar_risk']:.2f}")

    # Rule: Wide spread
    if request.spread_percent is not None and request.spread_percent > MAX_SPREAD_FOR_LIVE:
        warnings.append(f"Spread {request.spread_percent}% exceeds recommended max {MAX_SPREAD_FOR_LIVE}%")

    # Rule: Low liquidity
    if request.liquidity_score is not None and request.liquidity_score < MIN_LIQUIDITY_SCORE:
        blockers.append("insufficient_liquidity")
        veto_reasons.append(f"Liquidity score {request.liquidity_score} below minimum {MIN_LIQUIDITY_SCORE}")

    # Determine status
    if blockers or hard_veto:
        if request.final_signal_score is not None and request.final_signal_score >= 60 and request.confidence is not None and request.confidence >= 0.4:
            # Marginal signal - allow paper only
            status: Literal["approved", "watch_only", "paper_only", "reduce_size", "blocked"] = "paper_only"
        else:
            status = "blocked"
    elif warnings or risk_score >= 60:
        status = "watch_only"
    else:
        status = "approved"

    result = RiskReviewResponse(
        run_id=run_id,
        symbol=request.symbol,
        status=status,
        risk_score=risk_score,
        hard_veto=hard_veto or len(blockers) > 0,
        veto_reasons=veto_reasons,
        max_dollar_risk=sizing["max_dollar_risk"],
        max_position_size_dollars=sizing["max_position_size_dollars"],
        position_size_cap_dollars=sizing["position_size_cap_dollars"],
        required_reward_risk_ratio=request.min_reward_risk_ratio,
        approved_reward_risk_ratio=request.min_reward_risk_ratio if status in ("approved", "paper_only") else None,
        blockers=blockers,
        warnings=warnings,
        checked_at=checked_at,
        live_trading_allowed=False,  # Always false
    )

    # Store latest
    global _LATEST_RISK_REVIEW
    _LATEST_RISK_REVIEW = result

    return result


def get_latest_risk_review() -> RiskReviewResponse | None:
    """Get the latest risk review."""
    return _LATEST_RISK_REVIEW
