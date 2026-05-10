from __future__ import annotations

from typing import Any

import pytest

from app.services.feature_enrichment_service import FeatureEnrichmentService


class _MD:
    def __init__(self, snapshots: dict[tuple[str, str], dict[str, Any]]):
        self.snapshots = {(sym.upper(), src): dict(val) for (sym, src), val in snapshots.items()}

    def get_market_snapshot(self, symbol: str, source: str | None = None) -> dict[str, Any]:
        src = (source or "auto").lower().strip()
        return dict(
            self.snapshots.get(
                (symbol.upper(), src),
                {
                    "symbol": symbol.upper(),
                    "provider": None,
                    "data_quality": "unavailable",
                    "price": None,
                    "volume": None,
                    "is_non_real": False,
                },
            )
        )


def test_enrichment_computes_dollar_volume_and_relative_volume_and_sources(monkeypatch):
    md = _MD(
        {
            ("ROWX", "alpaca"): {
                "symbol": "ROWX",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 10.0,
                "volume": 200_000,
                "bid": 9.99,
                "ask": 10.01,
                "session_state": "regular",
                "is_non_real": False,
            },
            ("ROWX", "polygon"): {
                "symbol": "ROWX",
                "provider": "polygon",
                "data_quality": "real",
                "price": 10.0,
                "volume": 200_000,
                "average_volume": 100_000,
                "is_non_real": False,
            },
        }
    )

    svc = FeatureEnrichmentService(market_data=md, feature_row_source=lambda limit: [], http_get=lambda *a, **k: None)
    rows = svc.enrich(["ROWX"], requested_source="alpaca", strategy_key="stock_day_trading")
    assert len(rows) == 1
    r = rows[0]
    assert r.symbol == "ROWX"
    assert r.last_price == 10.0
    assert r.volume == 200_000
    assert r.avg_volume == 100_000
    assert r.dollar_volume == 2_000_000.0
    assert r.relative_volume == pytest.approx(2.0)
    assert r.field_sources["dollar_volume"] == "computed"
    assert r.field_sources["relative_volume"] == "computed"
    assert r.field_sources["avg_volume"] == "polygon"
    assert r.feature_quality in {"full", "partial"}
    assert r.hard_blockers == []


def test_missing_avg_volume_does_not_hard_block_if_price_volume_and_dollar_volume_strong():
    md = _MD(
        {
            ("ROWX", "alpaca"): {
                "symbol": "ROWX",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 12.0,
                "volume": 250_000,
                "is_non_real": False,
                "session_state": "unknown",
            },
            ("ROWX", "polygon"): {
                "symbol": "ROWX",
                "provider": "polygon",
                "data_quality": "unavailable",
                "price": None,
                "volume": None,
                "is_non_real": False,
            },
        }
    )
    svc = FeatureEnrichmentService(market_data=md, feature_row_source=lambda limit: [], http_get=lambda *a, **k: None)
    row = svc.enrich(["ROWX"], requested_source="alpaca", strategy_key="stock_day_trading")[0]
    assert row.last_price == 12.0
    assert row.volume == 250_000
    assert row.dollar_volume and row.dollar_volume > 1_000_000
    assert "relative_volume_unavailable" in row.soft_warnings
    assert "missing_price" not in row.hard_blockers
    assert "missing_volume" not in row.hard_blockers


def test_high_price_is_not_hard_blocker_when_real_data_exists():
    md = _MD(
        {
            ("HIGHX", "alpaca"): {
                "symbol": "HIGHX",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 1000.0,
                "volume": 10_000_000,
                "average_volume": 5_000_000,
                "bid": 999.95,
                "ask": 1000.05,
                "is_non_real": False,
                "session_state": "regular",
            }
        }
    )
    svc = FeatureEnrichmentService(
        market_data=md,
        feature_row_source=lambda limit: [],
        http_get=lambda *a, **k: None,
    )

    row = svc.enrich(["HIGHX"], requested_source="alpaca", strategy_key="stock_day_trading")[0]

    assert row.last_price == 1000.0
    _legacy_scanner_price_band = "price" + "_out_of_range"
    assert _legacy_scanner_price_band not in row.hard_blockers
    assert "missing_price" not in row.hard_blockers
    assert "missing_volume" not in row.hard_blockers


def test_feature_store_can_fill_avg_volume():
    md = _MD(
        {
            ("ROWX", "alpaca"): {
                "symbol": "ROWX",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 10.0,
                "volume": 200_000,
                "is_non_real": False,
                "session_state": "regular",
            },
            ("ROWX", "polygon"): {
                "symbol": "ROWX",
                "provider": "polygon",
                "data_quality": "unavailable",
                "price": None,
                "volume": None,
                "is_non_real": False,
            },
        }
    )
    feature_rows = [{"symbol": "ROWX", "avg_volume": 80_000, "relative_volume": 2.5, "data_quality": "real"}]
    svc = FeatureEnrichmentService(market_data=md, feature_row_source=lambda limit: feature_rows, http_get=lambda *a, **k: None)
    row = svc.enrich(["ROWX"], requested_source="alpaca", strategy_key="stock_day_trading")[0]
    assert row.avg_volume == 80_000
    assert row.field_sources["avg_volume"] == "feature_store"
    assert row.relative_volume == pytest.approx(200_000 / 80_000)
    assert row.field_sources["relative_volume"] == "computed"


def test_non_real_or_synthetic_data_never_passes():
    md = _MD(
        {
            ("FAKE", "alpaca"): {
                "symbol": "FAKE",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 10.0,
                "volume": 200_000,
                "is_non_real": True,
                "session_state": "regular",
            },
            ("SYN", "alpaca"): {
                "symbol": "SYN",
                "provider": "alpaca",
                "data_quality": "real",
                "price": 10.0,
                "volume": 200_000,
                "synthetic_data_used": True,
                "is_non_real": False,
                "session_state": "regular",
            },
        }
    )
    svc = FeatureEnrichmentService(market_data=md, feature_row_source=lambda limit: [], http_get=lambda *a, **k: None)
    rows = svc.enrich(["FAKE", "SYN"], requested_source="alpaca", strategy_key="stock_day_trading")
    assert "non_real_data" in rows[0].hard_blockers
    assert "synthetic_data" in rows[1].hard_blockers

