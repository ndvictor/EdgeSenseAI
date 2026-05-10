from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

import requests
from pydantic import BaseModel, ConfigDict, Field

from app.core.settings import settings
from app.services.market_condition_scanner_service import _session_state, _spread_bps
from app.services.market_data_service import MarketDataService
from app.services.worker_output_store import get_latest_feature_rows_for_production_discovery


class NormalizedScannerFeatureRow(BaseModel):
    """Normalized, source-attributed feature row used by the real scanner.

    The scanner treats `hard_blockers` as reject reasons and `soft_warnings` as
    display/diagnostic hints only.
    """

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    provider_primary: str | None = None
    provider_chain: list[str] = Field(default_factory=list)

    last_price: float | None = None
    volume: float | None = None
    avg_volume: float | None = None
    relative_volume: float | None = None
    spread_bps: float | None = None
    dollar_volume: float | None = None
    vwap: float | None = None
    rsi: float | None = None
    macd_signal: str | None = None

    data_quality: str = "unavailable"
    feature_quality: str = "missing"
    field_sources: dict[str, str] = Field(default_factory=dict)
    hard_blockers: list[str] = Field(default_factory=list)
    soft_warnings: list[str] = Field(default_factory=list)

    relative_volume_status: str = "unavailable"
    spread_status: str = "unavailable"


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class _AlphaVantageIndicators:
    rsi: float | None
    macd_signal: str | None
    field_sources: dict[str, str]
    soft_warnings: list[str]


