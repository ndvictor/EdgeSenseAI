"""Live watchlist candidates.

This service must NOT return hardcoded demo tickers as if they were real signals.
If no signal engine is connected, we surface candidate-universe entries as
"watch_only / not_configured" rows so the UI can render user-owned symbols
without fake triggers/fills.
"""

from app.schemas import LiveWatchlistCandidate
from app.services.candidate_universe_service import CandidateStatus, list_candidates


def build_live_candidates() -> list[LiveWatchlistCandidate]:
    rows: list[LiveWatchlistCandidate] = []
    for c in list_candidates(status=CandidateStatus.ACTIVE):
        asset_class = (c.asset_class or "stock").lower().strip()
        if asset_class not in {"stock", "option", "crypto"}:
            asset_class = "stock"
        prio = int(max(0, min(100, round(float(c.priority_score or 50.0)))))
        rows.append(
            LiveWatchlistCandidate(
                symbol=c.symbol,
                asset=asset_class.upper(),
                asset_class=asset_class,  # type: ignore[arg-type]
                horizon=c.horizon or "swing",
                trigger="not_configured",
                trigger_type="not_configured",
                priority_score=prio,
                trigger_strength=prio,
                account_fit="not_configured",
                account_fit_label="Not evaluated",
                suggested_expression="Watch-only until signal + risk gates are connected",
                agent_status="not_configured",
                notify_status="watch_only",
                notify_label="Watch only",
                data_quality="not_configured",
                reason="Live watchlist is currently sourced from Candidate Universe (no live signal engine connected).",
                risk_factors=[],
            )
        )
    return rows
