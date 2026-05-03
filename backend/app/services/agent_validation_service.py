"""LangGraph Agent Validation Service.

Validates high-quality ensemble signals through specialist agent-style checks.
For now this is deterministic and dry-run. Does not require actual LangGraph.

NO paid LLM calls.
Deterministic validation only.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SpecialistVote(BaseModel):
    """Vote from a specialist agent."""

    model_config = ConfigDict(protected_namespaces=())

    agent_key: str
    vote: Literal["pass", "watch", "block", "abstain"]
    score: float = Field(..., ge=0, le=1)
    reason: str


class AgentValidationRequest(BaseModel):
    """Request to run agent validation."""

    model_config = ConfigDict(protected_namespaces=())

    ensemble_signal: dict[str, Any] | None = None
    symbol: str | None = None
    strategy_key: str | None = None
    final_signal_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    llm_policy: str = "deterministic_only"  # deterministic_only, cheap_summary_allowed, strong_reasoning_allowed
    dry_run: bool = True
    data_quality: str | None = None
    liquidity_score: float | None = None
    spread_percent: float | None = None
    volatility_score: float | None = None


class AgentValidationResponse(BaseModel):
    """Response from agent validation."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["pass", "watch", "blocked", "skipped"]
    symbol: str | None = None
    specialist_votes: list[SpecialistVote]
    validation_score: float = Field(..., ge=0, le=100)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str
    checked_at: datetime


# Constants
MIN_SIGNAL_SCORE_FOR_VALIDATION = 60.0
MIN_CONFIDENCE_FOR_PASS = 0.50
MIN_LIQUIDITY_SCORE = 0.3
MAX_SPREAD_PERCENT = 2.0

# In-memory storage
_LATEST_AGENT_VALIDATION: AgentValidationResponse | None = None


def _deterministic_data_quality_check(
    data_quality: str | None, volatility_score: float | None
) -> SpecialistVote:
    """Data Quality Agent - deterministic check."""
    if data_quality == "fail":
        return SpecialistVote(
            agent_key="data_quality_agent",
            vote="block",
            score=0.0,
            reason="Data quality check failed. Signal rejected.",
        )
    if data_quality == "unavailable":
        return SpecialistVote(
            agent_key="data_quality_agent",
            vote="watch",
            score=0.3,
            reason="Data quality unavailable. Reduced confidence.",
        )
    score = 0.9 if data_quality == "pass" else 0.6
    return SpecialistVote(
        agent_key="data_quality_agent",
        vote="pass",
        score=score,
        reason="Data quality acceptable." if data_quality == "pass" else "Data quality marginal.",
    )


def _deterministic_market_regime_check(
    final_signal_score: float | None, confidence: float | None
) -> SpecialistVote:
    """Market Regime Agent - deterministic check."""
    if final_signal_score is None or final_signal_score < MIN_SIGNAL_SCORE_FOR_VALIDATION:
        return SpecialistVote(
            agent_key="market_regime_agent",
            vote="block",
            score=0.0,
            reason=f"Signal score {final_signal_score} below minimum threshold {MIN_SIGNAL_SCORE_FOR_VALIDATION}.",
        )
    if confidence is not None and confidence < MIN_CONFIDENCE_FOR_PASS:
        return SpecialistVote(
            agent_key="market_regime_agent",
            vote="watch",
            score=confidence,
            reason=f"Confidence {confidence:.2f} below pass threshold {MIN_CONFIDENCE_FOR_PASS}.",
        )
    score = min(1.0, (final_signal_score / 100) * (confidence or 0.5))
    return SpecialistVote(
        agent_key="market_regime_agent",
        vote="pass",
        score=score,
        reason=f"Signal score {final_signal_score} and confidence {confidence} meet thresholds.",
    )


def _deterministic_technical_signal_check(final_signal_score: float | None) -> SpecialistVote:
    """Technical Signal Agent - deterministic check."""
    if final_signal_score is None:
        return SpecialistVote(
            agent_key="technical_signal_agent",
            vote="abstain",
            score=0.0,
            reason="No signal score provided.",
        )
    if final_signal_score >= 80:
        return SpecialistVote(
            agent_key="technical_signal_agent",
            vote="pass",
            score=final_signal_score / 100,
            reason=f"Strong technical signal: {final_signal_score}.",
        )
    if final_signal_score >= 60:
        return SpecialistVote(
            agent_key="technical_signal_agent",
            vote="watch",
            score=final_signal_score / 100,
            reason=f"Moderate technical signal: {final_signal_score}. Watch for confirmation.",
        )
    return SpecialistVote(
        agent_key="technical_signal_agent",
        vote="block",
        score=final_signal_score / 100,
        reason=f"Weak technical signal: {final_signal_score}. Below minimum threshold.",
    )


def _deterministic_volume_check(liquidity_score: float | None, spread_percent: float | None) -> SpecialistVote:
    """Volume Agent - deterministic liquidity check."""
    warnings = []
    if liquidity_score is None:
        warnings.append("Liquidity score not provided")
    if spread_percent is None:
        warnings.append("Spread percent not provided")

    if liquidity_score is not None and liquidity_score < MIN_LIQUIDITY_SCORE:
        return SpecialistVote(
            agent_key="volume_agent",
            vote="block",
            score=liquidity_score,
            reason=f"Liquidity score {liquidity_score} below minimum {MIN_LIQUIDITY_SCORE}.",
        )
    if spread_percent is not None and spread_percent > MAX_SPREAD_PERCENT:
        return SpecialistVote(
            agent_key="volume_agent",
            vote="watch",
            score=max(0, 1 - spread_percent / 100),
            reason=f"Spread {spread_percent}% above watch threshold {MAX_SPREAD_PERCENT}%.",
        )

    score = 0.8
    if liquidity_score is not None:
        score = min(1.0, liquidity_score)
    if spread_percent is not None:
        score = min(score, max(0, 1 - spread_percent / 10))

    return SpecialistVote(
        agent_key="volume_agent",
        vote="pass",
        score=score,
        reason="Liquidity and spread acceptable for trading." + (f" Warnings: {warnings}" if warnings else ""),
    )


