from __future__ import annotations

from typing import Any

from app.services.candidate_universe_service import list_candidates
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


def _worker_output_candidates(*, max_pick: int) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    """Production discovery uses only latest scanner-linked worker outputs."""
    scanner_candidates = get_latest_scanner_candidates(max_pick)
    feature_rows = get_latest_feature_rows_for_production_discovery(max_pick)
    row_sources = [scanner_candidates, feature_rows]

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


def _no_scanner_candidates_response() -> dict[str, Any]:
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
        "usable_symbols": [],
        "ranked_candidates": [],
        "scanner_candidates": [],
        "feature_rows": [],
        "source_breakdown": {"scanner": 0, "feature_rows": 0},
        "selected_candidate": None,
        "candidate_source": "none",
        "raw_candidate_count": 0,
        "filtered_candidate_count": 0,
        "blockers": ["no_scanner_candidates_passed_filters"],
        "warnings": [],
        "next_action": "No provider-backed scanner candidates are available.",
    }


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

    Orchestrator mode is production-strict:
    - explicit request symbols are allowed
    - upstream discovery symbols are allowed
    - latest scanner-linked worker outputs are allowed
    - no candidate universe fallback
    - no universe selection fallback
    - no old feature row fallback
    """
    if orchestrator_mode:
        cap = max(1, min(100, max_symbols))
        manual = _norm_symbols(seed_symbols)
        discovered = _norm_symbols(discovery_symbols)

        if manual:
            symbols = manual[:cap]
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
                "ranked_candidates": [{"symbol": symbol, "source_type": "manual_symbols"} for symbol in symbols],
                "scanner_candidates": [],
                "feature_rows": [],
                "source_breakdown": {"manual_symbols": len(symbols)},
                "selected_candidate": symbols[0],
                "candidate_source": "manual_symbols",
                "raw_candidate_count": len(symbols),
                "filtered_candidate_count": len(symbols),
                "blockers": [],
                "warnings": [],
                "next_action": "Proceed to Alpha Engine selection.",
            }

        if discovered:
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

        symbols, scanner_candidates, feature_rows = _worker_output_candidates(max_pick=cap)
        if not symbols:
            return _no_scanner_candidates_response()

        picked = symbols[:cap]
        return {
            "decision": "candidate_selected",
            "recommendation": {
                "status": "candidate_selected",
                "symbol": picked[0],
                "mock_data_used": False,
                "synthetic_data_used": False,
                "reason": None,
            },
            "symbols": picked,
            "usable_symbols": picked,
            "ranked_candidates": [{"symbol": symbol, "source_type": "scanner"} for symbol in picked],
            "scanner_candidates": scanner_candidates,
            "feature_rows": feature_rows,
            "source_breakdown": {"scanner": len(scanner_candidates), "feature_rows": len(feature_rows)},
            "selected_candidate": picked[0],
            "candidate_source": "scanner",
            "raw_candidate_count": len(scanner_candidates) or len(feature_rows),
            "filtered_candidate_count": len(picked),
            "blockers": [],
            "warnings": [],
            "next_action": "Proceed to Alpha Engine selection.",
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
