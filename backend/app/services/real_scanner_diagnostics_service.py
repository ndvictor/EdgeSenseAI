from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.effective_runtime import effective_str
from app.services.market_condition_scanner_service import _relative_volume, _session_state, _spread_bps
from app.services.market_data_service import MarketDataService


HARD_BLOCKER_REASONS = (
    "missing_price",
    "missing_volume",
    "dollar_volume_too_low",
    "market_closed",
    "provider_unavailable",
    "stale_data",
    "spread_too_wide",
    "not_fractionable",
    "position_notional_below_broker_min",
    "risk_sizing_failed",
)

SOFT_WARNING_REASONS = (
    "missing_relative_volume",
    "relative_volume_too_low",
    "missing_avg_volume",
    "missing_spread",
    "wide_spread_after_hours",
    "high_price_fractional_required",
    "fractional_support_unknown",
    "incomplete_feature_set",
)

REJECTION_REASONS = HARD_BLOCKER_REASONS
_ALLOWED_SCAN_SESSIONS = {"regular", "market_open", "open", "premarket", "post_market", "postmarket", "unknown"}
_REGULAR_MARKET_SESSIONS = {"regular", "market_open", "open"}
_MARKET_DATA = MarketDataService()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_from_env(name: str, default: bool) -> bool:
    raw = effective_str(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _setting_float(name: str, default: float) -> float:
    value = _float_or_none(effective_str(name))
    return default if value is None else value


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


def _fractional_supported(snapshot: dict[str, Any]) -> bool | str:
    raw = snapshot.get("fractionable")
    if raw is None:
        raw = snapshot.get("fractional_supported")
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return True if _bool_from_env("FRACTIONAL_SHARES_ENABLED", True) else "unknown"
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _fractional_feasibility(price: float | None, snapshot: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    account_equity = _setting_float("ACCOUNT_EQUITY_DEFAULT", 1000.0)
    max_position_pct = _setting_float("MAX_POSITION_PCT", 0.05)
    max_risk_per_trade_pct = _setting_float("MAX_RISK_PER_TRADE_PCT", 0.005)
    broker_min_notional = _setting_float("BROKER_MIN_NOTIONAL", 1.0)
    target_position_notional = account_equity * max_position_pct
    max_risk_dollars = account_equity * max_risk_per_trade_pct
    fractional_supported = _fractional_supported(snapshot)
    feasibility: dict[str, Any] = {
        "account_equity": account_equity,
        "max_position_pct": max_position_pct,
        "target_position_notional": target_position_notional,
        "max_risk_per_trade_pct": max_risk_per_trade_pct,
        "max_risk_dollars": max_risk_dollars,
        "broker_min_notional": broker_min_notional,
        "estimated_quantity": None,
        "fractional_required": False,
        "fractional_supported": fractional_supported,
        "price_feasibility_status": "missing_price",
    }
    blockers: list[str] = []
    warnings: list[str] = []
    if price is None or price <= 0:
        blockers.append("missing_price")
        return feasibility, blockers, warnings
    estimated_quantity = target_position_notional / price
    fractional_required = estimated_quantity < 1.0
    feasibility.update(
        {
            "estimated_quantity": estimated_quantity,
            "fractional_required": fractional_required,
            "price_feasibility_status": "fractional_feasible" if fractional_required else "whole_share_feasible",
        }
    )
    if target_position_notional < broker_min_notional:
        blockers.append("position_notional_below_broker_min")
        feasibility["price_feasibility_status"] = "position_notional_below_broker_min"
    if max_risk_dollars <= 0 or target_position_notional <= 0:
        blockers.append("risk_sizing_failed")
        feasibility["price_feasibility_status"] = "risk_sizing_failed"
    if fractional_required:
        warnings.append("high_price_fractional_required")
        if fractional_supported is False:
            blockers.append("not_fractionable")
            feasibility["price_feasibility_status"] = "not_fractionable"
        elif fractional_supported == "unknown":
            warnings.append("fractional_support_unknown")
    return feasibility, blockers, warnings


def _candidate_score(
    *,
    hard_blockers: list[str],
    soft_warnings: list[str],
    enrichment_needed: list[str],
    relative_volume: float | None,
    dollar_volume: float | None,
    spread_bps: float | None,
) -> float:
    if hard_blockers:
        return 0.0
    score = 0.55
    if relative_volume is not None:
        score += min(relative_volume, 3.0) * 0.08
    if dollar_volume is not None and dollar_volume >= 25_000_000:
        score += 0.12
    elif dollar_volume is not None and dollar_volume >= 5_000_000:
        score += 0.06
    if spread_bps is not None:
        if spread_bps <= 10:
            score += 0.08
        elif spread_bps <= 35:
            score += 0.03
    score -= min(len(soft_warnings), 5) * 0.035
    score -= min(len(enrichment_needed), 5) * 0.04
    return round(max(0.0, min(0.99, score)), 4)


def _evaluate_symbol(symbol: str, snapshot: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    price = _price(snapshot)
    volume = _volume(snapshot)
    avg_volume = _float_or_none(snapshot.get("average_volume") or snapshot.get("avg_volume"))
    relative_volume = _float_or_none(_relative_volume(snapshot))
    spread_bps = _spread_bps(snapshot, price)
    session_state = _session_state(snapshot)
    data_quality = str(snapshot.get("data_quality") or "").lower()
    hard_blockers: list[str] = []
    soft_warnings: list[str] = []
    enrichment_needed: list[str] = []

    if not _has_provider_data(snapshot):
        hard_blockers.append("provider_unavailable")
    if data_quality == "stale" or snapshot.get("stale_data") or snapshot.get("is_stale"):
        hard_blockers.append("stale_data")
    if price is None or price <= 0:
        hard_blockers.append("missing_price")
    if volume is None or volume <= 0:
        hard_blockers.append("missing_volume")

    feasibility, feasibility_blockers, feasibility_warnings = _fractional_feasibility(price, snapshot)
    hard_blockers.extend(feasibility_blockers)
    soft_warnings.extend(feasibility_warnings)

    if avg_volume is None:
        enrichment_needed.append("avg_volume")
        soft_warnings.append("missing_avg_volume")
    if relative_volume is None:
        enrichment_needed.append("relative_volume")
        soft_warnings.append("missing_relative_volume")
    elif relative_volume < 1.5:
        soft_warnings.append("relative_volume_too_low")
    if spread_bps is None:
        soft_warnings.append("missing_spread")
    elif spread_bps > 35.0:
        if session_state in _REGULAR_MARKET_SESSIONS:
            hard_blockers.append("spread_too_wide")
        else:
            soft_warnings.append("wide_spread_after_hours")
    dollar_volume = None if price is None or volume is None else price * volume
    if dollar_volume is not None and dollar_volume < 1_000_000:
        hard_blockers.append("dollar_volume_too_low")
    if session_state not in _ALLOWED_SCAN_SESSIONS:
        hard_blockers.append("market_closed")

    hard_blockers = list(dict.fromkeys(hard_blockers))
    soft_warnings = list(dict.fromkeys(soft_warnings))
    enrichment_needed = list(dict.fromkeys(enrichment_needed))
    score = _candidate_score(
        hard_blockers=hard_blockers,
        soft_warnings=soft_warnings,
        enrichment_needed=enrichment_needed,
        relative_volume=relative_volume,
        dollar_volume=dollar_volume,
        spread_bps=spread_bps,
    )
    if hard_blockers:
        candidate_status = "blocked"
        decision = "blocked"
        next_action = "do_not_send_to_alpha"
        decision_reason = f"Hard blockers: {', '.join(hard_blockers)}"
    elif enrichment_needed:
        candidate_status = "needs_enrichment"
        decision = "watchlist_only"
        next_action = "send_to_feature_enrichment"
        decision_reason = "Real data is available, but derived features need enrichment before Alpha scoring."
    elif score < 0.55:
        candidate_status = "watchlist_only"
        decision = "watchlist_only"
        next_action = "monitor_candidate"
        decision_reason = "Candidate has no hard blockers but score is not strong enough for Alpha yet."
    else:
        candidate_status = "candidate_selected"
        decision = "candidate_selected"
        next_action = "send_to_alpha"
        decision_reason = "Candidate has real data, feasible sizing, and enough features for scanner selection."

    metrics = {
        "symbol": symbol,
        "last_price": price,
        "volume": volume,
        "avg_volume": avg_volume,
        "relative_volume": relative_volume,
        "relative_volume_status": "available" if relative_volume is not None else "unavailable",
        "spread_bps": spread_bps,
        "spread_status": "available" if spread_bps is not None else "unavailable",
        "session_state": session_state,
        "dollar_volume": dollar_volume,
        "provider_name": snapshot.get("provider"),
        "data_quality": snapshot.get("data_quality"),
        "field_sources": {
            "last_price": snapshot.get("provider") if price is not None else None,
            "volume": snapshot.get("provider") if volume is not None else None,
            "avg_volume": snapshot.get("provider") if avg_volume is not None else None,
            "relative_volume": "computed" if relative_volume is not None else None,
            "spread_bps": snapshot.get("provider") if spread_bps is not None else None,
            "dollar_volume": "computed" if dollar_volume is not None else None,
        },
        "provider_chain": [snapshot.get("provider")] if snapshot.get("provider") else [],
        "feature_quality": "complete" if not enrichment_needed else "partial",
        "hard_blockers": hard_blockers,
        "soft_warnings": soft_warnings,
        "enrichment_needed": enrichment_needed,
        "candidate_status": candidate_status,
        "decision": decision,
        "decision_reason": decision_reason,
        "next_action": next_action,
        "confidence": score,
        "score": score,
        "rejection_reasons": hard_blockers,
        **feasibility,
    }
    return hard_blockers, metrics


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
    watchlist: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    rejection_counts = {reason: 0 for reason in HARD_BLOCKER_REASONS}
    warning_counts = {reason: 0 for reason in SOFT_WARNING_REASONS}
    enrichment_counts: dict[str, int] = {}
    provider_data_count = 0
    provider_name: str | None = provider_priority[0] if provider_priority else None
    fallback_provider: str | None = None
    fallback_reason: str | None = None

    for symbol in clean_symbols:
        snapshot = _MARKET_DATA.get_market_snapshot(symbol, source=requested_source)
        actual_provider = snapshot.get("provider") or provider_name
        if snapshot.get("provider"):
            provider_name = str(snapshot.get("provider"))
        if _has_provider_data(snapshot):
            provider_data_count += 1
        fallback_provider, fallback_reason = _merge_fallback_details(fallback_provider, fallback_reason, snapshot, provider_priority)
        hard_blockers, metrics = _evaluate_symbol(symbol, snapshot)
        metrics["provider_name"] = metrics.get("provider_name") or actual_provider
        metrics["source"] = candidate_source
        metrics["candidate_source"] = candidate_source
        for reason in hard_blockers:
            if reason in rejection_counts:
                rejection_counts[reason] += 1
        for warning in metrics.get("soft_warnings") or []:
            if warning in warning_counts:
                warning_counts[warning] += 1
        for feature in metrics.get("enrichment_needed") or []:
            enrichment_counts[feature] = enrichment_counts.get(feature, 0) + 1
        if metrics["candidate_status"] == "candidate_selected":
            selected.append(metrics)
        elif metrics["candidate_status"] in {"needs_enrichment", "watchlist_only"}:
            watchlist.append(metrics)
        else:
            rejected.append(metrics)

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
        "selected_count": len(selected),
        "watchlist_count": len(watchlist),
        "blocked_count": len(rejected),
        "needs_enrichment_count": len([row for row in watchlist if row.get("candidate_status") == "needs_enrichment"]),
        "no_trade_count": len([row for row in rejected if row.get("decision") == "no_trade"]),
        "rejection_counts": rejection_counts,
        "warning_counts": warning_counts,
        "enrichment_counts": enrichment_counts,
        "selected_candidates": selected,
        "watchlist_candidates": watchlist,
        "rejected_candidates": rejected,
        "status": status,
        "no_qualified_setup": not selected,
        "reason": None if clean_symbols else "no_real_discovery_universe_configured",
        "submitted_order": False,
        "broker_called": False,
        "llm_used": False,
    }
    if clean_symbols and not selected and status == "no_qualified_setup":
        diagnostics["reason"] = "no_symbols_ready_for_alpha"
    if clean_symbols and status == "data_unavailable":
        diagnostics["reason"] = "data_unavailable"
    return diagnostics
