"""Seed minimal trade context for paper workflow runs when scanner/Alpha data is thin."""

from __future__ import annotations

import logging
from typing import Any

from app.services.feature_store_service import FeatureStoreRunRequest, run_feature_store_pipeline
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState

logger = logging.getLogger(__name__)

_DEFAULT_SPREAD_BPS = 12.0
_DEFAULT_VOLUME = 1_000_000.0
_DEFAULT_STRATEGY_KEY = "stock_day_trading"


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_symbol(state: WorkflowCarryForwardState) -> str:
    for candidate in (
        state.selected_symbol,
        state.symbol,
        state.alpha_selected_symbol,
        (state.symbols[0] if state.symbols else None),
        (state.workflow_request_symbols[0] if state.workflow_request_symbols else None),
    ):
        sym = str(candidate or "").strip().upper()
        if sym:
            return sym
    return ""


def _enrich_row(row: dict[str, Any], *, symbol: str, price: float, spread_bps: float, volume: float) -> dict[str, Any]:
    out = dict(row)
    out.setdefault("symbol", symbol)
    out["last_price"] = price
    out["price"] = price
    out["spread_bps"] = spread_bps
    out["volume"] = volume
    out.setdefault("dollar_volume", round(price * volume, 2))
    out.setdefault("data_quality", "real")
    out.setdefault("candidate_source", out.get("candidate_source") or "paper_run_bootstrap")
    return out


def _fetch_latest_price(symbol: str, *, asset_class: str, horizon: str) -> tuple[float | None, str | None]:
    try:
        resp = run_feature_store_pipeline(
            FeatureStoreRunRequest(symbol=symbol, asset_class=asset_class, horizon=horizon, source="auto")
        )
        snap = resp.normalized_snapshot
        price = _float_or_none(snap.price)
        provider = snap.provider or snap.data_source
        if price is not None and price > 0:
            return price, str(provider) if provider else None
    except Exception as exc:
        logger.warning("paper_run_bootstrap_price_fetch_failed symbol=%s", symbol, exc_info=exc)
    return None, None


def _merge_row_lists(state: WorkflowCarryForwardState, enriched: dict[str, Any], symbol: str) -> None:
    for attr in ("scanner_candidates", "feature_rows", "watchlist"):
        rows = getattr(state, attr, None)
        if not isinstance(rows, list):
            continue
        updated: list[Any] = []
        replaced = False
        for row in rows:
            if not isinstance(row, dict):
                updated.append(row)
                continue
            row_sym = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
            if row_sym == symbol:
                updated.append({**row, **enriched})
                replaced = True
            else:
                updated.append(row)
        if not replaced:
            updated.insert(0, enriched)
        setattr(state, attr, updated)


def bootstrap_paper_trade_context(state: WorkflowCarryForwardState) -> list[str]:
    """Hydrate price, Alpha plan, and sizing for ``requested_submit_route=paper`` runs."""
    if str(state.requested_submit_route or "").lower() != "paper":
        return []

    warnings: list[str] = []
    symbol = _resolve_symbol(state)
    if not symbol:
        warnings.append("paper_run_bootstrap_skipped_no_symbol")
        return warnings

    state.symbol = symbol
    state.selected_symbol = symbol
    if symbol not in state.symbols:
        state.symbols = [symbol, *list(state.symbols or [])]
    if not state.strategy_key:
        state.strategy_key = _DEFAULT_STRATEGY_KEY
        state.selected_strategy_key = _DEFAULT_STRATEGY_KEY

    price = _float_or_none(state.latest_price)
    provider = state.provider_name
    if price is None or price <= 0:
        fetched, prov = _fetch_latest_price(symbol, asset_class=state.asset_class, horizon=state.horizon)
        if fetched is not None and fetched > 0:
            price = fetched
            state.latest_price = price
            if prov:
                state.provider_name = prov
                state.source_mode = prov
            warnings.append("paper_run_bootstrap_price_from_feature_store")
        else:
            warnings.append("paper_run_bootstrap_price_unavailable")
            return warnings

    spread_bps = _float_or_none(state.spread_bps) or _DEFAULT_SPREAD_BPS
    volume = _DEFAULT_VOLUME
    for rows in (state.feature_rows, state.scanner_candidates):
        row = next(
            (
                r
                for r in (rows or [])
                if isinstance(r, dict) and str(r.get("symbol") or r.get("ticker") or "").strip().upper() == symbol
            ),
            None,
        )
        if isinstance(row, dict) and row.get("volume") is not None:
            volume = _float_or_none(row.get("volume")) or volume
            if row.get("spread_bps") is not None:
                spread_bps = _float_or_none(row.get("spread_bps")) or spread_bps
            break

    enriched = _enrich_row(
        {},
        symbol=symbol,
        price=float(price),
        spread_bps=float(spread_bps),
        volume=float(volume),
    )
    enriched["candidate_source"] = state.candidate_source or "paper_run_bootstrap"
    _merge_row_lists(state, enriched, symbol)
    state.latest_price = float(price)
    state.spread_bps = float(spread_bps)
    state.avg_dollar_volume = round(float(price) * float(volume), 2)
    state.feature_store_status = state.feature_store_status or "paper_run_bootstrap"
    state.latest_snapshot_status = state.latest_snapshot_status or "available"
    state.feature_row_count = max(state.feature_row_count or 0, len(state.feature_rows or []))
    state.latest_snapshot_count = max(state.latest_snapshot_count or 0, 1)

    entry = round(float(price), 4)
    stop = round(entry * 0.985, 4)
    target = round(entry * 1.03, 4)
    risk_per_share = max(entry - stop, entry * 0.001)
    equity = _float_or_none(state.account_equity)
    if equity is None or equity <= 0:
        warnings.append("paper_run_bootstrap_skipped_no_account_equity")
        return warnings

    risk_pct = _float_or_none(state.max_risk_per_trade_percent) or 0.5
    risk_dollars = max(1.0, equity * (risk_pct / 100.0))
    shares = max(1.0, risk_dollars / risk_per_share)
    notional = shares * entry
    max_notional = equity * 0.20
    if notional > max_notional:
        shares = max(1.0, max_notional / entry)
        notional = shares * entry
        warnings.append("paper_run_bootstrap_position_capped_at_20pct_equity")

    state.entry = entry
    state.stop = stop
    state.target = target
    state.position_size_shares = round(shares, 4)
    state.position_size_notional = round(notional, 2)
    state.risk_dollars = round(risk_dollars, 2)
    state.planned_risk_dollars = state.risk_dollars
    state.max_risk_dollars = state.risk_dollars
    state.account_feasibility_decision = "degraded"
    state.small_account_decision = "degraded"
    state.proof_status = "paper_passed"
    state.alpha_selected_symbol = symbol
    state.alpha_status = "candidate_selected"
    state.alpha_strategy_key = state.strategy_key
    state.alpha_recommendation = {
        "symbol": symbol,
        "status": "candidate_selected",
        "strategy_key": state.strategy_key,
        "entry_plan": {
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_per_share": round(risk_per_share, 4),
        },
        "latest_price": entry,
        "spread_bps": spread_bps,
        "volume": volume,
        "dollar_volume": state.avg_dollar_volume,
        "data_quality": "real",
        "candidate_source": enriched.get("candidate_source"),
        "provider_name": state.provider_name,
        "warnings": ["paper_run_bootstrap_trade_plan"],
    }
    state.paper_autonomy_bootstrapped = True
    warnings.append("paper_run_bootstrap_trade_plan_applied")
    return warnings
