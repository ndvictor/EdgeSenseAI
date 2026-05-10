from app.core.effective_runtime import effective_str
from app.data_providers.alpaca_provider import AlpacaProvider
from app.data_providers.base import MarketCandlesResponse, MarketSnapshot
from app.data_providers.polygon_provider import PolygonProvider
from app.data_providers.yfinance_provider import YFinanceProvider


class UnavailableMarketDataProvider:
    """Provider contract for missing/disabled market data sources."""

    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        return MarketSnapshot(
            symbol=symbol.upper(),
            asset_class=asset_class,
            current_price=0.0,
            previous_close=0.0,
            day_change_percent=0.0,
            volume=0,
            relative_volume=0.0,
            bid=0.0,
            ask=0.0,
            spread_percent=0.0,
            vwap=0.0,
            volatility_proxy=0.0,
            data_mode="source_unavailable",
            is_mock=False,
        )

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        return []

    def get_candles(self, symbol: str, period: str = "1mo", interval: str = "1d", asset_class: str = "stock") -> MarketCandlesResponse:
        return MarketCandlesResponse(
            symbol=symbol.upper(),
            asset_class=asset_class,
            interval=interval,
            period=period,
            data_mode="source_unavailable",
            candles=[],
        )


def get_market_data_provider(provider_name: str | None = None):
    """Return the active provider.

    Resolution order:
    1. Explicit provider_name passed by workflow/UI (yfinance/polygon/alpaca); never overridden by runtime.
    2. provider_name omitted or ``auto`` → MARKET_DATA_PROVIDER from runtime_settings.json / env / defaults
    3. Unavailable provider fallback when no supported real provider is selected

    Supported values:
    - yfinance: research-grade market data via yfinance
    - polygon: Polygon.io (requires POLYGON_API_KEY)
    - alpaca: Alpaca market data (requires ALPACA_MARKET_DATA_ENABLED and keys; equities only in Model Lab)
    """
    explicit = provider_name.strip().lower() if isinstance(provider_name, str) and provider_name.strip() else ""
    if explicit and explicit != "auto":
        provider = explicit
    else:
        provider = (effective_str("MARKET_DATA_PROVIDER") or "alpaca").lower().strip()
    if provider == "auto":
        provider = (effective_str("MARKET_DATA_PROVIDER") or "alpaca").lower().strip()

    if provider == "yfinance":
        return YFinanceProvider()
    if provider == "polygon":
        return PolygonProvider()
    if provider == "alpaca":
        return AlpacaProvider()

    return UnavailableMarketDataProvider()
