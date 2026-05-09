from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import app.services.agent_runtime.wrappers.data_readiness_adapter as adapter


def _fake_resp(
    symbol: str,
    *,
    price: float | None = 100.0,
    quality: str = "pass",
    provider: str = "yfinance",
    is_mock: bool = False,
    warnings: list[str] | None = None,
    blockers: list[str] | None = None,
    provider_statuses: list[dict[str, Any]] | None = None,
):
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(id=f"fs_{symbol}", ticker=symbol, data_quality=quality)
    snap = SimpleNamespace(
        timestamp=now,
        price=price,
        volume=123456,
        change_percent=1.2,
        relative_volume=1.1,
        spread_percent=0.01,
        provider=provider,
        is_mock=is_mock,
        data_quality="mock" if is_mock else "real",
    )
    report = SimpleNamespace(
        quality_status=quality,
        freshness_status="fresh",
        blockers=blockers or [],
        warnings=warnings or [],
    )
    return SimpleNamespace(
        row=row,
        normalized_snapshot=snap,
        quality_report=report,
        storage_mode="in_memory",
        warnings=warnings or [],
        provider_statuses=provider_statuses or [{"provider": provider, "data_quality": "real", "error": None}],
    )


def test_kafka_and_qlib_do_not_block_dry_run_data_readiness(monkeypatch):
    monkeypatch.setattr(adapter, "run_feature_store_pipeline", lambda req: _fake_resp(req.symbol))
    monkeypatch.setattr(adapter, "get_feature_row_persistence_status", lambda _row_id: {"persisted": False, "data_source": "in_memory_fallback"})

    out = adapter.evaluate_data_readiness(symbols=["AMD"], asset_class="stock", horizon="day_trading", source="runtime")

    assert out["decision"] in {"data_ready", "degraded"}
    assert out["kafka_status"] == "configured_optional_not_active"
    assert "no_usable_symbols" not in out["blockers"]
    assert out["artifacts"]["qlib_status"] == "optional_not_checked"


def test_provider_throttling_returns_degraded_warning_not_crash(monkeypatch):
    def fake_pipeline(req):
        return _fake_resp(
            req.symbol,
            quality="warn",
            provider="polygon",
            warnings=["delayed provider response"],
            provider_statuses=[
                {"provider": "yfinance", "data_quality": "unavailable", "error": "HTTP 429 throttled"},
                {"provider": "polygon", "data_quality": "real", "error": None},
            ],
        )

    monkeypatch.setattr(adapter, "run_feature_store_pipeline", fake_pipeline)
    monkeypatch.setattr(adapter, "get_feature_row_persistence_status", lambda _row_id: {"persisted": False, "data_source": "in_memory_fallback"})

    out = adapter.evaluate_data_readiness(symbols=["AMD"], asset_class="stock", horizon="day_trading", source="runtime")

    assert out["decision"] == "degraded"
    assert out["usable_symbols"] == ["AMD"]
    assert any("HTTP 429" in warning or "fallback used" in warning for warning in out["warnings"])


def test_no_usable_symbols_blocks_workflow_data_readiness(monkeypatch):
    monkeypatch.setattr(
        adapter,
        "run_feature_store_pipeline",
        lambda req: _fake_resp(req.symbol, price=None, quality="fail", provider="unknown", blockers=["Price is required for feature generation and model routing."]),
    )

    out = adapter.evaluate_data_readiness(symbols=["AMD"], asset_class="stock", horizon="day_trading", source="runtime")

    assert out["decision"] == "blocked"
    assert "no_usable_symbols" in out["blockers"]
    assert out["latest_snapshot_count"] == 0


def test_partial_usable_symbols_degrades_but_continues(monkeypatch):
    def fake_pipeline(req):
        if req.symbol == "AMD":
            return _fake_resp("AMD")
        return _fake_resp(req.symbol, price=None, quality="fail", blockers=["missing price"])

    monkeypatch.setattr(adapter, "run_feature_store_pipeline", fake_pipeline)
    monkeypatch.setattr(adapter, "get_feature_row_persistence_status", lambda _row_id: {"persisted": False, "data_source": "in_memory_fallback"})

    out = adapter.evaluate_data_readiness(symbols=["AMD", "MSFT"], asset_class="stock", horizon="day_trading", source="runtime")

    assert out["decision"] == "degraded"
    assert out["usable_symbols"] == ["AMD"]
    assert out["rejected_symbols"] == ["MSFT"]


def test_runtime_source_is_preserved_and_mock_source_is_explicit(monkeypatch):
    monkeypatch.setattr(adapter, "run_feature_store_pipeline", lambda req: _fake_resp(req.symbol, is_mock=req.source == "mock", provider=req.source))
    monkeypatch.setattr(adapter, "get_feature_row_persistence_status", lambda _row_id: {"persisted": False, "data_source": "in_memory_fallback"})

    runtime = adapter.evaluate_data_readiness(symbols=["AMD"], asset_class="stock", horizon="day_trading", source="runtime")
    mock = adapter.evaluate_data_readiness(symbols=["AMD"], asset_class="stock", horizon="day_trading", source="mock")

    assert runtime["source_mode"] == "runtime"
    assert runtime["using_mock_data"] is False
    assert mock["source_mode"] == "mock"
    assert mock["using_mock_data"] is True


def test_data_readiness_output_includes_required_status_fields(monkeypatch):
    monkeypatch.setattr(adapter, "run_feature_store_pipeline", lambda req: _fake_resp(req.symbol))
    monkeypatch.setattr(adapter, "get_feature_row_persistence_status", lambda _row_id: {"persisted": True, "data_source": "postgres"})

    out = adapter.evaluate_data_readiness(symbols=["AMD"], asset_class="stock", horizon="day_trading", source="runtime")

    for key in ["provider_status", "feature_store_status", "persistence_status", "freshness_status", "kafka_status"]:
        assert key in out
    assert out["feature_row_count"] == 1
    assert out["latest_snapshot_count"] == 1
