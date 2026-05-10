from __future__ import annotations

import os
from typing import Any

from app.services.candidate_universe_service import get_persistence_mode, list_candidates
from app.services.real_scanner_diagnostics_service import build_scanner_diagnostics
from app.services.universe_selection_service import get_latest_universe_selection
from app.services.worker_output_store import record_worker_status, save_scanner_candidates
from app.workers.common import clean_symbols, get_worker_run_id, print_summary, require_production_data_policy, setup_worker_logging


def _candidate_symbols(limit: int) -> list[str]:
    candidates = list_candidates(status="active")
    ranked = sorted(candidates, key=lambda c: (-float(c.priority_score or 0), str(c.symbol)))
    return clean_symbols([c.symbol for c in ranked[:limit]])


def _latest_universe_symbols(limit: int) -> list[str]:
    latest = get_latest_universe_selection()
    if latest is None:
        return []
    return clean_symbols([c.symbol for c in (latest.selected_watchlist or latest.ranked_candidates or [])[:limit]])


def run() -> dict[str, Any]:
    setup_worker_logging()
    require_production_data_policy()
    worker_run_id = get_worker_run_id("market-scanner-worker")
    max_candidates = max(1, int(os.environ.get("WORKER_MAX_CANDIDATES") or "25"))
    provider = os.environ.get("MARKET_DATA_PROVIDER", "yfinance")
    warnings: list[str] = []
    blockers: list[str] = []

    seed_symbols = _candidate_symbols(max_candidates)
    candidate_source = "candidate_universe"
    if not seed_symbols:
        seed_symbols = _latest_universe_symbols(max_candidates)
        candidate_source = "latest_universe_selection"

    if not seed_symbols:
        diagnostics = build_scanner_diagnostics(
            symbols=[],
            max_candidates=max_candidates,
            requested_source=provider,
            source="real_provider",
            candidate_source="scanner",
            scanner_run_id=worker_run_id,
        )
        summary = {
            "worker": "market-scanner-worker",
            "worker_run_id": worker_run_id,
            "scanner_run_id": worker_run_id,
            "provider": diagnostics.get("provider_name") or provider,
            "provider_name": diagnostics.get("provider_name") or provider,
            "provider_priority": diagnostics.get("provider_priority") or [],
            "provider_configured": diagnostics.get("provider_configured") or False,
            "candidate_source": "scanner",
            "recommendation_status": "no_qualified_setup",
            "raw_candidate_count": 0,
            "filtered_candidate_count": 0,
            "selected_symbols": [],
            "rejected_count": 0,
            "blockers": ["no_real_discovery_universe_configured"],
            "warnings": warnings,
            "persistence_status": get_persistence_mode(),
            "scanner_diagnostics": diagnostics,
        }
        record_worker_status(
            worker="market-scanner-worker",
            status="no_qualified_setup",
            worker_run_id=worker_run_id,
            provider=diagnostics.get("provider_name") or provider,
            provider_name=diagnostics.get("provider_name") or provider,
            provider_priority=diagnostics.get("provider_priority") or [],
            provider_configured=diagnostics.get("provider_configured") or False,
            source="real_provider",
            candidate_source="scanner",
            selected_symbols=[],
            raw_candidate_count=0,
            filtered_candidate_count=0,
            warnings=warnings,
            blockers=["no_real_discovery_universe_configured"],
            scanner_diagnostics=diagnostics,
        )
        print_summary(summary)
        return summary

    try:
        diagnostics = build_scanner_diagnostics(
            symbols=seed_symbols[:max_candidates],
            max_candidates=max_candidates,
            requested_source=os.environ.get("MARKET_DATA_PROVIDER", "auto"),
            source="real_provider",
            candidate_source="scanner",
            scanner_run_id=worker_run_id,
        )
    except Exception as exc:
        summary = {
            "worker": "market-scanner-worker",
            "worker_run_id": worker_run_id,
            "provider": provider,
            "candidate_source": candidate_source,
            "recommendation_status": "data_unavailable",
            "raw_candidate_count": len(seed_symbols),
            "filtered_candidate_count": 0,
            "selected_symbols": [],
            "rejected_count": len(seed_symbols),
            "blockers": ["scanner_or_provider_unavailable"],
            "warnings": [str(exc)],
            "persistence_status": get_persistence_mode(),
        }
        record_worker_status(
            worker="market-scanner-worker",
            status="data_unavailable",
            worker_run_id=worker_run_id,
            provider=provider,
            candidate_source=candidate_source,
            selected_symbols=[],
            raw_candidate_count=len(seed_symbols),
            filtered_candidate_count=0,
            warnings=[str(exc)],
            blockers=["scanner_or_provider_unavailable"],
        )
        print_summary(summary)
        return summary

    scanner_candidates = list(diagnostics.get("selected_candidates") or [])
    selected_symbols = clean_symbols([candidate.get("symbol") for candidate in scanner_candidates])
    if diagnostics.get("status") == "data_unavailable":
        blockers.append("scanner_or_provider_unavailable")
        recommendation_status = "data_unavailable"
    elif not selected_symbols:
        blockers.append("no_scanner_candidates_passed_filters")
        recommendation_status = "no_qualified_setup"
    else:
        recommendation_status = "candidate_selected"

    summary = {
        "worker": "market-scanner-worker",
        "worker_run_id": worker_run_id,
        "scanner_run_id": worker_run_id,
        "provider": diagnostics.get("provider_name") or provider,
        "provider_name": diagnostics.get("provider_name") or provider,
        "provider_priority": diagnostics.get("provider_priority") or [],
        "provider_configured": diagnostics.get("provider_configured") or False,
        "feed": diagnostics.get("feed"),
        "fallback_provider": diagnostics.get("fallback_provider"),
        "fallback_reason": diagnostics.get("fallback_reason"),
        "source": "real_provider",
        "candidate_source": "scanner",
        "recommendation_status": recommendation_status,
        "raw_candidate_count": len(seed_symbols),
        "filtered_candidate_count": len(selected_symbols),
        "selected_symbols": selected_symbols,
        "rejected_count": int(diagnostics.get("total_symbols_rejected") or 0),
        "rejection_counts": diagnostics.get("rejection_counts") or {},
        "blockers": blockers,
        "warnings": warnings,
        "persistence_status": get_persistence_mode(),
        "scanner_diagnostics": diagnostics,
    }
    save_scanner_candidates(
        worker_run_id=worker_run_id,
        provider_name=diagnostics.get("provider_name") or provider,
        candidates=scanner_candidates,
        rejected_candidates=list(diagnostics.get("rejected_candidates") or []),
        status=recommendation_status,
        warnings=warnings,
        blockers=blockers,
        diagnostics=diagnostics,
    )
    print_summary(summary)
    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
