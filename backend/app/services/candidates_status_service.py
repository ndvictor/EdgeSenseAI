"""Candidates stage visibility/status.

Read-only status endpoint backing service:
- does not generate candidates automatically
- does not run recommendations or risk workflows
- does not call external providers
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.candidate_universe_service import get_candidate_universe_summary


CandidatesHealth = Literal["ready", "warning", "error", "disabled"]


class CandidatesSummary(BaseModel):
    candidates_status: CandidatesHealth
    candidate_sources_configured: int
    active_candidates: int
    ranked_candidates: int
    blocked_candidates: int
    last_candidate_at: str | None
    next_action: str


class CandidateSourceStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    key: str
    label: str
    status: CandidatesHealth
    description: str
    input_stage: str
    candidate_types: list[str]
    downstream_consumers: list[str]
    active_count: int
    ranked_count: int
    blocked_count: int
    last_candidate_at: str | None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_action: str


class CandidatesPipelinePosition(BaseModel):
    previous_stage: Literal["signals"] = "signals"
    current_stage: Literal["candidates"] = "candidates"
    next_stage: Literal["recommendations"] = "recommendations"
    downstream_stage: Literal["risk"] = "risk"


class CandidatesStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok"] = "ok"
    data_mode: Literal["summary"] = "summary"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: CandidatesSummary
    candidate_sources: list[CandidateSourceStatus]
    pipeline_position: CandidatesPipelinePosition = Field(default_factory=CandidatesPipelinePosition)


def build_candidates_status() -> CandidatesStatusResponse:
    # Safe read-only counts from candidate universe (does not generate candidates).
    universe = get_candidate_universe_summary()
    active_candidates = int(universe.get("active_count", 0) or 0)

    if active_candidates <= 0:
        next_action = (
            "No active candidates yet. Run the Signal Engine (Signals stage), run Universe Selection, "
            "or add symbols to Candidates via Candidate Universe."
        )
    else:
        next_action = "Candidates are available. Run Recommendations to rank/select, then proceed to Risk checks."

    sources: list[CandidateSourceStatus] = [
        CandidateSourceStatus(
            key="signal_engine",
            label="Signal Engine",
            status="ready",
            description="Promotes qualified signals into trade candidates",
            input_stage="signals",
            candidate_types=["rvol_breakout", "vwap_reclaim", "gap_continuation", "regime_momentum"],
            downstream_consumers=["recommendations", "risk", "command_center"],
            active_count=active_candidates,
            ranked_count=0,
            blocked_count=0,
            last_candidate_at=None,
            next_action=next_action,
        ),
        CandidateSourceStatus(
            key="manual_watchlist",
            label="Manual Watchlist",
            status="ready",
            description="User-curated symbols promoted into Candidates for review",
            input_stage="signals",
            candidate_types=["manual_pick"],
            downstream_consumers=["recommendations", "risk", "command_center"],
            active_count=0,
            ranked_count=0,
            blocked_count=0,
            last_candidate_at=None,
            next_action="Add symbols to Candidate Universe with source_type=manual or watchlist.",
        ),
        CandidateSourceStatus(
            key="scanner_watchlist",
            label="Scanner Watchlist",
            status="ready",
            description="Symbols discovered by scanners and added to Candidates for ranking",
            input_stage="signals",
            candidate_types=["scanner_discovery"],
            downstream_consumers=["recommendations", "risk", "command_center"],
            active_count=0,
            ranked_count=0,
            blocked_count=0,
            last_candidate_at=None,
            next_action="Run Market Scanner, then promote scan hits into Candidate Universe.",
        ),
        CandidateSourceStatus(
            key="strategy_lab",
            label="Strategy Lab",
            status="ready",
            description="Strategy experimentation outputs that can be promoted into Candidates",
            input_stage="signals",
            candidate_types=["strategy_workflow_match"],
            downstream_consumers=["recommendations", "risk", "command_center"],
            active_count=0,
            ranked_count=0,
            blocked_count=0,
            last_candidate_at=None,
            next_action="Run a Strategy Workflow and promote actionable symbols into Candidate Universe.",
        ),
        CandidateSourceStatus(
            key="live_watchlist",
            label="Live Watchlist",
            status="ready",
            description="Intraday triggered watchlist items promoted into Candidates (paper-only visibility)",
            input_stage="signals",
            candidate_types=["live_trigger"],
            downstream_consumers=["recommendations", "risk", "command_center"],
            active_count=0,
            ranked_count=0,
            blocked_count=0,
            last_candidate_at=None,
            next_action="Run live watchlist scan (paper research mode) and promote items into Candidate Universe.",
        ),
        CandidateSourceStatus(
            key="market_regime_filter",
            label="Market Regime Filter",
            status="ready",
            description="Filters/annotates candidates based on market regime constraints",
            input_stage="signals",
            candidate_types=["regime_filtered"],
            downstream_consumers=["recommendations", "risk", "command_center"],
            active_count=0,
            ranked_count=0,
            blocked_count=0,
            last_candidate_at=None,
            next_action="Compute market regime and apply regime gates during candidate ranking.",
        ),
        CandidateSourceStatus(
            key="catalyst_filter",
            label="Catalyst Filter",
            status="ready",
            description="Filters/annotates candidates using catalyst and sentiment context",
            input_stage="signals",
            candidate_types=["catalyst_tagged"],
            downstream_consumers=["recommendations", "risk", "command_center"],
            active_count=0,
            ranked_count=0,
            blocked_count=0,
            last_candidate_at=None,
            next_action="Ingest/normalize catalysts and sentiment signals, then tag candidates before ranking.",
        ),
    ]

    summary = CandidatesSummary(
        candidates_status="ready",
        candidate_sources_configured=len(sources),
        active_candidates=sum(s.active_count for s in sources),
        ranked_candidates=sum(s.ranked_count for s in sources),
        blocked_candidates=sum(s.blocked_count for s in sources),
        last_candidate_at=None,
        next_action=next_action,
    )

    return CandidatesStatusResponse(summary=summary, candidate_sources=sources)

