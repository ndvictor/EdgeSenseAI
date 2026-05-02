from app.data_providers.base import MarketSnapshot


class ProviderNotConfiguredError(RuntimeError):
    pass


class PolygonProvider:
    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        raise ProviderNotConfiguredError("Polygon provider is not configured. Add API key and adapter implementation.")

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        raise ProviderNotConfiguredError("Polygon provider is not configured. Add API key and adapter implementation.")


class AlpacaProvider:
    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        raise ProviderNotConfiguredError("Alpaca provider is not configured. Add API key and adapter implementation.")

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        raise ProviderNotConfiguredError("Alpaca provider is not configured. Add API key and adapter implementation.")


class TradierOptionsProvider:
    def get_options_chain(self, symbol: str) -> dict:
        raise ProviderNotConfiguredError("Tradier options provider is not configured. Add API key and options-chain adapter.")


class CryptoProvider:
    def get_snapshot(self, symbol: str, asset_class: str = "crypto") -> MarketSnapshot:
        raise ProviderNotConfiguredError("Crypto provider is not configured. Add exchange API adapter implementation.")

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        raise ProviderNotConfiguredError("Crypto provider is not configured. Add exchange API adapter implementation.")
