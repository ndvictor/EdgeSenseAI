from pydantic import BaseModel


class RegimeFactor(BaseModel):
    name: str
    value: str
    signal: str
    impact: str


class MarketRegimeResponse(BaseModel):
    regime_state: str
    confidence: float
    strategy_bias: str
    allowed_strategies: list[str]
    blocked_strategies: list[str]
    factors: list[RegimeFactor]
    notes: list[str]


def build_market_regime() -> MarketRegimeResponse:
    return MarketRegimeResponse(
        regime_state="risk_on_momentum",
        confidence=0.72,
        strategy_bias="favor_breakout_and_pullback_entries",
        allowed_strategies=[
            "RVOL breakout",
            "trend pullback",
            "defined-risk bullish option spread",
            "fractional spot crypto trend trade",
        ],
        blocked_strategies=[
            "wide-spread options",
            "low-liquidity breakouts without confirmation",
            "mean reversion against strong trend",
        ],
        factors=[
            RegimeFactor(name="SPY trend", value="above VWAP / positive slope", signal="risk_on", impact="supports long setups"),
            RegimeFactor(name="QQQ momentum", value="positive intraday breadth", signal="growth_bid", impact="supports semiconductor candidates"),
            RegimeFactor(name="Volatility proxy", value="moderate", signal="tradable", impact="stops can be sized normally"),
            RegimeFactor(name="BTC correlation", value="risk-on alignment", signal="crypto_supportive", impact="crypto watchlist allowed but risk reviewed"),
        ],
        notes=[
            "Prototype regime data. Replace with VIX, breadth, SPY/QQQ trend, sector ETF, and BTC liquidity inputs.",
            "Regime should gate strategy selection before recommendations are promoted.",
        ],
    )
