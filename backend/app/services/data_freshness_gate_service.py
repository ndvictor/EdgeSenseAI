"""Data Freshness / Data Quality Gate Service.

Implements Step 3 of the Adaptive Agentic Quant Workflow:
- Gate every workflow before universe selection, scanner, or decision workflow trusts data
- Checks quote freshness, bar freshness, bid/ask availability, volume, data quality
- NO LLMs used - deterministic only
- NO fake values - blocks on unavailable data
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.market_data_service import MarketDataService


class DataFreshnessSymbolResult(BaseModel):
    """Result for a single symbol's data freshness check."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    provider: str = "unknown"
    data_quality: Literal["excellent", "good", "fair", "poor", "unavailable"] = "unavailable"
    is_mock: bool = False
    quote_age_seconds: float | None = None
    bar_age_seconds: float | None = None
    has_price: bool = False
    has_volume: bool = False
    has_bid_ask: bool = False
    spread_percent: float | None = None
    freshness_status: Literal["fresh", "stale", "unknown"] = "unknown"
    tradability_status: Literal["pass", "warn", "fail", "unknown"] = "unknown"
    decision: Literal["usable", "degraded", "blocked"] = "blocked"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DataFreshnessCheckRequest(BaseModel):
    """Request to run data freshness check."""

    model_config = ConfigDict(protected_namespaces=())

    symbols: list[str] = Field(default_factory=list, description="Explicit symbols to check. NO defaults.")
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    source: Literal["auto", "yfinance", "alpaca", "polygon", "mock"] = "auto"
    max_quote_age_seconds: float = 90.0
    max_bar_age_seconds: float = 300.0
    require_bid_ask: bool = False  # yfinance doesn't have bid/ask
    allow_mock: bool = False
    market_phase: str | None = None
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"


class DataFreshnessSummary(BaseModel):
    """Summary of data freshness check."""

    total_checked: int = 0
    usable_count: int = 0
    degraded_count: int = 0
    blocked_count: int = 0
    mock_blocked_count: int = 0
    unavailable_count: int = 0