class FeatureEnrichmentService:
    """Enrich raw provider snapshots into normalized scanner feature rows.

    Ownership boundary:
    - Scanner calls this service once per batch.
    - This service owns provider priority, missing-field handling, and source attribution.
    """

    def __init__(
        self,
        *,
        market_data: MarketDataService | None = None,
        feature_row_source: Callable[[int], list[dict[str, Any]]] | None = None,
        http_get: Callable[..., Any] | None = None,
    ) -> None:
        self._market_data = market_data or MarketDataService()
        self._feature_row_source = feature_row_source or (lambda limit: get_latest_feature_rows_for_production_discovery(limit))
        self._http_get = http_get or requests.get

    def enrich(
        self,
        symbols: list[str],
        *,
        requested_source: str = "auto",
        strategy_key: str = "stock_day_trading",
        max_candidates: int = 25,
    ) -> list[NormalizedScannerFeatureRow]:
        clean: list[str] = []
        seen: set[str] = set()
        for raw in symbols or []:
            sym = str(raw or "").strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            clean.append(sym)
            if len(clean) >= max_candidates:
                break

        feature_rows = self._index_feature_rows(limit=max(len(clean) * 4, 50))
        out: list[NormalizedScannerFeatureRow] = []
        for symbol in clean:
            out.append(self._enrich_one(symbol, requested_source=requested_source, strategy_key=strategy_key, feature_rows=feature_rows))
        return out

    def _index_feature_rows(self, *, limit: int) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for row in self._feature_row_source(limit) or []:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
            if not symbol:
                continue
            if symbol not in indexed:
                indexed[symbol] = dict(row)
        return indexed

    def _provider_chain(self, requested_source: str) -> list[str]:
        # Contract priority order (scanner calls with explicit requested_source when needed).
        base = ["alpaca", "polygon", "feature_store", "alpha_vantage"]
        req = (requested_source or "auto").lower().strip()
        if req in {"alpaca", "polygon"}:
            return [req] + [p for p in base if p != req]
        if req in {"auto", "runtime", "manual", "candidate"}:
            return base
        # Unknown explicit source: still attempt it first (if MarketDataService supports it), then contract defaults.
        return [req] + [p for p in base if p != req]

    def _enrich_one(
        self,
        symbol: str,
        *,
        requested_source: str,
        strategy_key: str,
        feature_rows: dict[str, dict[str, Any]],
    ) -> NormalizedScannerFeatureRow:
        chain = self._provider_chain(requested_source)
        field_sources: dict[str, str] = {}
        hard: list[str] = []
        soft: list[str] = []

        # Primary snapshot (Alpaca/Polygon/YFinance via MarketDataService provider priority).
        primary_snapshot = self._market_data.get_market_snapshot(symbol, source=requested_source)
        provider_primary = str(primary_snapshot.get("provider") or chain[0] or "unknown") if primary_snapshot else (chain[0] if chain else None)

        data_quality = str(primary_snapshot.get("data_quality") or "unavailable").lower()
        is_non_real = bool(primary_snapshot.get("is_non_real") or primary_snapshot.get("non_real") or primary_snapshot.get("using_non_real_data"))
        is_synth = bool(primary_snapshot.get("synthetic") or primary_snapshot.get("synthetic_data_used") or primary_snapshot.get("spread_synthetic"))
        if is_non_real:
            hard.append("non_real_data")
        if is_synth:
            hard.append("synthetic_data")
        if data_quality == "stale" or primary_snapshot.get("stale_data") or primary_snapshot.get("is_stale"):
            hard.append("stale_data")
        if not primary_snapshot.get("provider") or data_quality in {"unavailable", "not_configured"}:
            hard.append("provider_unavailable")

        last_price = _float_or_none(primary_snapshot.get("price") or primary_snapshot.get("current_price") or primary_snapshot.get("last_price"))
        if last_price is not None:
            field_sources["last_price"] = str(primary_snapshot.get("provider") or provider_primary)
        volume = _float_or_none(primary_snapshot.get("volume"))
        if volume is not None:
            field_sources["volume"] = str(primary_snapshot.get("provider") or provider_primary)
        vwap = _float_or_none(primary_snapshot.get("vwap"))
        if vwap is not None:
            field_sources["vwap"] = str(primary_snapshot.get("provider") or provider_primary)

        avg_volume = _float_or_none(primary_snapshot.get("average_volume") or primary_snapshot.get("avg_volume"))
        if avg_volume is not None:
            field_sources["avg_volume"] = str(primary_snapshot.get("provider") or provider_primary)

        spread_bps = _spread_bps(primary_snapshot, last_price)
        spread_status = "unavailable"
        session_state = _session_state(primary_snapshot)
        max_spread_bps = _env_float("SCANNER_MAX_SPREAD_BPS", 35.0)
        if spread_bps is None:
            # Wide/missing spreads can be normal outside regular session.
            spread_status = "unavailable"
            if session_state in {"regular", "market_open", "open"}:
                soft.append("spread_unavailable")
            else:
                soft.append("spread_unavailable_closed_market")
        else:
            field_sources["spread_bps"] = str(primary_snapshot.get("provider") or provider_primary)
            if spread_bps > max_spread_bps:
                spread_status = "too_wide"
                if session_state in {"regular", "market_open", "open"}:
                    hard.append("spread_too_wide")
                else:
                    soft.append("spread_too_wide_closed_market")
            else:
                spread_status = "ok"

        # Fill avg_volume from Polygon if missing.
        if avg_volume is None:
            poly_snapshot = self._market_data.get_market_snapshot(symbol, source="polygon")
            poly_avg = _float_or_none(poly_snapshot.get("average_volume") or poly_snapshot.get("avg_volume"))
            if poly_avg is not None and poly_snapshot.get("data_quality") not in {"unavailable", "not_configured"}:
                avg_volume = poly_avg
                field_sources["avg_volume"] = "polygon"

        # Fill avg_volume from feature store (worker feature rows) if still missing.
        if avg_volume is None:
            fs = feature_rows.get(symbol)
            if isinstance(fs, dict):
                fs_avg = _float_or_none(fs.get("avg_volume") or fs.get("average_volume"))
                if fs_avg is not None:
                    avg_volume = fs_avg
                    field_sources["avg_volume"] = "feature_store"

        # Relative volume: prefer provider-provided, else compute.
        rel = _float_or_none(primary_snapshot.get("relative_volume"))
        relative_volume_status = "unavailable"
        if rel is not None:
            relative_volume_status = "provided"
            field_sources["relative_volume"] = str(primary_snapshot.get("provider") or provider_primary)
        elif volume is not None and avg_volume is not None and avg_volume > 0:
            rel = float(volume) / float(avg_volume)
            relative_volume_status = "computed"
            field_sources["relative_volume"] = "computed"
        else:
            soft.append("relative_volume_unavailable")

        # Derived dollar volume.
        dollar_volume = None
        if last_price is not None and volume is not None:
            dollar_volume = float(last_price) * float(volume)
            field_sources["dollar_volume"] = "computed"

        # Hard safety thresholds (configurable). Price level is not a gate; feasibility/sizing decides tradability.
        min_dollar_volume = _env_float("SCANNER_MIN_DOLLAR_VOLUME", 1_000_000.0)
        if last_price is None or last_price <= 0:
            hard.append("missing_price")
        if volume is None or volume <= 0:
            hard.append("missing_volume")
        if dollar_volume is None or dollar_volume < min_dollar_volume:
            hard.append("dollar_volume_too_low")

        # Technical indicators (optional enrichment only).
        indicators = self._alpha_vantage_indicators(symbol)
        if indicators.rsi is not None:
            field_sources.update(indicators.field_sources)
        if indicators.soft_warnings:
            soft.extend(indicators.soft_warnings)

        # Feature quality.
        present = {
            "price": last_price is not None,
            "volume": volume is not None,
            "avg_volume": avg_volume is not None,
            "relative_volume": rel is not None,
            "spread": spread_bps is not None,
        }
        if present["price"] and present["volume"] and present["avg_volume"] and present["relative_volume"]:
            feature_quality = "full"
        elif present["price"] and present["volume"]:
            feature_quality = "partial"
        else:
            feature_quality = "missing"

        # Provider chain used (include only the contract chain; primary snapshot provider may differ).
        provider_chain = list(chain)
        if provider_primary and provider_primary not in provider_chain:
            provider_chain.insert(0, provider_primary)

        return NormalizedScannerFeatureRow(
            symbol=symbol,
            provider_primary=provider_primary,
            provider_chain=provider_chain,
            last_price=last_price,
            volume=volume,
            avg_volume=avg_volume,
            relative_volume=rel,
            spread_bps=spread_bps,
            dollar_volume=dollar_volume,
            vwap=vwap,
            rsi=indicators.rsi,
            macd_signal=indicators.macd_signal,
            data_quality="real" if (not is_non_real and not is_synth and data_quality == "real") else (data_quality or "unavailable"),
            feature_quality=feature_quality,
            field_sources=field_sources,
            hard_blockers=sorted(set(hard)),
            soft_warnings=sorted(set(soft)),
            relative_volume_status=relative_volume_status,
            spread_status=spread_status,
        )

    def _alpha_vantage_indicators(self, symbol: str) -> _AlphaVantageIndicators:
        # Optional enrichment only. No fake fallbacks.
        key = (settings.alpha_vantage_key or "").strip()
        if not key:
            return _AlphaVantageIndicators(rsi=None, macd_signal=None, field_sources={}, soft_warnings=[])
        try:
            rsi = self._fetch_alpha_vantage_rsi(symbol, api_key=key)
            macd_signal = self._fetch_alpha_vantage_macd_signal(symbol, api_key=key)
            sources: dict[str, str] = {}
            if rsi is not None:
                sources["rsi"] = "alpha_vantage"
            if macd_signal is not None:
                sources["macd_signal"] = "alpha_vantage"
            return _AlphaVantageIndicators(rsi=rsi, macd_signal=macd_signal, field_sources=sources, soft_warnings=[])
        except Exception:
            # Keep enrichment failures non-fatal.
            return _AlphaVantageIndicators(rsi=None, macd_signal=None, field_sources={}, soft_warnings=["alpha_vantage_unavailable"])

    def _fetch_alpha_vantage_rsi(self, symbol: str, *, api_key: str) -> float | None:
        resp = self._http_get(
            "https://www.alphavantage.co/query",
            params={
                "function": "RSI",
                "symbol": symbol.upper(),
                "interval": "daily",
                "time_period": "14",
                "series_type": "close",
                "apikey": api_key,
            },
            timeout=10,
        )
        payload = resp.json() if hasattr(resp, "json") else {}
        series = payload.get("Technical Analysis: RSI") or {}
        if not isinstance(series, dict) or not series:
            return None
        latest_key = sorted(series.keys())[-1]
        point = series.get(latest_key) or {}
        return _float_or_none(point.get("RSI"))

    def _fetch_alpha_vantage_macd_signal(self, symbol: str, *, api_key: str) -> str | None:
        resp = self._http_get(
            "https://www.alphavantage.co/query",
            params={
                "function": "MACD",
                "symbol": symbol.upper(),
                "interval": "daily",
                "series_type": "close",
                "apikey": api_key,
            },
            timeout=10,
        )
        payload = resp.json() if hasattr(resp, "json") else {}
        series = payload.get("Technical Analysis: MACD") or {}
        if not isinstance(series, dict) or not series:
            return None
        latest_key = sorted(series.keys())[-1]
        point = series.get(latest_key) or {}
        macd = _float_or_none(point.get("MACD"))
        signal = _float_or_none(point.get("MACD_Signal"))
        if macd is None or signal is None:
            return None
        if macd > signal:
            return "bullish"
        if macd < signal:
            return "bearish"
        return "neutral"

