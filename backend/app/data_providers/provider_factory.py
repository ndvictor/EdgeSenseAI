from app.data_providers.mock_provider import MockMarketDataProvider


def get_market_data_provider() -> MockMarketDataProvider:
    """Return the active provider.

    The platform uses the mock provider until Polygon/Alpaca/Tradier/Crypto providers are configured.
    """
    return MockMarketDataProvider()
