"""Market Regime Model Service.

Implements Step 4 of the Adaptive Agentic Quant Workflow:
- Classify current market state using deterministic baseline
- NO LLM calls - uses SPY/QQQ/VIX data when available
- Returns unknown/warn if data unavailable - NO fake output
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.market_data_service import MarketDataService


class MarketRegimeRequest(BaseModel):
    """Request to run market regime detection."""

    model_config = ConfigDict(protected_namespaces=())

    source: Literal["auto", "yfinance", "alpaca", "polygon", "mock"] = "auto"
    symbols: list[str] = Field(default_factory=list, description="Optional symbols to use for regime detection")
    spy_symbol: str = "SPY"
    qqq_symbol: str = "QQQ"
    vix_symbol: str = "^VIX"  # May not be available on all providers
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    allow_mock: bool = False


class MarketRegimeResponse(BaseModel):
    """Response from market regime detection."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["pass", "warn", "fail"]
    regime: Literal["risk_on", "risk_off", "chop", "momentum", "volatility_expansion", "mean_reversion", "unknown"]
    trend_state: Literal["uptrend", "downtrend", "sideways", "mixed", "unknown"]
    volatility_state: Literal["low", "normal", "elevated", "high", "extreme", "unknown"]
    breadth_proxy: str = "unknown"  # Simplified - would use NYSE advance/decline
    sector_rotation_proxy: str = "unknown"  # Simplified
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    regime_score: float = Field(default=0.0, ge=0.0, le=100.0)
    allowed_strategy_families: list[str] = Field(default_factory=list)
    blocked_strategy_families: list[str] = Field(default_factory=list)
    inputs_used: dict = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: str


# In-memory storage
_LATEST_REGIME: MarketRegimeResponse | None = None
_REGIME_HISTORY: list[MarketRegimeResponse] = []

_MARKET_DATA = MarketDataService()


def _get_price_history_safe(symbol: str, source: str, period: str = "1mo", interval: str = "1d") -> dict | None:
    """Safely get price history, returns None on failure."""
    try:
        result = _MARKET_DATA.get_price_history(symbol, period=period, interval=interval, source=source)
        if result.get("data_quality") in ["unavailable", "not_configured"]:
            return None
        if not result.get("data"):
            return None
        return result
    except Exception:
        return None


def _calculate_trend_state(spy_data: list | None, qqq_data: list | None) -> tuple[str, float]:
    """Calculate trend state from price history."""
    if not spy_data and not qqq_data:
        return "unknown", 0.0

    def _calc_returns(data: list) -> list[float]:
        returns = []
        for i in range(1, len(data)):
            prev_close = data[i-1].get("close")
            curr_close = data[i].get("close")
            if prev_close and curr_close and prev_close > 0:
                returns.append((curr_close - prev_close) / prev_close)
        return returns

    spy_returns = _calc_returns(spy_data) if spy_data else []
    qqq_returns = _calc_returns(qqq_data) if qqq_data else []

    # Use whichever has data
    returns = spy_returns if spy_returns else qqq_returns

    if not returns:
        return "unknown", 0.0

    avg_return = sum(returns) / len(returns)
    total_return = sum(returns)

    # Determine trend
    if total_return > 0.05:  # >5% over period
        return "uptrend", min(total_return * 10, 1.0)  # Scale confidence
    elif total_return < -0.05:  # <-5% over period
        return "downtrend", min(abs(total_return) * 10, 1.0)
    elif abs(total_return) < 0.02:  # Small movement
        return "sideways", 0.5
    else:
        return "mixed", 0.6


def _calculate_volatility_state(returns: list[float]) -> tuple[str, float]:
    """Calculate volatility state from returns."""
    if not returns or len(returns) < 2:
        return "unknown", 0.0

    # Calculate standard deviation
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    std_dev = variance ** 0.5

    # Annualized volatility approximation
    annualized_vol = std_dev * (252 ** 0.5)  # Assuming daily returns

    if annualized_vol < 0.10:
        return "low", annualized_vol
    elif annualized_vol < 0.20:
        return "normal", annualized_vol
    elif annualized_vol < 0.30:
        return "elevated", annualized_vol
    elif annualized_vol < 0.40:
        return "high", annualized_vol
    else:
        return "extreme", annualized_vol


