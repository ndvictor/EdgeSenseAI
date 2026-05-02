import os

from app.data_providers.mock_provider import MockMarketDataProvider
from app.data_providers.yfinance_provider import YFinanceProvider


def get_market_data_provider(provider_name: str | None = None):
    """Return the active provider.

    Resolution order:
    1. Explicit provider_name passed by workflow/UI
    2. MARKET_DATA_PROVIDER environment variable
    3. mock provider fallback

    Supported values:
    - mock: deterministic prototype data
    - yfinance: research-grade market data via yfinance
    """
    provider = (provider_name or os.getenv("MARKET_DATA_PROVIDER", "mock")).lower().strip()

    if provider == "yfinance":
        return YFinanceProvider()

    return MockMarketDataProvider()
