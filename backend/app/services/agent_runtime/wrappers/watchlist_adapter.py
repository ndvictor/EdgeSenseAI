from __future__ import annotations

from typing import Any

from app.core.production_safety import allow_worker_symbols_in_production, is_production_environment
from app.services.candidate_universe_service import list_candidates
from app.services.feature_store_service import get_latest_feature_rows
from app.services.universe_selection_service import UniverseSelectionRequest, get_latest_universe_selection, run_universe_selection
from app.services.worker_output_store import get_latest_feature_rows as get_latest_worker_feature_rows
from app.services.worker_output_store import get_latest_feature_rows_for_production_discovery, get_latest_scanner_candidates


def _norm_symbols(raw: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in raw or []:
        s = str(x).strip().upper()
        if not s or s == "CANDIDATE_UNIVERSE_EMPTY":
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _horizon_for_universe(horizon: str) -> str:
    h = (horizon or "day_trading").lower().strip()
    if h in ("day_trading", "day_trade"):
        return "day_trade"
    return "day_trade"


def _symbols_from_feature_pipeline(*, max_pick: int) -> list[str]:
    rows = get_latest_feature_rows()
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        t = (row.ticker or "").strip().upper()
        if not t or t in seen:
            continue
        if getattr(row, "data_quality", None) == "fail":
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_pick:
            break
    return out


def _symbols_from_latest_universe(*, max_pick: int) -> list[str]:
    latest = get_latest_universe_selection()
    if latest is None:
        return []
    out: list[str] = []
    for c in latest.selected_watchlist or []:
        s = (c.symbol or "").strip().upper()
        if s and s not in out:
            out.append(s)
        if len(out) >= max_pick:
            break
    return out


def _symbols_from_candidate_universe(*, asset_class: str, horizon: str, max_pick: int) -> list[str]:
    candidates = list_candidates(status="active")
    out: list[str] = []
    for candidate in sorted(candidates, key=lambda c: (-float(c.priority_score or 0), str(c.symbol))):
        symbol = (candidate.symbol or "").strip().upper()
        if not symbol or symbol in out:
            continue
        if candidate.asset_class != asset_class:
            continue
        if candidate.horizon not in {horizon, "day_trade", "day_trading"}:
            continue
        if candidate.source_type == "manual":
            continue
        out.append(symbol)
        if len(out) >= max_pick:
            break
    return out


def _worker_output_candidates(*, max_pick: int) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    scanner_candidates = get_latest_scanner_candidates(max_pick)
    if is_production_environment():
        feature_rows = (
            get_latest_feature_rows_for_production_discovery(max_pick)
            if allow_worker_symbols_in_production()
            else []
        )
        row_sources = [scanner_candidates, feature_rows]
    else:
        feature_rows = get_latest_worker_feature_rows(max_pick)
        row_sources = [feature_rows, scanner_candidates]

    seen: set[str] = set()
    symbols: list[str] = []
    for src in row_sources:
        for row in src:
            symbol = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            symbols.append(symbol)
            if len(symbols) >= max_pick:
                break
    return symbols, scanner_candidates, feature_rows


def build_watchlist(
    *,
    asset_class: str,
    horizon: str,
    max_symbols: int = 10,
    seed_symbols: list[str] | None = None,
    discovery_symbols: list[str] | None = None,
    orchestrator_mode: bool = False,
    data_source: str = "auto",
) -> dict[str, Any]:
    """Build a workflow-ready watchlist.

    **Orchestrator mode**: ``seed_symbols`` are symbols **explicitly** supplied on the workflow
    request only. ``discovery_symbols`` are symbols already resolved upstream (e.g. data readiness
    from worker/scanner output); those never run :func:`run_universe_selection`.
    When ``seed_symbols`` is empty, discovery uses worker store / scanner paths (not universe_selection).

    **Normal mode**: legacy Candidate Universe list for non-orchestrated runs.
    """
    if orchestrator_mode:
        cap = max(1, min(100, max_symbols))
        pipeline_horizon = _horizon_for_universe(horizon)
        manual = _norm_symbols(seed_symbols)
        discovered = _norm_symbols(discovery_symbols)

        if not manual and discovered:
            symbols = discovered[:cap]
            return {
                "decision": "candidate_selected",
                "recommendation": {
                    "status": "candidate_selected",
                    "symbol": symbols[0],
                    "mock_data_used": False,
                    "synthetic_data_used": False,
                    "reason": None,
                },
                "symbols": symbols,
                "usable_symbols": symbols,
                "ranked_candidates": [{"symbol": symbol, "source_type": "scanner"} for symbol in symbols],
                "scanner_candidates": [],
                "feature_rows": [],
                "source_breakdown": {"scanner": len(symbols), "worker_output_feed": len(symbols)},
                "selected_candidate": symbols[0],
                "candidate_source": "scanner",
                "raw_candidate_count": len(symbols),
                "filtered_candidate_count": len(symbols),
                "blockers": [],
                "warnings": [],
                "next_action": "Proceed to Alpha Engine selection.",
            }

        seeds = manual
        candidate_source = "manual_symbols" if manual else None
        ac_raw = (asset_class or "stock").lower().strip()
        if ac_raw not in ("stock", "option", "crypto"):
            ac_raw = "stock"
        try:
            if not seeds:
                seeds, scanner_candidates, feature_rows = _worker_output_candidates(max_pick=cap)
                if seeds:
                    symbols = seeds[:cap]
                    return {
                        "decision": "candidate_selected",
                        "recommendation": {
                            "status": "candidate_selected",
                            "symbol": symbols[0],
                            "mock_data_used": False,
                            "synthetic_data_used": False,
                            "reason": None,
                        },
                        "symbols": symbols,
                        "usable_symbols": symbols,
                        "ranked_candidates": [{"symbol": symbol, "source_type": "scanner"} for symbol in symbols],
                        "scanner_candidates": scanner_candidates,
                        "feature_rows": feature_rows,
                        "source_breakdown": {"scanner": len(scanner_candidates), "feature_rows": len(feature_rows)},
                        "selected_candidate": symbols[0],
                        "candidate_source": "scanner",
                        "raw_candidate_count": len(scanner_candidates) or len(feature_rows),
                        "filtered_candidate_count": len(symbols),
                        "blockers": [],
                        "warnings": [],
                        "next_action": "Proceed to Alpha Engine selection.",
                    }
            if not seeds:
                seeds = _symbols_from_candidate_universe(asset_class=ac_raw, horizon=horizon, max_pick=cap)
                candidate_source = "candidate_universe" if seeds else candidate_source
            if not seeds:
                seeds = _symbols_from_feature_pipeline(max_pick=cap)
                candidate_source = "feature_pipeline" if seeds else candidate_source
            if not seeds:
                seeds = _symbols_from_latest_universe(max_pick=cap)
                candidate_source = "latest_universe_selection" if seeds else candidate_source
        except Exception as exc:
            return {
                "decision": "blocked",
                "recommendation": {
                    "status": "data_unavailable",
                    "symbol": None,
                    "mock_data_used": False,
                    "synthetic_data_used": False,
                    "reason": "scanner_or_provider_unavailable",
                },
                "symbols": [],
                "ranked_candidates": [],
                "source_breakdown": {},
                "selected_candidate": None,
                "candidate_source": "scanner/provider",
                "raw_candidate_count": 0,
                "filtered_candidate_count": 0,
                "blockers": ["scanner_or_provider_unavailable"],
                "warnings": [str(exc)],
                "next_action": "Provider-backed discovery failed; verify market data provider configuration.",
            }

        if not seeds:
            return {
                "decision": "no_trade",
                "recommendation": {
                    "status": "no_qualified_setup",
                    "symbol": None,
                    "mock_data_used": False,
                    "synthetic_data_used": False,
                    "reason": "no_scanner_candidates_passed_filters",
                },
                "symbols": [],
                "ranked_candidates": [],
                "source_breakdown": {"candidate_universe": 0, "feature_pipeline": 0, "latest_universe": 0},
                "selected_candidate": None,
                "candidate_source": "none",
                "raw_candidate_count": 0,
                "filtered_candidate_count": 0,
                "blockers": ["no_scanner_candidates_passed_filters"],
                "warnings": [],
                "next_action": "No provider-backed scanner/candidate symbols are available.",
            }
        if not seed_symbols:
            symbols = seeds[:cap]
            return {
                "decision": "candidate_selected" if symbols else "no_trade",
                "recommendation": {
                    "status": "candidate_selected" if symbols else "no_qualified_setup",
                    "symbol": symbols[0] if symbols else None,
                    "mock_data_used": False,
                    "synthetic_data_used": False,
                    "reason": None if symbols else "no_scanner_candidates_passed_filters",
                },
                "symbols": symbols,
                "ranked_candidates": [{"symbol": symbol, "source_type": candidate_source or "scanner/provider"} for symbol in symbols],
                "source_breakdown": {candidate_source or "scanner/provider": len(symbols)},
                "selected_candidate": symbols[0] if symbols else None,
                "candidate_source": candidate_source or "scanner/provider",
                "raw_candidate_count": len(seeds),
                "filtered_candidate_count": len(symbols),
                "blockers": [] if symbols else ["no_scanner_candidates_passed_filters"],
                "warnings": [],
                "next_action": "Proceed to strategy selection." if symbols else "No provider-backed scanner/candidate symbols are available.",
            }
        src = data_source if data_source in ("auto", "yfinance", "alpaca", "polygon") else "auto"
        try:
            univ = run_universe_selection(
                UniverseSelectionRequest(
                    symbols=seeds[: max(50, cap * 5)],
                    asset_class=ac_raw,  # type: ignore[arg-type]
                    horizon=pipeline_horizon,  # type: ignore[arg-type]
                    source=src,  # type: ignore[arg-type]
                    max_candidates=cap,
                    min_score=40,
                )
            )
        except Exception as exc:
            return {
                "decision": "blocked",
                "recommendation": {
                    "status": "data_unavailable",
                    "symbol": None,
                    "mock_data_used": False,
                    "synthetic_data_used": False,
                    "reason": "scanner_or_provider_unavailable",
                },
                "symbols": [],
                "ranked_candidates": [],
                "source_breakdown": {"candidate_universe": len(seeds)},
                "selected_candidate": None,
                "candidate_source": "scanner/provider",
                "raw_candidate_count": len(seeds),
                "filtered_candidate_count": 0,
                "blockers": ["scanner_or_provider_unavailable"],
                "warnings": [str(exc)],
                "next_action": "Provider-backed discovery failed; verify market data provider configuration.",
            }
        selected = univ.selected_watchlist or []
        if not selected and univ.ranked_candidates:
            selected = univ.ranked_candidates[:cap]

        symbols = [(c.symbol or "").upper() for c in selected if c.symbol][:cap]
        discovery_blocker = "no_scanner_candidates_passed_filters"
        discovery_status = "no_qualified_setup"
        if not symbols and (
            univ.status == "blocked_by_data_freshness"
            or any("unavailable" in str(b).lower() or "provider" in str(b).lower() for b in (univ.blockers or []))
        ):
            discovery_blocker = "scanner_or_provider_unavailable"
            discovery_status = "data_unavailable"
        ranked_candidates = [
            {
                "symbol": c.symbol,
                "priority_score": c.priority_score,
                "universe_score": c.universe_score,
                "source_type": "universe_selection",
                "provider": c.provider,
                "data_quality": c.data_quality,
            }
            for c in selected[:cap]
        ]
        return {
            "symbols": symbols,
            "ranked_candidates": ranked_candidates,
            "source_breakdown": {
                "universe_selection": len(symbols),
                "universe_run_id": univ.run_id,
                "data_freshness_status": univ.data_freshness_status,
            },
            "selected_candidate": symbols[0] if symbols else None,
            "next_action": "Proceed to strategy selection." if symbols else (univ.blockers[0] if univ.blockers else "No symbols passed universe selection."),
            "universe_selection_status": univ.status,
            "pipeline_blockers": univ.blockers,
            "candidate_source": "universe_selection",
            "raw_candidate_count": len(seeds),
            "filtered_candidate_count": len(symbols),
            "recommendation": {
                "status": "candidate_selected" if symbols else discovery_status,
                "symbol": symbols[0] if symbols else None,
                "mock_data_used": False,
                "synthetic_data_used": False,
                "reason": None if symbols else discovery_blocker,
            },
            "blockers": [] if symbols else [discovery_blocker],
            "warnings": list(univ.warnings or []),
        }

    candidates = list_candidates(status="active")
    filtered = [c for c in candidates if c.asset_class == asset_class and c.horizon in {horizon, "day_trade", "day_trading"}]
    filtered = sorted(filtered, key=lambda c: (-float(c.priority_score or 0), str(c.symbol)))
    symbols = [c.symbol for c in filtered[:max_symbols]]
    ranked_candidates = [{"symbol": c.symbol, "priority_score": c.priority_score, "source_type": c.source_type} for c in filtered[:max_symbols]]
    return {
        "symbols": symbols,
        "ranked_candidates": ranked_candidates,
        "source_breakdown": {"candidate_universe": len(symbols)},
        "selected_candidate": symbols[0] if symbols else None,
        "next_action": "Proceed to strategy selection." if symbols else "No candidates available. Run market scanner promotion or add manual candidates.",
    }