def _determine_regime(
    trend_state: str,
    volatility_state: str,
    spy_available: bool,
    qqq_available: bool,
    vix_available: bool,
) -> tuple[str, float, float]:
    """Determine market regime from inputs."""
    if not spy_available and not qqq_available:
        return "unknown", 0.0, 0.0

    # Regime determination logic
    if trend_state == "uptrend" and volatility_state in ["low", "normal"]:
        regime = "risk_on"
        score = 80.0
        confidence = 0.7
    elif trend_state == "downtrend" and volatility_state in ["elevated", "high", "extreme"]:
        regime = "risk_off"
        score = 20.0
        confidence = 0.7
    elif trend_state == "uptrend" and volatility_state in ["elevated", "high"]:
        regime = "momentum"
        score = 75.0
        confidence = 0.6
    elif trend_state == "sideways" and volatility_state in ["elevated", "high"]:
        regime = "chop"
        score = 50.0
        confidence = 0.5
    elif trend_state == "sideways" and volatility_state == "low":
        regime = "mean_reversion"
        score = 45.0
        confidence = 0.5
    elif volatility_state == "extreme":
        regime = "volatility_expansion"
        score = 30.0
        confidence = 0.6
    else:
        regime = "chop"
        score = 50.0
        confidence = 0.5

    return regime, score, confidence


def _determine_strategy_families(
    regime: str,
    trend_state: str,
    volatility_state: str,
) -> tuple[list[str], list[str]]:
    """Determine allowed and blocked strategy families based on regime."""
    allowed = []
    blocked = []

    # Base strategies always allowed in paper mode
    base_allowed = ["stock_swing", "stock_day_trading", "stock_one_month"]

    if regime == "risk_on":
        allowed = base_allowed + ["options_swing", "crypto_swing", "crypto_intraday"]
        blocked = ["options_earnings"]  # Too risky in strong uptrend
    elif regime == "risk_off":
        allowed = ["stock_swing"]  # Only conservative
        blocked = ["stock_day_trading", "options_day_trading", "options_swing", "options_earnings", "crypto_intraday", "crypto_cycle"]
    elif regime == "chop":
        allowed = base_allowed + ["options_swing"]
        blocked = ["options_day_trading", "crypto_intraday", "options_earnings"]
    elif regime == "momentum":
        allowed = base_allowed + ["options_swing", "crypto_swing"]
        blocked = ["options_earnings", "crypto_intraday"]  # Avoid event risk
    elif regime == "mean_reversion":
        allowed = base_allowed + ["options_swing"]
        blocked = ["options_day_trading", "options_earnings"]
    elif regime == "volatility_expansion":
        allowed = ["stock_swing", "stock_one_month"]
        blocked = ["stock_day_trading", "options_day_trading", "options_swing", "options_earnings", "crypto_intraday", "crypto_cycle"]
    else:  # unknown
        allowed = ["stock_swing"]  # Most conservative
        blocked = ["stock_day_trading", "options_day_trading", "options_swing", "options_earnings", "crypto_intraday", "crypto_swing", "crypto_cycle", "stock_one_month"]

    return allowed, blocked


