from __future__ import annotations

import os
from typing import Any

from app.services.candidate_universe_service import get_persistence_mode
from app.services.market_session_service import get_market_session_state, scanner_mode_for_session
from app.services.real_scanner_diagnostics_service import build_scanner_diagnostics
from app.services.worker_output_store import record_worker_status, save_scanner_candidates
from app.workers.common import clean_symbols, get_worker_run_id, print_summary, require_production_data_policy, setup_worker_logging


def _configured_scanner_symbols(limit: int) -> list[str]:
    """Explicit scanner universe for scheduled workers.

    No default/fallback symbols. Configure SCANNER_SYMBOLS or WORKER_SYMBOLS in Azure Container Apps.
    """
    raw = os.environ.get("SCANNER_SYMBOLS") or os.environ.get("WORKER_SYMBOLS") or ""
    return clean_symbols(raw.split(","))[:limit]


def _session_payload() -> dict[str, Any]:
    state = get_market_session_state()
    mode = scanner_mode_for_session(state)
    return {
        "market_session": state.market_session,
        "market_date": state.market_date,
        "current_time_et": state.current_time_et,
        "clock_source": state.clock_source,
        "is_trading_day": state.is_trading_day,
        "is_market_open": state.is_market_open,
        "is_pre_market": state.is_pre_market,
        "is_regular_market": state.is_regular_market,
        "is_post_market": state.is_post_market,
        "next_open": state.next_open,
        "next_close": state.next_close,
        "scanner_mode": mode,
        "session_warnings": list(state.warnings or []),
    }


def _record_and_return(summary: dict[str, Any]) -> dict[str, Any]:
    record_worker_status(
        worker="market-scanner-worker",
        status=str(summary.get("status") or summary.get("recommendation_status") or "unknown"),
        worker_run_id=str(summary.get("worker_run_id") or ""),
        provider=summary.get("provider_name") or summary.get("provider"),
        provider_name=summary.get("provider_name") or summary.get("provider"),
        provider_priority=summary.get("provider_priority") or [],
        provider_configured=bool(summary.get("provider_configured")),
        source="real_provider",
        candidate_source="scanner",
        selected_symbols=summary.get("selected_symbols") or [],
        raw_candidate_count=int(summary.get("raw_candidate_count") or 0),
        filtered_candidate_count=int(summary.get("filtered_candidate_count") or 0),
        warnings=summary.get("warnings") or [],
        blockers=summary.get("blockers") or [],
        scanner_diagnostics=summary.get("scanner_diagnostics") or {},
        market_session=summary.get("market_session"),
        market_date=summary.get("market_date"),
        current_time_et=summary.get("current_time_et"),
        clock_source=summary.get("clock_source"),
        is_trading_day=summary.get("is_trading_day"),
        is_market_open=summary.get("is_market_open"),
        is_pre_market=summary.get("is_pre_market"),
        is_regular_market=summary.get("is_regular_market"),
        is_post_market=summary.get("is_post_market"),
        next_open=summary.get("next_open"),
        next_close=summary.get("next_close"),
        scanner_mode=summary.get("scanner_mode"),
    )
    print_summary(summary)
    return summary


