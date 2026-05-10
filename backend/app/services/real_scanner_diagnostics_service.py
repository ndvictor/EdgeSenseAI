from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.effective_runtime import effective_str
from app.services.market_condition_scanner_service import _relative_volume, _session_state, _spread_bps
from app.services.feature_enrichment_service import FeatureEnrichmentService, NormalizedScannerFeatureRow
from app.services.market_data_service import MarketDataService


REJECTION_REASONS = (
    "missing_price",
    "missing_volume",
    "missing_spread",
    "spread_too_wide",
    "dollar_volume_too_low",
    "market_closed",
    "provider_unavailable",
    "stale_data",
    "non_real_data",
    "synthetic_data",
)

_ALLOWED_SCAN_SESSIONS = {"regular", "market_open", "open", "premarket", "unknown"}
_MARKET_DATA = MarketDataService()
_ENRICH = FeatureEnrichmentService()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_symbols(symbols: list[str] | None, max_candidates: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in symbols or []:
        symbol = str(raw or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(symbol)
        if len(out) >= max_candidates:
            break
    return out


def _priority_for_source(source: str) -> list[str]:
    try:
        return list(_MARKET_DATA._priority_for_source(source))  # noqa: SLF001 - diagnostics must match runtime provider order.
    except Exception:
        return []


def _provider_configured(provider_name: str | None) -> bool:
    if not provider_name:
        return False
    provider = _MARKET_DATA.providers.get(provider_name)
    if provider is None:
        return False
    configured = getattr(provider, "is_configured", None)
    if callable(configured):
        try:
            return bool(configured())
        except Exception:
            return False
    return True


def _alpaca_feed() -> str | None:
    raw = (effective_str("ALPACA_MARKET_DATA_FEED") or effective_str("ALPACA_DATA_FEED") or "iex").lower().strip()
    return "sip" if raw == "sip" else "iex"


def _price(snapshot: dict[str, Any]) -> float | None:
    return _float_or_none(snapshot.get("price") or snapshot.get("current_price") or snapshot.get("last_price"))


def _volume(snapshot: dict[str, Any]) -> float | None:
    return _float_or_none(snapshot.get("volume"))


def _has_provider_data(snapshot: dict[str, Any]) -> bool:
    if snapshot.get("is_non_real") or snapshot.get("synthetic") or snapshot.get("synthetic_data_used"):
        return False
    return bool(snapshot.get("provider") and snapshot.get("data_quality") not in {"unavailable", "not_configured"})


def _fallback_details(snapshot: dict[str, Any], priority: list[str], actual_provider: str | None) -> tuple[str | None, str | None]:
    if not priority or not actual_provider or actual_provider == priority[0]:
        return None, None
    statuses = snapshot.get("provider_statuses") or []
    for status in statuses:
        if status.get("provider") == priority[0]:
            reason = status.get("error") or status.get("data_quality") or "primary_provider_unavailable"
            return actual_provider, str(reason)
    return actual_provider, "primary_provider_unavailable"


def _merge_fallback_details(
    current_provider: str | None,
    current_reason: str | None,
    snapshot: dict[str, Any],
    priority: list[str],
) -> tuple[str | None, str | None]:
    provider, reason = _fallback_details(snapshot, priority, snapshot.get("provider"))
    if provider:
        return provider, reason
    return current_provider, current_reason


def _evaluate_symbol(symbol: str, snapshot: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    price = _price(snapshot)
    volume = _volume(snapshot)
    relative_volume = _float_or_none(_relative_volume(snapshot))
    spread_bps = _spread_bps(snapshot, price)
    session_state = _session_state(snapshot)
    data_quality = str(snapshot.get("data_quality") or "").lower()
    reasons: list[str] = []

    if not _has_provider_data(snapshot):
        reasons.append("provider_unavailable")
    if data_quality == "stale" or snapshot.get("stale_data") or snapshot.get("is_stale"):
        reasons.append("stale_data")
    if price is None or price <= 0:
        reasons.append("missing_price")
    if volume is None or volume <= 0:
        reasons.append("missing_volume")
    if relative_volume is None:
        reasons.append("missing_relative_volume")
    elif relative_volume < 1.5:
        reasons.append("relative_volume_too_low")
    if spread_bps is None:
        reasons.append("missing_spread")
    elif spread_bps > 35.0:
        reasons.append("spread_too_wide")
    if price is not None and volume is not None and price * volume < 1_000_000:
        reasons.append("dollar_volume_too_low")
    if session_state not in _ALLOWED_SCAN_SESSIONS:
        reasons.append("market_closed")

    metrics = {
        "symbol": symbol,
        "last_price": price,
        "volume": volume,
        "avg_volume": _float_or_none(snapshot.get("average_volume") or snapshot.get("avg_volume")),
        "relative_volume": relative_volume,
        "spread_bps": spread_bps,
        "session_state": session_state,
        "dollar_volume": None if price is None or volume is None else price * volume,
        "provider_name": snapshot.get("provider"),
        "data_quality": snapshot.get("data_quality"),
        "rejection_reasons": reasons,
    }
    return reasons, metrics


def _metrics_from_enriched(row: NormalizedScannerFeatureRow, *, candidate_source: str) -> dict[str, Any]:
    return {
        "symbol": row.symbol,
        "last_price": row.last_price,
        "volume": row.volume,
        "avg_volume": row.avg_volume,
        "relative_volume": row.relative_volume,
        "spread_bps": row.spread_bps,
        "dollar_volume": row.dollar_volume,
        "vwap": row.vwap,
        "rsi": row.rsi,
        "macd_signal": row.macd_signal,
        "provider_name": row.provider_primary,
        "provider_chain": row.provider_chain,
        "data_quality": row.data_quality,
        "feature_quality": row.feature_quality,
        "field_sources": row.field_sources,
        "hard_blockers": row.hard_blockers,
        "soft_warnings": row.soft_warnings,
        "relative_volume_status": row.relative_volume_status,
        "spread_status": row.spread_status,
        "source": candidate_source,
        "candidate_source": candidate_source,
    }


def build_scanner_diagnostics(
    *,
    symbols: list[str] | None,
    max_candidates: int,
    requested_source: str = "auto",
    source: str = "real_provider",
    candidate_source: str = "scanner",
    scanner_run_id: str | None = None,
) -> dict[str, Any]:
    started_at = _utc_now()
    run_id = scanner_run_id or f"scanner-{uuid4().hex[:12]}"
    max_candidates = max(1, min(int(max_candidates or 10), 100))
    clean_symbols = _clean_symbols(symbols, max_candidates)
    provider_priority = _priority_for_source(requested_source)
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    rejection_counts = {reason: 0 for reason in REJECTION_REASONS}
    provider_data_count = 0
    provider_name: str | None = provider_priority[0] if provider_priority else None
    fallback_provider: str | None = None
    fallback_reason: str | None = None

    enriched_rows = _ENRICH.enrich(clean_symbols, requested_source=requested_source, strategy_key="stock_day_trading", max_candidates=max_candidates)

    for row in enriched_rows:
        provider_name = provider_name or row.provider_primary
        if row.data_quality == "real" and "provider_unavailable" not in row.hard_blockers:
            provider_data_count += 1

        # Best-effort preserve old fallback fields from MarketDataService snapshots.
        # (Enrichment owns provider chain; this remains for legacy visibility only.)
        try:
            snap = _MARKET_DATA.get_market_snapshot(row.symbol, source=requested_source)
            fallback_provider, fallback_reason = _merge_fallback_details(fallback_provider, fallback_reason, snap, provider_priority)
        except Exception:
            pass

        metrics = _metrics_from_enriched(row, candidate_source=candidate_source)
        reasons = list(row.hard_blockers)

        if reasons:
            for reason in reasons:
                if reason == "synthetic_data":
                    key = "synthetic_data"
                elif reason == "non_real_data":
                    key = "non_real_data"
                else:
                    key = reason
                if key in rejection_counts:
                    rejection_counts[key] += 1
            rejected.append({**metrics, "rejection_reasons": reasons})
            continue

        selected.append({**metrics, "score": 0.8})

    status = "candidate_selected" if selected else ("data_unavailable" if clean_symbols and provider_data_count == 0 else "no_qualified_setup")
    diagnostics = {
        "scanner_run_id": run_id,
        "provider_name": provider_name,
        "provider_priority": provider_priority,
        "provider_configured": _provider_configured(provider_name),
        "alpaca_configured": _provider_configured("alpaca"),
        "alpaca_feed": _alpaca_feed(),
        "feed": _alpaca_feed() if provider_name == "alpaca" else None,
        "fallback_provider": fallback_provider,
        "fallback_reason": fallback_reason,
        "scan_started_at": started_at,
        "scan_finished_at": _utc_now(),
        "source": source,
        "candidate_source": candidate_source,
        "total_symbols_seen": len(clean_symbols),
        "total_symbols_with_provider_data": provider_data_count,
        "total_symbols_rejected": len(rejected),
        "total_symbols_passed": len(selected),
        "rejection_counts": rejection_counts,
        "selected_candidates": selected,
        "rejected_candidates": rejected,
        "status": status,
        "no_qualified_setup": not selected,
        "reason": None if clean_symbols else "no_real_discovery_universe_configured",
        "submitted_order": False,
        "broker_called": False,
        "llm_used": False,
    }
    if clean_symbols and not selected and status == "no_qualified_setup":
        diagnostics["reason"] = "no_symbols_passed_scanner_criteria"
    if clean_symbols and status == "data_unavailable":
        diagnostics["reason"] = "data_unavailable"
    return diagnostics