def _deterministic_model_orchestrator_check(final_signal_score: float | None) -> SpecialistVote:
    """Model Orchestrator Agent - deterministic check."""
    if final_signal_score is None:
        return SpecialistVote(
            agent_key="model_orchestrator_agent",
            vote="abstain",
            score=0.0,
            reason="No signal score to evaluate.",
        )
    if final_signal_score >= 85:
        return SpecialistVote(
            agent_key="model_orchestrator_agent",
            vote="pass",
            score=0.95,
            reason=f"High-quality ensemble signal: {final_signal_score}.",
        )
    if final_signal_score >= 70:
        return SpecialistVote(
            agent_key="model_orchestrator_agent",
            vote="pass",
            score=0.75,
            reason=f"Good ensemble signal: {final_signal_score}.",
        )
    if final_signal_score >= 60:
        return SpecialistVote(
            agent_key="model_orchestrator_agent",
            vote="watch",
            score=0.50,
            reason=f"Marginal ensemble signal: {final_signal_score}. Proceed with caution.",
        )
    return SpecialistVote(
        agent_key="model_orchestrator_agent",
        vote="block",
        score=final_signal_score / 100,
        reason=f"Low-quality ensemble signal: {final_signal_score}.",
    )


def _deterministic_risk_manager_placeholder() -> SpecialistVote:
    """Risk Manager Agent - placeholder (actual risk check is separate service)."""
    return SpecialistVote(
        agent_key="risk_manager_agent_placeholder",
        vote="abstain",
        score=0.5,
        reason="Risk review performed separately by Risk Manager service.",
    )


def _deterministic_portfolio_manager_placeholder() -> SpecialistVote:
    """Portfolio Manager Agent - placeholder."""
    return SpecialistVote(
        agent_key="portfolio_manager_agent_placeholder",
        vote="abstain",
        score=0.5,
        reason="Portfolio allocation performed separately by Capital Allocation service.",
    )


def run_agent_validation(request: AgentValidationRequest) -> AgentValidationResponse:
    """Run deterministic agent validation.

    Rules:
    - No paid LLM calls.
    - If llm_policy deterministic_only, run deterministic checks.
    - If signal score < 60, skipped/blocked.
    - Data quality issues reduce score.
    - Missing spread/liquidity creates warning.
    - Output is validation only, not recommendation.
    """
    run_id = f"agent-val-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc)

    symbol = request.symbol
    if request.ensemble_signal and not symbol:
        symbol = request.ensemble_signal.get("symbol")

    final_score = request.final_signal_score
    if request.ensemble_signal and final_score is None:
        final_score = request.ensemble_signal.get("final_signal_score")

    confidence = request.confidence
    if request.ensemble_signal and confidence is None:
        confidence = request.ensemble_signal.get("confidence")

    # Check if should skip due to low score
    if final_score is not None and final_score < MIN_SIGNAL_SCORE_FOR_VALIDATION:
        return AgentValidationResponse(
            run_id=run_id,
            status="skipped",
            symbol=symbol,
            specialist_votes=[],
            validation_score=0.0,
            blockers=[f"Signal score {final_score} below minimum {MIN_SIGNAL_SCORE_FOR_VALIDATION}"],
            warnings=[],
            reason=f"Validation skipped: signal score too low ({final_score}).",
            checked_at=checked_at,
        )

    # Run specialist votes
    votes = [
        _deterministic_data_quality_check(request.data_quality, request.volatility_score),
        _deterministic_market_regime_check(final_score, confidence),
        _deterministic_technical_signal_check(final_score),
        _deterministic_volume_check(request.liquidity_score, request.spread_percent),
        _deterministic_model_orchestrator_check(final_score),
        _deterministic_risk_manager_placeholder(),
        _deterministic_portfolio_manager_placeholder(),
    ]

    # Calculate aggregate score
    valid_votes = [v for v in votes if v.vote != "abstain"]
    if valid_votes:
        avg_score = sum(v.score for v in valid_votes) / len(valid_votes)
    else:
        avg_score = 0.0

    validation_score = int(avg_score * 100)

    # Determine status
    block_votes = [v for v in votes if v.vote == "block"]
    watch_votes = [v for v in votes if v.vote == "watch"]

    blockers = [v.reason for v in block_votes]
    warnings = [v.reason for v in watch_votes]

    if block_votes:
        status: Literal["pass", "watch", "blocked", "skipped"] = "blocked"
        reason = f"Blocked by {len(block_votes)} specialist(s): {[v.agent_key for v in block_votes]}"
    elif watch_votes:
        status = "watch"
        reason = f"Watch status from {len(watch_votes)} specialist(s). Proceed with caution."
    else:
        status = "pass"
        reason = f"Passed validation with score {validation_score}. All specialists agree."

    result = AgentValidationResponse(
        run_id=run_id,
        status=status,
        symbol=symbol,
        specialist_votes=votes,
        validation_score=validation_score,
        blockers=blockers,
        warnings=warnings,
        reason=reason,
        checked_at=checked_at,
    )

    # Store latest
    global _LATEST_AGENT_VALIDATION
    _LATEST_AGENT_VALIDATION = result

    return result


def get_latest_agent_validation() -> AgentValidationResponse | None:
    """Get the latest agent validation result."""
    return _LATEST_AGENT_VALIDATION