def run() -> dict[str, Any]:
    setup_worker_logging()
    require_production_data_policy()
    worker_run_id = get_worker_run_id("market-scanner-worker")
    max_candidates = max(1, int(os.environ.get("WORKER_MAX_CANDIDATES") or "25"))
    provider = os.environ.get("MARKET_DATA_PROVIDER", "yfinance")
    session = _session_payload()

    if session["scanner_mode"] == "market_closed":
        return _record_and_return(
            {
                "worker": "market-scanner-worker",
                "worker_run_id": worker_run_id,
                "scanner_run_id": worker_run_id,
                "provider": provider,
                "provider_name": provider,
                "source": "real_provider",
                "candidate_source": "scanner",
                "status": "market_closed",
                "recommendation_status": "market_closed",
                "raw_candidate_count": 0,
                "filtered_candidate_count": 0,
                "selected_symbols": [],
                "rejected_count": 0,
                "blockers": ["market_closed"],
                "warnings": session.get("session_warnings") or [],
                "persistence_status": get_persistence_mode(),
                "scanner_diagnostics": {"status": "market_closed", **session},
                **session,
            }
        )

    seed_symbols = _configured_scanner_symbols(max_candidates)
    if not seed_symbols:
        diagnostics = build_scanner_diagnostics(
            symbols=[],
            max_candidates=max_candidates,
            requested_source=provider,
            source="real_provider",
            candidate_source="scanner",
            scanner_run_id=worker_run_id,
        )
        diagnostics = {**diagnostics, **session}
        return _record_and_return(
            {
                "worker": "market-scanner-worker",
                "worker_run_id": worker_run_id,
                "scanner_run_id": worker_run_id,
                "provider": diagnostics.get("provider_name") or provider,
                "provider_name": diagnostics.get("provider_name") or provider,
                "provider_priority": diagnostics.get("provider_priority") or [],
                "provider_configured": diagnostics.get("provider_configured") or False,
                "source": "real_provider",
                "candidate_source": "scanner",
                "status": "no_qualified_setup",
                "recommendation_status": "no_qualified_setup",
                "raw_candidate_count": 0,
                "filtered_candidate_count": 0,
                "selected_symbols": [],
                "rejected_count": 0,
                "blockers": ["no_configured_scanner_symbols"],
                "warnings": session.get("session_warnings") or [],
                "persistence_status": get_persistence_mode(),
                "scanner_diagnostics": diagnostics,
                **session,
            }
        )

    try:
        diagnostics = build_scanner_diagnostics(
            symbols=seed_symbols[:max_candidates],
            max_candidates=max_candidates,
            requested_source=provider,
            source="real_provider",
            candidate_source="scanner",
            scanner_run_id=worker_run_id,
        )
        diagnostics = {**diagnostics, **session}
    except Exception as exc:
        return _record_and_return(
            {
                "worker": "market-scanner-worker",
                "worker_run_id": worker_run_id,
                "scanner_run_id": worker_run_id,
                "provider": provider,
                "provider_name": provider,
                "source": "real_provider",
                "candidate_source": "scanner",
                "status": "data_unavailable",
                "recommendation_status": "data_unavailable",
                "raw_candidate_count": len(seed_symbols),
                "filtered_candidate_count": 0,
                "selected_symbols": [],
                "rejected_count": len(seed_symbols),
                "blockers": ["scanner_or_provider_unavailable"],
                "warnings": [str(exc), *(session.get("session_warnings") or [])],
                "persistence_status": get_persistence_mode(),
                "scanner_diagnostics": {"status": "data_unavailable", "warning": str(exc), **session},
                **session,
            }
        )

    scanner_candidates = list(diagnostics.get("selected_candidates") or [])
    selected_symbols = clean_symbols([candidate.get("symbol") for candidate in scanner_candidates])
    blockers: list[str] = []
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
        "status": recommendation_status,
        "recommendation_status": recommendation_status,
        "raw_candidate_count": len(seed_symbols),
        "filtered_candidate_count": len(selected_symbols),
        "selected_symbols": selected_symbols,
        "rejected_count": int(diagnostics.get("total_symbols_rejected") or 0),
        "rejection_counts": diagnostics.get("rejection_counts") or {},
        "blockers": blockers,
        "warnings": session.get("session_warnings") or [],
        "persistence_status": get_persistence_mode(),
        "scanner_diagnostics": diagnostics,
        **session,
    }
    save_scanner_candidates(
        worker_run_id=worker_run_id,
        provider_name=diagnostics.get("provider_name") or provider,
        candidates=scanner_candidates,
        rejected_candidates=list(diagnostics.get("rejected_candidates") or []),
        status=recommendation_status,
        warnings=session.get("session_warnings") or [],
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
