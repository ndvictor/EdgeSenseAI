from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.services.market_regime_service import MarketRegimeResponse, RegimeFactor


class MarketRegimeProvider(Protocol):
    provider_name: str

    def build_regime(self) -> MarketRegimeResponse:
        ...


class StaticPrototypeRegimeProvider:
    provider_name = "static_prototype"

    def build_regime(self) -> MarketRegimeResponse:
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
                "Prototype regime data. This is hard-coded/static, not real market data yet.",
                "Replace with VIX, breadth, SPY/QQQ trend, sector ETF, yields, DXY, and BTC liquidity inputs before treating regime as source-backed.",
                "Regime should gate strategy selection before recommendations are promoted.",
            ],
            data_source="hardcoded_prototype",
            source_type="static_placeholder",
            source_detail="StaticPrototypeRegimeProvider returns static prototype values. No live provider data is used.",
            provider="none",
            model_used="none",
            llm_used="none",
            agent_used="none",
            calculation_engine="static_rule_placeholder",
            real_data_used=False,
            generated_at=datetime.now(timezone.utc),
        )


class MockRegimeProvider:
    provider_name = "mock_regime"

    def build_regime(self) -> MarketRegimeResponse:
        response = StaticPrototypeRegimeProvider().build_regime()
        response.data_source = "mock"
        response.source_type = "mock"
        response.source_detail = "MockRegimeProvider uses controlled test values for UI/API development only."
        response.provider = "mock"
        response.real_data_used = False
        return response


class SourceBackedRegimeProvider:
    provider_name = "source_backed_regime"

    def build_regime(self) -> MarketRegimeResponse:
        response = StaticPrototypeRegimeProvider().build_regime()
        response.data_source = "placeholder"
        response.source_type = "not_implemented"
        response.source_detail = "SourceBackedRegimeProvider is a boundary for future real VIX/breadth/SPY/QQQ/DXY/yields inputs. It is not wired yet."
        response.provider = "not_configured"
        response.real_data_used = False
        response.notes = [
            "Source-backed market regime provider is not configured yet.",
            "Do not treat this as live regime intelligence until provider inputs are wired and validated.",
        ]
        return response


def get_market_regime_provider(source_type: str = "static_prototype") -> MarketRegimeProvider:
    if source_type == "mock":
        return MockRegimeProvider()
    if source_type in {"source_backed", "real"}:
        return SourceBackedRegimeProvider()
    return StaticPrototypeRegimeProvider()
