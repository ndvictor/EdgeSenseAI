from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.services.market_regime_service import MarketRegimeResponse


class MarketRegimeProvider(Protocol):
    provider_name: str

    def build_regime(self) -> MarketRegimeResponse:
        ...


class UnavailableRegimeProvider:
    provider_name = "not_configured"

    def build_regime(self) -> MarketRegimeResponse:
        return MarketRegimeResponse(
            regime_state="unavailable",
            confidence=0.0,
            strategy_bias="unavailable",
            allowed_strategies=[],
            blocked_strategies=[],
            factors=[],
            notes=[
                "Source-backed market regime provider is not configured.",
                "No market regime values are fabricated.",
            ],
            data_source="source_unavailable",
            source_type="not_configured",
            source_detail="Market regime provider inputs are not configured.",
            provider="not_configured",
            model_used="none",
            llm_used="none",
            agent_used="none",
            calculation_engine="not_configured",
            real_data_used=False,
            generated_at=datetime.now(timezone.utc),
        )


class SourceBackedRegimeProvider:
    provider_name = "source_backed_regime"

    def build_regime(self) -> MarketRegimeResponse:
        response = UnavailableRegimeProvider().build_regime()
        response.data_source = "source_unavailable"
        response.source_type = "not_configured"
        response.source_detail = "SourceBackedRegimeProvider is a boundary for future real VIX/breadth/SPY/QQQ/DXY/yields inputs. It is not wired yet."
        response.provider = "not_configured"
        response.real_data_used = False
        response.notes = [
            "Source-backed market regime provider is not configured yet.",
            "Do not treat this as live regime intelligence until provider inputs are wired and validated.",
        ]
        return response


def get_market_regime_provider(source_type: str = "source_backed") -> MarketRegimeProvider:
    if source_type in {"source_backed", "real"}:
        return SourceBackedRegimeProvider()
    return UnavailableRegimeProvider()
