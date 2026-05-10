"""Seed workflow carry-forward state from real scanner diagnostics (no invented symbols)."""

from __future__ import annotations

from typing import Any

from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _no_hard_blockers(row: dict[str, Any]) -> bool:
    hb = row.get("hard_blockers")
    return not (isinstance(hb, list) and hb)


def seed_workflow_state_from_scanner_diagnostics(
    state: WorkflowCarryForwardState,
    scanner_diagnostics: dict[str, Any],
    latest_scanner_status: dict[str, Any] | None = None,
) -> None:
    """Populate state from ``selected_candidates`` (or unblocked watchlist-style lists only).

    Does not read ``rejected_candidates`` or legacy universe_selection.
    """
    raw_selected = scanner_diagnostics.get("selected_candidates")
    selected: list[dict[str, Any]] = []
    if isinstance(raw_selected, list):
        selected = [c for c in raw_selected if isinstance(c, dict) and _no_hard_blockers(c)]
    if not selected:
        alt = scanner_diagnostics.get("watchlist_candidates")
        if isinstance(alt, list):
            selected = [c for c in alt if isinstance(c, dict) and _no_hard_blockers(c)]
    candidates: list[dict[str, Any]] = []
    for c in selected:
        sym = str(c.get("symbol") or c.get("ticker") or "").strip().upper()
        if not sym:
            continue
        row = dict(c)
        row.setdefault("symbol", sym)
        candidates.append(row)
    if not candidates:
        return

    first = candidates[0]
    sym0 = str(first.get("symbol") or "").strip().upper()
    symbols = [str(c.get("symbol") or "").strip().upper() for c in candidates if c.get("symbol")]

    state.scanner_candidates = list(candidates)
    state.feature_rows = list(candidates)
    state.watchlist = list(candidates)
    state.usable_symbols = list(symbols)
    state.symbols = list(symbols)
    state.symbol = sym0
    state.selected_symbol = sym0

    src_diag = str(scanner_diagnostics.get("candidate_source") or "").strip()
    src_c = str(first.get("candidate_source") or first.get("source") or "").strip()
    state.candidate_source = (src_c or src_diag) or None

    prov = scanner_diagnostics.get("provider_name")
    if prov:
        state.source_mode = str(prov)
        state.provider_name = str(prov)
    elif not state.source_mode:
        state.source_mode = state.source

    merged_ps: dict[str, Any] = dict(state.provider_status)
    merged_ps.update(
        {
            "scanner_run_id": scanner_diagnostics.get("scanner_run_id"),
            "provider_configured": scanner_diagnostics.get("provider_configured"),
            "alpaca_configured": scanner_diagnostics.get("alpaca_configured"),
            "provider_priority": scanner_diagnostics.get("provider_priority"),
            "scanner_latest_status": latest_scanner_status or {},
        }
    )
    state.provider_status = merged_ps

    state.latest_price = _float_or_none(first.get("last_price"))
    state.spread_bps = _float_or_none(first.get("spread_bps"))
    state.avg_dollar_volume = _float_or_none(first.get("dollar_volume"))

    state.latest_snapshot_status = "available"
    state.latest_snapshot_count = len(candidates)
    state.feature_store_status = "scanner_enriched"
    state.feature_row_count = len(candidates)
    if not state.persistence_status:
        state.persistence_status = "scanner_runtime"
    state.freshness_status = "fresh"

    state.submitted_order = False
    state.broker_called = False
    state.llm_used = False
