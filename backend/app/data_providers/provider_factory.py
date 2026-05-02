import os

from app.data_providers.mock_provider import MockMarketDataProvider
from app.data_providers.yfinance_provider import YFinanceProvider


def get_market_data_provider():
    """Return the active provider based on MARKET_DATA_PROVIDER.

    Supported values:
    - mock: deterministic prototype data
    - yfinance: research-grade market data via yfinance
    """
    provider = os.getenv("MARKET_DATA_PROVIDER", "mock").lower().strip()

    if provider == "yfinance":
        return YFinanceProvider()

    return MockMarketDataProvider()
