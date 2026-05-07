from __future__ import annotations

from dataclasses import dataclass

from app.services.strategy_eligibility.models import (
    AccountState,
    CheckerOutcome,
    EligibilityStatus,
    Features,
    MarketCondition,
    ProofStatus,
    StrategyCandidate,
    StrategyGroup,
    WorkflowContext,
)


@dataclass(frozen=True)
class CheckerEval:
    status: CheckerOutcome
    message: str


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    eligibility_status: EligibilityStatus
    reason: str
    requirements_passed: list[str]
    requirements_failed: list[str]
    blockers: list[str]
    warnings: list[str]
    next_action: str


def proof_status_checker(proof_status: ProofStatus, paper_status: str) -> CheckerEval:
    if proof_status == "blocked":
        return CheckerEval("fail", "Proof status is blocked.")
    if proof_status in ("proven", "paper_passed"):
        return CheckerEval("pass", f"Proof status '{proof_status}' is acceptable.")
    if proof_status in ("backtest_required", "research_only"):
        return CheckerEval("warn", f"Proof status '{proof_status}' requires additional validation.")
    return CheckerEval("warn", f"Proof status '{proof_status}' is unknown; treat as unproven.")


def data_quality_gate(data_quality: str) -> CheckerEval:
    if data_quality == "fail":
        return CheckerEval("fail", "Data quality failed; block strategy eligibility.")
    if data_quality == "warn":
        return CheckerEval("warn", "Data quality warning; prefer paper/research routes.")
    return CheckerEval("pass", "Data quality passed.")


def risk_budget_gate(risk_budget_available: bool) -> CheckerEval:
    if not risk_budget_available:
        return CheckerEval("fail", "Risk budget not available; block strategy eligibility.")
    return CheckerEval("pass", "Risk budget available.")


def liquidity_gate(liquidity_state: str) -> CheckerEval:
    if liquidity_state == "poor":
        return CheckerEval("fail", "Liquidity is poor; block strategy eligibility.")
    if liquidity_state == "unknown":
        return CheckerEval("warn", "Liquidity is unknown; prefer paper/research routes.")
    return CheckerEval("pass", f"Liquidity '{liquidity_state}' is acceptable.")


def _require(flag: bool, key: str, passed: list[str], failed: list[str]) -> None:
    if flag:
        passed.append(key)
    else:
        failed.append(key)


def _requirements_regime_aware_momentum(
    market: MarketCondition,
    features: Features,
    passed: list[str],
    failed: list[str],
) -> None:
    _require(market.data_quality == "pass", "data_quality_pass", passed, failed)
    _require(features.rvol_elevated is True, "rvol_elevated", passed, failed)
    _require(features.price_above_vwap is True or features.vwap_reclaiming is True, "vwap_structure_pass", passed, failed)
    _require(features.relative_strength_positive is True, "relative_strength_positive", passed, failed)
    _require(market.regime == "risk_on", "regime_supports_momentum", passed, failed)
    _require(features.catalyst_confirmed is True or features.volume_confirms is True, "catalyst_or_volume_confirmation", passed, failed)
    _require(market.liquidity_state in ("good", "acceptable"), "liquidity_pass", passed, failed)
    _require(features.spread_pass is True, "spread_pass", passed, failed)
    _require(features.risk_reward_pass is True, "risk_reward_pass", passed, failed)


