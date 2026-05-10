from __future__ import annotations

import os
from typing import Any

from app.services.candidate_universe_service import CandidateSourceType, add_candidate, get_persistence_mode, list_candidates
from app.services.market_condition_scanner_service import MarketScannerRequest, run_market_condition_scan
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
        summary = {
            "worker": "market-scanner-worker",
            "worker_run_id": worker_run_id,
            "provider": provider,
            "candidate_source": "none",
            "recommendation_status": "no_qualified_setup",
            "raw_candidate_count": 0,
            "filtered_candidate_count": 0,
            "selected_symbols": [],
            "rejected_count": 0,
            "blockers": ["no_scanner_candidates_passed_filters"],
            "warnings": warnings,
            "persistence_status": get_persistence_mode(),
        }
        record_worker_status(
            worker="market-scanner-worker",
            status="no_qualified_setup",
            worker_run_id=worker_run_id,
            provider=provider,
            candidate_source="none",
            selected_symbols=[],
            raw_candidate_count=0,
            filtered_candidate_count=0,
            warnings=warnings,
            blockers=["no_scanner_candidates_passed_filters"],
        )
        print_summary(summary)
        return summary

    try:
        scan = run_market_condition_scan(
            MarketScannerRequest(
                strategy_key=os.environ.get("WORKER_SCANNER_STRATEGY", "multi_factor"),
                symbols=seed_symbols[:max_candidates],
                data_source=os.environ.get("MARKET_DATA_PROVIDER", "auto"),
                auto_run=False,
                trigger_type="scheduled",
                trigger_workflow=False,
                use_latest_watchlist=False,
            )
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

    selected_symbols = clean_symbols([signal.symbol for signal in scan.matched_signals])
    scanner_candidates: list[dict[str, Any]] = []
    for signal in scan.matched_signals:
        metadata = dict(signal.metadata or {})
        scanner_candidates.append(
            {
                "symbol": signal.symbol,
                "source": "scanner",
                "provider_name": scan.data_source if scan.data_source != "source_backed" else provider,
                "last_price": metadata.get("last_price") or metadata.get("price"),
                "volume": metadata.get("volume"),
                "avg_volume": metadata.get("avg_volume") or metadata.get("average_volume"),
                "relative_volume": metadata.get("relative_volume"),
                "spread_bps": metadata.get("spread_bps"),
                "vwap": metadata.get("vwap"),
                "price_above_vwap": metadata.get("price_above_vwap"),
                "session_state": metadata.get("session_state"),
                "score": signal.confidence,
                "signal_key": signal.signal_key,
                "reason": signal.reason,
            }
        )
        try:
            add_candidate(
                symbol=signal.symbol,
                asset_class="stock",
                horizon="day_trading",
                source_type=CandidateSourceType.SCANNER,
                source_detail=f"Worker scanner run {scan.run_id}: {signal.signal_key}",
                priority_score=round(float(signal.confidence or 0) * 100, 2),
                notes=signal.reason,
            )
        except Exception as exc:
            warnings.append(f"candidate_persistence_failed:{exc}")

    if not selected_symbols and scan.data_source == "placeholder":
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
        "provider": provider,
        "candidate_source": candidate_source,
        "recommendation_status": recommendation_status,
        "raw_candidate_count": len(seed_symbols),
        "filtered_candidate_count": len(selected_symbols),
        "selected_symbols": selected_symbols,
        "rejected_count": len(scan.skipped_signals),
        "blockers": blockers,
        "warnings": warnings + list(scan.model_dump().get("warnings", []) or []),
        "persistence_status": get_persistence_mode(),
    }
    save_scanner_candidates(
        worker_run_id=worker_run_id,
        provider_name=provider,
        candidates=scanner_candidates,
        rejected_candidates=[signal.model_dump() for signal in scan.skipped_signals],
        status=recommendation_status,
        warnings=warnings + list(scan.model_dump().get("warnings", []) or []),
        blockers=blockers,
    )
    print_summary(summary)
    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