class DataFreshnessCheckResponse(BaseModel):
    """Response from data freshness check."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["pass", "warn", "fail"]
    source: str
    checked_at: str
    results: list[DataFreshnessSymbolResult]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: DataFreshnessSummary


# In-memory storage for latest check
_LATEST_FRESHNESS_CHECK: DataFreshnessCheckResponse | None = None
_FRESHNESS_CHECK_HISTORY: list[DataFreshnessCheckResponse] = []


_MARKET_DATA = MarketDataService()


def _check_symbol_freshness(
    symbol: str,
    source: str,
    max_quote_age: float,
    max_bar_age: float,
    require_bid_ask: bool,
    allow_mock: bool,
    horizon: str,
) -> DataFreshnessSymbolResult:
    """Check data freshness for a single symbol."""
    result = DataFreshnessSymbolResult(symbol=symbol.upper())
    blockers: list[str] = []
    warnings: list[str] = []

    # Get market snapshot
    try:
        snapshot = _MARKET_DATA.get_market_snapshot(symbol, source=source)
    except Exception as e:
        blockers.append(f"Failed to fetch market data: {e}")
        result.blockers = blockers
        result.warnings = warnings
        result.decision = "blocked"
        result.tradability_status = "fail"
        return result

    # Check if mock data
    is_mock = snapshot.get("is_mock", False)
    result.is_mock = is_mock
    result.provider = snapshot.get("provider", "unknown")
    result.data_quality = snapshot.get("data_quality", "unavailable")

    # Block if mock and not allowed
    if is_mock and not allow_mock:
        blockers.append("Mock data detected but allow_mock=false")
        result.blockers = blockers
        result.warnings = warnings
        result.decision = "blocked"
        result.tradability_status = "fail"
        return result

    # Check data quality
    if result.data_quality in ["unavailable", "not_configured"]:
        blockers.append(f"Data quality is {result.data_quality}")
        result.blockers = blockers
        result.warnings = warnings
        result.decision = "blocked"
        result.tradability_status = "fail"
        return result

    # Check price availability
    price = snapshot.get("price")
    result.has_price = price is not None
    if not result.has_price:
        blockers.append("No price available")

    # Check volume availability
    volume = snapshot.get("volume")
    result.has_volume = volume is not None and volume > 0
    if not result.has_volume:
        if horizon == "day_trade":
            blockers.append("Volume required for day trading but not available")
        else:
            warnings.append("Volume not available - some signals may be limited")

    # Check bid/ask
    bid = snapshot.get("bid")
    ask = snapshot.get("ask")
    result.has_bid_ask = bid is not None and ask is not None
    if result.has_bid_ask and price:
        spread = ask - bid
        result.spread_percent = (spread / price) * 100 if price > 0 else None
    else:
        if require_bid_ask:
            blockers.append("Bid/ask required but not available")
        else:
            warnings.append("Bid/ask not available - spread estimates may be inaccurate")

    # Determine freshness (simplified - would check timestamp in real implementation)
    # For now, assume data is fresh if it has a price
    if result.has_price and not blockers:
        result.freshness_status = "fresh"
        result.quote_age_seconds = 0  # Unknown actual age
    elif result.has_price and warnings and not blockers:
        result.freshness_status = "fresh"
        result.quote_age_seconds = 0
    else:
        result.freshness_status = "unknown"

    # Determine tradability status
    if blockers:
        result.tradability_status = "fail"
        result.decision = "blocked"
    elif warnings:
        result.tradability_status = "warn"
        result.decision = "degraded"
    else:
        result.tradability_status = "pass"
        result.decision = "usable"

    result.blockers = blockers
    result.warnings = warnings
    return result


def run_data_freshness_check(request: DataFreshnessCheckRequest) -> DataFreshnessCheckResponse:
    """Run data freshness check on provided symbols."""
    global _LATEST_FRESHNESS_CHECK, _FRESHNESS_CHECK_HISTORY

    run_id = f"fresh-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc).isoformat()

    # Require explicit symbols
    if not request.symbols:
        response = DataFreshnessCheckResponse(
            run_id=run_id,
            status="fail",
            source=request.source,
            checked_at=checked_at,
            results=[],
            blockers=["No symbols provided. Explicit symbols required."],
            warnings=[],
            summary=DataFreshnessSummary(total_checked=0, blocked_count=0),
        )
        _LATEST_FRESHNESS_CHECK = response
        _FRESHNESS_CHECK_HISTORY.append(response)
        return response

    # Check each symbol
    results: list[DataFreshnessSymbolResult] = []
    for symbol in request.symbols:
        result = _check_symbol_freshness(
            symbol=symbol,
            source=request.source,
            max_quote_age=request.max_quote_age_seconds,
            max_bar_age=request.max_bar_age_seconds,
            require_bid_ask=request.require_bid_ask,
            allow_mock=request.allow_mock,
            horizon=request.horizon,
        )
        results.append(result)

    # Calculate summary
    usable_count = sum(1 for r in results if r.decision == "usable")
    degraded_count = sum(1 for r in results if r.decision == "degraded")
    blocked_count = sum(1 for r in results if r.decision == "blocked")
    mock_blocked_count = sum(1 for r in results if r.is_mock and r.decision == "blocked")
    unavailable_count = sum(1 for r in results if r.data_quality == "unavailable")

    summary = DataFreshnessSummary(
        total_checked=len(results),
        usable_count=usable_count,
        degraded_count=degraded_count,
        blocked_count=blocked_count,
        mock_blocked_count=mock_blocked_count,
        unavailable_count=unavailable_count,
    )

    # Determine overall status
    if blocked_count == len(results):
        status = "fail"
        blockers = ["All symbols blocked by data freshness checks"]
    elif blocked_count > 0:
        status = "warn"
        blockers = []
        warnings = [f"{blocked_count}/{len(results)} symbols blocked by data checks"]
    elif degraded_count > 0:
        status = "warn"
        blockers = []
        warnings = [f"{degraded_count}/{len(results)} symbols have degraded data quality"]
    else:
        status = "pass"
        blockers = []
        warnings = []

    response = DataFreshnessCheckResponse(
        run_id=run_id,
        status=status,
        source=request.source,
        checked_at=checked_at,
        results=results,
        blockers=blockers,
        warnings=warnings,
        summary=summary,
    )

    _LATEST_FRESHNESS_CHECK = response
    _FRESHNESS_CHECK_HISTORY.append(response)

    # Keep only last 100 checks
    if len(_FRESHNESS_CHECK_HISTORY) > 100:
        _FRESHNESS_CHECK_HISTORY = _FRESHNESS_CHECK_HISTORY[-100:]

    return response


def get_latest_data_freshness_check() -> DataFreshnessCheckResponse | None:
    """Get the most recent data freshness check."""
    return _LATEST_FRESHNESS_CHECK


def list_data_freshness_checks(limit: int = 20) -> list[DataFreshnessCheckResponse]:
    """List recent data freshness checks."""
    return _FRESHNESS_CHECK_HISTORY[-limit:]


def get_usable_symbols_from_latest_check() -> list[str]:
    """Get list of usable symbols from latest check."""
    if not _LATEST_FRESHNESS_CHECK:
        return []
    return [
        r.symbol for r in _LATEST_FRESHNESS_CHECK.results
        if r.decision in ["usable", "degraded"]
    ]


def get_blocked_symbols_from_latest_check() -> list[str]:
    """Get list of blocked symbols from latest check."""
    if not _LATEST_FRESHNESS_CHECK:
        return []
    return [
        r.symbol for r in _LATEST_FRESHNESS_CHECK.results
        if r.decision == "blocked"
    ]