def run_market_regime_model(request: MarketRegimeRequest) -> MarketRegimeResponse:
    """Run market regime detection."""
    global _LATEST_REGIME

    run_id = f"regime-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc).isoformat()

    blockers: list[str] = []
    warnings: list[str] = []

    # Try to get SPY data
    spy_data = _get_price_history_safe(request.spy_symbol, request.source)
    spy_available = spy_data is not None and spy_data.get("data")

    # Try to get QQQ data
    qqq_data = _get_price_history_safe(request.qqq_symbol, request.source)
    qqq_available = qqq_data is not None and qqq_data.get("data")

    # Check if mock data
    if spy_available and spy_data.get("is_mock") and not request.allow_mock:
        blockers.append(f"SPY data is mock but allow_mock=false")
        spy_available = False
        spy_data = None

    if qqq_available and qqq_data.get("is_mock") and not request.allow_mock:
        blockers.append(f"QQQ data is mock but allow_mock=false")
        qqq_available = False
        qqq_data = None

    # VIX is optional - don't block if unavailable
    vix_available = False
    vix_warnings = []

    # Determine inputs used
    inputs_used = {
        "spy_symbol": request.spy_symbol,
        "spy_available": spy_available,
        "qqq_symbol": request.qqq_symbol,
        "qqq_available": qqq_available,
        "vix_symbol": request.vix_symbol,
        "vix_available": vix_available,
        "source": request.source,
    }

    # If neither SPY nor QQQ available, return unknown
    if not spy_available and not qqq_available:
        warnings.append("Neither SPY nor QQQ data available - cannot determine regime")
        if not blockers:
            blockers.append("No market index data available")

        response = MarketRegimeResponse(
            run_id=run_id,
            status="fail" if blockers else "warn",
            regime="unknown",
            trend_state="unknown",
            volatility_state="unknown",
            confidence=0.0,
            regime_score=0.0,
            allowed_strategy_families=[],
            blocked_strategy_families=[
                "stock_day_trading", "stock_swing", "stock_one_month",
                "options_day_trading", "options_swing", "options_earnings",
                "crypto_intraday", "crypto_swing", "crypto_cycle"
            ],
            inputs_used=inputs_used,
            blockers=blockers,
            warnings=warnings,
            checked_at=checked_at,
        )
        _LATEST_REGIME = response
        _REGIME_HISTORY.append(response)
        return response

    # Calculate trend state
    spy_prices = spy_data.get("data") if spy_data else None
    qqq_prices = qqq_data.get("data") if qqq_data else None
    trend_state, trend_confidence = _calculate_trend_state(spy_prices, qqq_prices)

    # Calculate volatility
    # Combine returns from both if available
    returns = []
    if spy_prices:
        for i in range(1, len(spy_prices)):
            prev = spy_prices[i-1].get("close")
            curr = spy_prices[i].get("close")
            if prev and curr and prev > 0:
                returns.append((curr - prev) / prev)

    volatility_state, vol_value = _calculate_volatility_state(returns)

    # Determine regime
    regime, regime_score, confidence = _determine_regime(
        trend_state=trend_state,
        volatility_state=volatility_state,
        spy_available=spy_available,
        qqq_available=qqq_available,
        vix_available=vix_available,
    )

    # Determine allowed/blocked strategies
    allowed, blocked = _determine_strategy_families(regime, trend_state, volatility_state)

    # Determine overall status
    if blockers:
        status = "fail"
    elif warnings or not spy_available or not qqq_available:
        status = "warn"
    else:
        status = "pass"

    response = MarketRegimeResponse(
        run_id=run_id,
        status=status,
        regime=regime,
        trend_state=trend_state,
        volatility_state=volatility_state,
        confidence=confidence,
        regime_score=regime_score,
        allowed_strategy_families=allowed,
        blocked_strategy_families=blocked,
        inputs_used=inputs_used,
        blockers=blockers,
        warnings=warnings,
        checked_at=checked_at,
    )

    _LATEST_REGIME = response
    _REGIME_HISTORY.append(response)

    # Keep only last 100
    if len(_REGIME_HISTORY) > 100:
        _REGIME_HISTORY = _REGIME_HISTORY[-100:]

    return response


def get_latest_market_regime() -> MarketRegimeResponse | None:
    """Get the most recent market regime detection."""
    return _LATEST_REGIME


def list_market_regime_history(limit: int = 20) -> list[MarketRegimeResponse]:
    """List recent market regime detections."""
    return _REGIME_HISTORY[-limit:]
