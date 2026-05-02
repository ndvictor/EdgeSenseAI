from typing import Protocol
from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    symbol: str
    asset_class: str
    current_price: float
    previous_close: float
    day_change_percent: float
    volume: int
    relative_volume: float
    bid: float
    ask: float
    spread_percent: float
    vwap: float
    volatility_proxy: float
    data_mode: str = "synthetic_prototype"


class MarketDataProvider(Protocol):
    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        """Return a normalized market snapshot for a symbol."""
        ...

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        """Return normalized snapshots for the current prototype watchlist."""
        ...
