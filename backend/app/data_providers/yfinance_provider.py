from __future__ import annotations

from app.data_providers.base import MarketSnapshot


class YFinanceProvider:
    """Live-ish market data adapter using yfinance.

    yfinance is suitable for prototype research workflows and UI validation. It should not be treated as an institutional low-latency market data source.
    """

    default_symbols = ["AMD", "NVDA", "BTC-USD"]

    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval="1d")
        fast = ticker.fast_info

        if hist.empty:
            raise ValueError(f"No market data returned for {symbol}")

        current_price = float(fast.get("last_price") or hist["Close"].iloc[-1])
        previous_close = float(fast.get("previous_close") or hist["Close"].iloc[-2] if len(hist) > 1 else hist["Close"].iloc[-1])
        volume = int(hist["Volume"].iloc[-1]) if "Volume" in hist else 0
        avg_volume = float(hist["Volume"].tail(5).mean()) if "Volume" in hist and volume else max(volume, 1)
        bid = float(fast.get("bid") or current_price)
        ask = float(fast.get("ask") or current_price)
        spread_percent = abs(ask - bid) / current_price * 100 if current_price else 0
        day_change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close else 0
        vwap = float(((hist["High"].iloc[-1] + hist["Low"].iloc[-1] + hist["Close"].iloc[-1]) / 3))
        volatility_proxy = float(hist["Close"].pct_change().tail(5).std() or 0) * 10

        return MarketSnapshot(
            symbol=symbol,
            asset_class=asset_class,
            current_price=round(current_price, 2),
            previous_close=round(previous_close, 2),
            day_change_percent=round(day_change_percent, 2),
            volume=volume,
            relative_volume=round(volume / avg_volume, 2) if avg_volume else 1,
            bid=round(bid, 2),
            ask=round(ask, 2),
            spread_percent=round(spread_percent, 3),
            vwap=round(vwap, 2),
            volatility_proxy=round(volatility_proxy, 3),
            data_mode="yfinance_research",
        )

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        snapshots: list[MarketSnapshot] = []
        for symbol in self.default_symbols:
            asset_class = "crypto" if "-USD" in symbol else "stock"
            try:
                snapshots.append(self.get_snapshot(symbol, asset_class))
            except Exception:
                continue
        return snapshots