def requirements_checker(
    strategy_group: StrategyGroup,
    market: MarketCondition,
    features: Features,
) -> tuple[CheckerEval, list[str], list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []

    if strategy_group != "regime_aware_momentum":
        warnings.append("Requirements for this strategy group are not fully implemented in v1.")
        return (CheckerEval("warn", "Strategy-group requirements not fully implemented in v1."), passed, failed, warnings)

    _requirements_regime_aware_momentum(market, features, passed, failed)
    if failed:
        return (CheckerEval("fail", f"{len(failed)} requirement(s) failed."), passed, failed, warnings)
    return (CheckerEval("pass", "All v1 requirements passed."), passed, failed, warnings)


def decide_eligibility_v1(
    *,
    workflow: WorkflowContext,
    strategy: StrategyCandidate,
    market: MarketCondition,
    features: Features,
    account: AccountState,
) -> EligibilityDecision:
    passed: list[str] = []
    failed: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    # A) Hard blockers
    if market.data_quality == "fail":
        blockers.append("data_quality_fail")
    if not account.risk_budget_available:
        blockers.append("risk_budget_unavailable")
    if not features.spread_pass:
        blockers.append("spread_fail")
    if not features.risk_reward_pass:
        blockers.append("risk_reward_fail")
    if strategy.proof_status == "blocked":
        blockers.append("proof_status_blocked")

    if blockers:
        return EligibilityDecision(
            eligible=False,
            eligibility_status="blocked",
            reason="Blocked by hard gates: " + ", ".join(blockers),
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=blockers,
            warnings=warnings,
            next_action="Address blockers before trigger monitoring.",
        )

    # D) Market open unproven
    if workflow.session == "market_open" and strategy.proof_status in ("backtest_required", "research_only", "unknown"):
        if account.paper_trading_enabled:
            return EligibilityDecision(
                eligible=False,
                eligibility_status="paper_only",
                reason="Market is open and strategy is unproven; allow paper-only validation.",
                requirements_passed=passed,
                requirements_failed=failed,
                blockers=blockers,
                warnings=warnings,
                next_action="Run paper-only validation before production trigger/execution.",
            )
        return EligibilityDecision(
            eligible=False,
            eligibility_status="blocked",
            reason="Market is open and strategy is unproven, and paper trading is disabled.",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=["paper_trading_disabled"],
            warnings=warnings,
            next_action="Enable paper trading or use adjusted research workflows.",
        )

    # B) Baseline workflow rules
    if workflow.selected_workflow == "baseline_fast_path":
        if strategy.proof_status not in ("proven", "paper_passed"):
            return EligibilityDecision(
                eligible=False,
                eligibility_status="blocked",
                reason="Baseline fast path requires proven or paper-passed proof status.",
                requirements_passed=passed,
                requirements_failed=failed,
                blockers=["proof_status_insufficient_for_baseline"],
                warnings=warnings,
                next_action="Use adjusted workflows or run paper/backtest validations.",
            )

        if not (strategy.paper_status == "passed" or strategy.proof_status == "proven"):
            warnings.append("Paper status is not passed; relying on proof status for baseline eligibility.")

        if market.data_quality != "pass":
            return EligibilityDecision(
                eligible=False,
                eligibility_status="blocked",
                reason="Baseline fast path requires data quality pass.",
                requirements_passed=passed,
                requirements_failed=failed,
                blockers=["data_quality_not_pass"],
                warnings=warnings,
                next_action="Fix data quality before baseline routing.",
            )

        if market.liquidity_state not in ("good", "acceptable"):
            return EligibilityDecision(
                eligible=False,
                eligibility_status="blocked",
                reason="Baseline fast path requires acceptable liquidity.",
                requirements_passed=passed,
                requirements_failed=failed,
                blockers=["liquidity_not_acceptable"],
                warnings=warnings,
                next_action="Wait for improved liquidity or use research/paper routes.",
            )

    # C) Adjusted workflow rules
    if workflow.selected_workflow in ("adjusted_research_path", "backtest_queue_path"):
        if strategy.requires_backtest and not strategy.already_backtested:
            return EligibilityDecision(
                eligible=False,
                eligibility_status="research_only",
                reason="Backtest required and not yet completed; research-only.",
                requirements_passed=passed,
                requirements_failed=failed,
                blockers=["backtest_required"],
                warnings=warnings,
                next_action="Queue/complete backtest before production eligibility.",
            )
        if strategy.proof_status not in ("proven", "paper_passed"):
            # Unproven strategies can be paper_only or research_only in adjusted workflows.
            status: EligibilityStatus = "paper_only" if account.paper_trading_enabled else "research_only"
            return EligibilityDecision(
                eligible=False,
                eligibility_status=status,
                reason="Adjusted workflow allows unproven strategies only in paper/research mode.",
                requirements_passed=passed,
                requirements_failed=failed,
                blockers=blockers,
                warnings=warnings,
                next_action="Run paper/research validation before production eligibility.",
            )

    # E) First production strategy requirement set
    req_eval, req_passed, req_failed, req_warnings = requirements_checker(strategy.strategy_group, market, features)
    passed.extend(req_passed)
    failed.extend(req_failed)
    warnings.extend(req_warnings)

    if strategy.strategy_group != "regime_aware_momentum":
        # v1 does not fully implement requirements for other groups.
        return EligibilityDecision(
            eligible=False,
            eligibility_status="research_only",
            reason="Strategy-group requirements not implemented for production eligibility in v1.",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=blockers,
            warnings=warnings,
            next_action="Use research workflows; extend v1 requirements to enable production eligibility.",
        )

    if req_eval.status == "fail":
        return EligibilityDecision(
            eligible=False,
            eligibility_status="blocked",
            reason="Strategy requirements failed.",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=["requirements_failed"],
            warnings=warnings,
            next_action="Fix failed requirements before trigger monitoring.",
        )

    if strategy.proof_status in ("proven", "paper_passed"):
        return EligibilityDecision(
            eligible=True,
            eligibility_status="eligible",
            reason="All requirements passed and proof status is sufficient.",
            requirements_passed=passed,
            requirements_failed=failed,
            blockers=blockers,
            warnings=warnings,
            next_action="Send eligible strategy/response to Stage 8 Trigger Monitoring.",
        )

    # Requirements pass but unproven
    status: EligibilityStatus = "paper_only" if account.paper_trading_enabled else "research_only"
    return EligibilityDecision(
        eligible=False,
        eligibility_status=status,
        reason="Requirements passed but proof status is not sufficient for production eligibility.",
        requirements_passed=passed,
        requirements_failed=failed,
        blockers=blockers,
        warnings=warnings,
        next_action="Run paper/research validation before production eligibility.",
    )

