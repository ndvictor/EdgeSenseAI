"""
Deterministic desired-inventory registry for the Lab Platform (v1).

No database, no filesystem scan, no external calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

ALL_STAGE_NUMBERS = list(range(1, 15))
LLM_RELATED_STAGES = [5, 13, 14]
STAGES_3_THROUGH_14 = list(range(3, 15))

StatusValue = Literal[
    "present",
    "present_partial",
    "partial",
    "need_to_build",
    "need_to_build_clarify",
    "backlog",
    "unclear",
]

STATUS_LABELS: dict[str, str] = {
    "present": "Present",
    "present_partial": "Present / Partial",
    "partial": "Partial",
    "need_to_build": "Need to Build",
    "need_to_build_clarify": "Need to Build / Clarify",
    "backlog": "Backlog",
    "unclear": "Unclear",
}

STAGE_META: list[tuple[int, str, str]] = [
    (1, "Account Owner Configuration", "account_owner_configuration"),
    (2, "System Initialization & Data Intake", "system_initialization_data_intake"),
    (3, "Session Router", "session_router"),
    (4, "Market Condition Scanner", "market_condition_scanner"),
    (5, "Workflow Router", "workflow_router"),
    (6, "Watchlist Builder", "watchlist_builder"),
    (7, "Strategy Requirements & Selector", "strategy_requirements_selector"),
    (8, "Trigger Monitoring", "trigger_monitoring"),
    (9, "Execution Planner", "execution_planner"),
    (10, "Trade Execution", "trade_execution"),
    (11, "Position Monitoring", "position_monitoring"),
    (12, "Close Position", "close_position"),
    (13, "Post-Trade Evaluation", "post_trade_evaluation"),
    (14, "Learning Loop", "learning_loop"),
]

COMPONENT_CATEGORY_ORDER = [
    "Python Script",
    "AI-Agent no LLM",
    "AI-Agent + LLM",
    "ML/Statistics Model",
    "State Object",
    "UI Component",
    "Orchestrator",
]


def _expand_stages(stages: list[int] | Literal["all"]) -> list[int]:
    if stages == "all":
        return list(ALL_STAGE_NUMBERS)
    return list(stages)


def inventory_category(unit_type: str) -> str:
    """Map a unit type string to one of COMPONENT_CATEGORY_ORDER."""
    s = unit_type.strip().lower()
    if "orchestrator" in s:
        return "Orchestrator"
    if "ui component" in s:
        return "UI Component"
    if s == "state object":
        return "State Object"
    if "python script / state store" in s or ("/ state store" in s and "python script" in s):
        return "Python Script"
    if "ai-agent + llm" in s or s.startswith("ai-agent + llm"):
        return "AI-Agent + LLM"
    if "ai-agent" in s:
        return "AI-Agent no LLM"
    if "ml/statistics model" in s or "statistics model" in s:
        return "ML/Statistics Model"
    if "python script" in s:
        return "Python Script"
    return "Python Script"


def _is_present_bucket(status: StatusValue) -> bool:
    return status == "present"


def _is_partial_bucket(status: StatusValue) -> bool:
    return status in ("partial", "present_partial")


def _is_missing_bucket(status: StatusValue) -> bool:
    return status in ("need_to_build", "need_to_build_clarify", "unclear")


def _is_backlog_bucket(status: StatusValue) -> bool:
    return status == "backlog"


def _coerce_status(raw: str) -> StatusValue:
    m: dict[str, StatusValue] = {
        "present": "present",
        "present_partial": "present_partial",
        "partial": "partial",
        "need_to_build": "need_to_build",
        "need_to_build_clarify": "need_to_build_clarify",
        "backlog": "backlog",
        "unclear": "unclear",
    }
    return m[raw]


# (name, stages list or "all", unit_type, needed_for_baseline, status, uses_llm, what_it_should_do, next_action)
_UNITS_SPEC: list[tuple[str, list[int] | Literal["all"], str, bool, str, bool, str, str]] = [
    (
        "Account settings schema",
        [1],
        "Python Script",
        True,
        "present_partial",
        False,
        "Store account mode, paper/live flags, risk limits, broker settings, approval requirements.",
        "Validate against actual settings endpoint and UI wiring.",
    ),
    (
        "Risk limit config",
        [1, 7, 9, 10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Encode per-trade, daily, and position caps used by gates and execution.",
        "Align runtime settings with risk review and paper execution paths.",
    ),
    (
        "Allowed asset config",
        [1],
        "Python Script",
        True,
        "need_to_build_clarify",
        False,
        "Define tradable universes, asset classes, and exclusion rules for the account.",
        "Specify schema and source of truth for allowed symbols and asset classes.",
    ),
    (
        "Approved workflow registry",
        [1, 5],
        "Python Script",
        True,
        "need_to_build",
        False,
        "List workflows permitted for this account and how they map to routes.",
        "Author registry entries and wire to workflow router inputs.",
    ),
    (
        "Approved response/strategy registry",
        [1, 7],
        "Python Script",
        True,
        "partial",
        False,
        "Track which strategies and response templates are approved for automation.",
        "Consolidate strategy registry with approval metadata.",
    ),
    (
        "Broker mode checker",
        [1, 10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Verify paper vs live mode, broker connectivity, and safety switches.",
        "Cross-check broker mode with execution and account settings.",
    ),
    (
        "Provider key checker",
        [2],
        "Python Script",
        True,
        "present",
        False,
        "Validate configured API keys and provider reachability for data and trading.",
        "Keep key checks aligned with integration-check catalog.",
    ),
    (
        "Data source registry",
        [2],
        "Python Script",
        True,
        "present",
        False,
        "Enumerate data sources, roles, and routing for ingestion.",
        "Ensure registry matches /data-sources and ingestion status.",
    ),
    (
        "Market data connector",
        [2],
        "Python Script",
        True,
        "present_partial",
        False,
        "Pull normalized market snapshots and candles from configured providers.",
        "Close gaps between mock and live provider paths in lab validation.",
    ),
    (
        "News/catalyst connector",
        [2],
        "Python Script",
        True,
        "partial",
        False,
        "Ingest news and catalyst feeds for scanner and regime context.",
        "Harden catalyst workflows when baseline requires news.",
    ),
    (
        "Account state connector",
        [2, 11],
        "Python Script",
        True,
        "present_partial",
        False,
        "Sync balances, positions, and buying power for risk and monitoring.",
        "Validate Alpaca paper snapshot usage across monitoring stages.",
    ),
    (
        "Data ingestion status unit",
        [2],
        "Python Script",
        True,
        "present_partial",
        False,
        "Surface ingestion health, counts, and last successful pulls per source.",
        "Align summary fields with data-ingestion API contract.",
    ),
    (
        "Normalization unit",
        [2, 4],
        "Python Script",
        True,
        "present_partial",
        False,
        "Normalize provider payloads into shared schemas for downstream agents.",
        "Verify normalization coverage for all active payload types.",
    ),
    (
        "Data freshness checker",
        [2, 4],
        "Python Script",
        True,
        "present_partial",
        False,
        "Measure staleness and block workflows when data is too old.",
        "Tie freshness thresholds to session and scanner decisions.",
    ),
    (
        "Data quality checker",
        [4, 7],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Evaluate quality signals and blockers before models and gates consume data.",
        "Align agent outputs with data-quality API and command center.",
    ),
    (
        "Feature builder",
        [4],
        "Python Script",
        True,
        "present_partial",
        False,
        "Compute engineered features from snapshots for models and scanners.",
        "Confirm feature parity across symbols and providers.",
    ),
    (
        "Feature store reader/writer",
        [4, 5, 6, 7],
        "Python Script",
        True,
        "present_partial",
        False,
        "Persist and load feature rows for workflows, watchlists, and selection.",
        "Validate read/write contracts for each consuming stage.",
    ),
    (
        "Session time checker",
        [3],
        "Python Script",
        True,
        "present_partial",
        False,
        "Determine regular vs extended session and trading windows.",
        "Define session boundaries and holidays integration.",
    ),
    (
        "Market calendar checker",
        [3],
        "Python Script",
        True,
        "present_partial",
        False,
        "Apply exchange calendars, early closes, and halts.",
        "Source authoritative calendar data and caching rules.",
    ),
    (
        "Session Router Agent",
        [3],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Route the workflow based on session state, halts, and maintenance windows.",
        "Implement non-LLM routing policy with explicit state updates.",
    ),
    (
        "Market condition scanner",
        [4],
        "AI-Agent no LLM",
        True,
        "partial",
        False,
        "Scan breadth, volatility, liquidity, and stress signals for regime context.",
        "Connect scanner outputs to workflow router inputs.",
    ),
    (
        "Regime classifier",
        [4],
        "ML/Statistics Model",
        True,
        "partial",
        False,
        "Classify market regime for strategy and risk adjustments.",
        "Validate regime labels against market-regime service outputs.",
    ),
    (
        "Liquidity condition checker",
        [4, 7, 9],
        "Python Script",
        True,
        "partial",
        False,
        "Score liquidity and microstructure risk for symbols and orders.",
        "Share liquidity signals across selection and planning.",
    ),
    (
        "Volatility condition model",
        [4],
        "Statistics Model",
        True,
        "partial",
        False,
        "Estimate volatility and uncertainty for sizing and gates.",
        "Calibrate volatility outputs with live and historical windows.",
    ),
    (
        "Disorder/entropy model",
        [4, 5, 7],
        "Statistics Model",
        False,
        "backlog",
        False,
        "Measure disorder or entropy for tail-risk and workflow caution.",
        "Defer until baseline regime and scanner are stable.",
    ),
    (
        "Opacity/hidden pressure model",
        [4, 5, 7],
        "Statistics Model",
        False,
        "backlog",
        False,
        "Detect latent pressure or opacity risk beyond price trends.",
        "Defer until core scanner metrics are validated.",
    ),
    (
        "Workflow decision object",
        [5],
        "State Object",
        True,
        "present_partial",
        False,
        "Carry router decisions, constraints, and next-stage intents between stages.",
        "Define schema versioning and persistence for workflow traces.",
    ),
    (
        "Workflow Router Agent",
        [5],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Choose the next workflow leg using rules, proofs, and urgency (critical path).",
        "Implement critical router agent before expanding automation breadth.",
    ),
    (
        "Baseline workflow rules",
        [5],
        "Python Script",
        True,
        "present_partial",
        False,
        "Encode default transitions and guards for the baseline closed loop.",
        "Author baseline rules table and unit tests for transitions.",
    ),
    (
        "Adjusted workflow rules",
        [5],
        "Python Script",
        True,
        "present_partial",
        False,
        "Apply regime- or account-specific adjustments to baseline routing.",
        "Layer adjustments behind explicit approval and audit hooks.",
    ),
    (
        "Urgency checker",
        [5, 8],
        "Python Script",
        True,
        "present_partial",
        False,
        "Score urgency for signals, triggers, and escalations.",
        "Connect urgency to trigger monitoring and notifications.",
    ),
    (
        "Proof-status checker",
        [5, 7],
        "Python Script",
        True,
        "present_partial",
        False,
        "Verify required proofs: backtest, paper, data quality, and risk gates.",
        "Define proof artifacts and statuses consumed by the router.",
    ),
    (
        "No-trade route",
        [5, 7, 10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Short-circuit to no-trade when constraints fail.",
        "Align no-trade evaluation with existing API behavior.",
    ),
    (
        "Universe filter",
        [6],
        "Python Script",
        True,
        "present_partial",
        False,
        "Filter the tradable universe before watchlist construction.",
        "Validate universe filters with discovery and selection services.",
    ),
    (
        "Watchlist builder agent",
        [6],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Assemble watchlists from universe, signals, and ranking outputs.",
        "Tighten agent policy for edge cases and empty universes.",
    ),
    (
        "Watchlist persistence",
        [6],
        "Python Script",
        True,
        "present_partial",
        False,
        "Persist watchlists and candidate links for downstream stages.",
        "Confirm durability semantics with watchlist APIs.",
    ),
    (
        "Ranking calculator",
        [6],
        "ML/Statistics Model",
        True,
        "partial",
        False,
        "Rank candidates using model scores and tie-breakers.",
        "Document ranking inputs and reproducibility checks.",
    ),
    (
        "Candidate universe store",
        [6, 7],
        "Python Script",
        True,
        "present",
        False,
        "Hold the active candidate set feeding strategy selection.",
        "Keep store consistent with candidate-universe endpoints.",
    ),
    (
        "Response eligibility checker",
        [7],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Decide whether a response path is allowed given proofs and gates.",
        "Consolidate eligibility logic scattered across services.",
    ),
    (
        "Backtest result lookup",
        [7],
        "Python Script",
        True,
        "partial",
        False,
        "Fetch and summarize backtests for strategy approval.",
        "Normalize backtest summaries for router consumption.",
    ),
    (
        "Paper-trading status lookup",
        [7],
        "Python Script",
        True,
        "partial",
        False,
        "Read paper trading history and readiness for promotion.",
        "Align with paper-trading lifecycle APIs.",
    ),
    (
        "Data quality gate",
        [7],
        "Python Script",
        True,
        "present_partial",
        False,
        "Hard gate strategy selection on data quality thresholds.",
        "Map gate failures to explicit remediation actions.",
    ),
    (
        "Risk budget gate",
        [7, 9, 10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Enforce risk budgets before planning and execution.",
        "Synchronize gate thresholds with account risk profile.",
    ),
    (
        "Trigger rule registry",
        [8],
        "Python Script",
        True,
        "present_partial",
        False,
        "Register trigger definitions, severities, and routing.",
        "Keep registry aligned with trigger-rules endpoints.",
    ),
    (
        "Trigger monitor agent",
        [8],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Monitor live triggers and transition signals to actions.",
        "Expand monitor coverage for multi-symbol bursts.",
    ),
    (
        "Timing window checker",
        [8],
        "Python Script",
        True,
        "present_partial",
        False,
        "Validate signal validity against time windows and sessions.",
        "Clarify interaction with session router and expiration rules.",
    ),
    (
        "Signal expiration checker",
        [8],
        "Python Script",
        True,
        "present_partial",
        False,
        "Expire stale signals and prevent execution on outdated triggers.",
        "Define TTL sources and clock synchronization assumptions.",
    ),
    (
        "Execution planner agent",
        [9],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Plan orders with sizing, stops, targets, and constraints.",
        "Connect planner outputs to execution prechecks.",
    ),
    (
        "Position sizing calculator",
        [9],
        "Python Script",
        True,
        "present_partial",
        False,
        "Translate risk budget into share sizes and notional.",
        "Validate sizing against capital allocation outputs.",
    ),
    (
        "Stop/target calculator",
        [9],
        "Python Script",
        True,
        "present_partial",
        False,
        "Derive protective stops and profit targets from strategy templates.",
        "Ensure consistency with risk manager and journal fields.",
    ),
    (
        "Order type selector",
        [9],
        "Python Script",
        True,
        "present_partial",
        False,
        "Choose market vs limit and time-in-force based on liquidity and urgency.",
        "Document selection policy and broker capability matrix.",
    ),
    (
        "Slippage/spread calculator",
        [9, 10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Estimate execution costs for planning and post-trade review.",
        "Calibrate on live paper fills when available.",
    ),
    (
        "Execution safety gate",
        [10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Block unsafe orders before submission.",
        "Align with execution precheck and audit requirements.",
    ),
    (
        "Human approval gate",
        [10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Require explicit human approval for sensitive orders.",
        "Verify approval workflow with execution audit records.",
    ),
    (
        "Broker paper order adapter",
        [10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Submit and normalize paper orders to the broker API.",
        "Cover idempotency and error mapping in the adapter.",
    ),
    (
        "Live trading blocker",
        [10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Prevent live submissions while lab and paper policies apply.",
        "Reassert blocker on every execution path.",
    ),
    (
        "Order status poller",
        [10, 11],
        "Python Script",
        True,
        "need_to_build_clarify",
        False,
        "Poll broker order status until terminal states.",
        "Clarify polling cadence vs webhooks for paper accounts.",
    ),
    (
        "Position monitor agent",
        [11],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Track open positions against plans and triggers.",
        "Align with live-watchlist and position monitoring UI.",
    ),
    (
        "PnL calculator",
        [11],
        "Python Script",
        True,
        "present_partial",
        False,
        "Compute unrealized and realized PnL for monitoring.",
        "Reconcile PnL with broker snapshots.",
    ),
    (
        "Thesis validity checker",
        [11],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Decide if the original thesis still holds while a position is open.",
        "Define thesis representation and invalidation rules.",
    ),
    (
        "Position risk monitor",
        [11],
        "Python Script",
        True,
        "present_partial",
        False,
        "Monitor concentration, gap, and stop distance risks.",
        "Feed risk monitor outputs to exit and alert paths.",
    ),
    (
        "Exit rule evaluator",
        [12],
        "Python Script",
        True,
        "present_partial",
        False,
        "Evaluate automated exit rules against live position state.",
        "Clarify precedence between manual, rule-based, and agent exits.",
    ),
    (
        "Close position agent",
        [12],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Orchestrate close decisions when exits trigger.",
        "Tighten coordination with exit evaluator and broker adapter.",
    ),
    (
        "Close order builder",
        [12],
        "Python Script",
        True,
        "present_partial",
        False,
        "Build closing orders with constraints and partial exit support.",
        "Validate builder outputs against broker min qty and lot rules.",
    ),
    (
        "Trade journal writer",
        [13],
        "Python Script",
        True,
        "present_partial",
        False,
        "Persist structured trade records for review and learning.",
        "Align journal schema with outcomes and attribution inputs.",
    ),
    (
        "Outcome labeler",
        [13],
        "AI-Agent no LLM",
        True,
        "present_partial",
        False,
        "Label trade outcomes for performance tracking.",
        "Standardize labels across paper and journal pipelines.",
    ),
    (
        "Performance attribution calculator",
        [13],
        "Statistics Model",
        True,
        "present_partial",
        False,
        "Attribute PnL to signals, strategies, and regimes.",
        "Document attribution methodology for audits.",
    ),
    (
        "Post-trade explanation agent",
        [13],
        "AI-Agent + LLM",
        False,
        "need_to_build_clarify",
        True,
        "Optional LLM narrative explaining post-trade outcomes.",
        "Gate optional LLM usage behind budget and policy.",
    ),
    (
        "Learning metrics updater",
        [14],
        "Python Script",
        True,
        "present_partial",
        False,
        "Update rolling metrics that feed learning loop decisions.",
        "Connect metrics to research priority and drift signals.",
    ),
    (
        "Drift detector",
        [14],
        "Statistics Model",
        True,
        "present_partial",
        False,
        "Detect performance or feature drift for models and strategies.",
        "Validate drift thresholds with historical baselines.",
    ),
    (
        "Promotion/demotion rules",
        [14],
        "Python Script",
        True,
        "present_partial",
        False,
        "Define when strategies or models promote between lab, paper, and prod.",
        "Clarify governance and manual approval steps.",
    ),
    (
        "Learning loop agent",
        [14],
        "AI-Agent no LLM + optional LLM",
        True,
        "present_partial",
        True,
        "Close the loop from outcomes to research tasks and adjustments.",
        "Keep non-LLM path primary; LLM assistance optional.",
    ),
    (
        "Learning loop LLM reviewer",
        [14],
        "AI-Agent + LLM",
        False,
        "backlog",
        True,
        "Optional LLM review of learning proposals and narratives.",
        "Defer until core learning metrics are stable.",
    ),
    (
        "Audit logger",
        "all",
        "Python Script",
        True,
        "partial",
        False,
        "Emit immutable audit records for sensitive actions across stages.",
        "Unify audit payloads across execution and workflow events.",
    ),
    (
        "Workflow trace store",
        "all",
        "Python Script / State Store",
        True,
        "partial",
        False,
        "Store workflow traces and decision graphs for replay.",
        "Define retention and redaction for trace payloads.",
    ),
    (
        "Alert/notification sender",
        [8, 11, 14],
        "Python Script",
        False,
        "need_to_build_clarify",
        False,
        "Send alerts for triggers, risk, and learning outcomes.",
        "Choose channels and escalation after baseline monitoring stabilizes.",
    ),
    (
        "LLM gateway/cost controller",
        LLM_RELATED_STAGES,
        "Python Script",
        True,
        "present_partial",
        False,
        "Meter, throttle, and gate paid LLM calls.",
        "Align gateway metrics with budget gate and settings.",
    ),
    (
        "Workflow explanation prompt",
        [5, 13, 14],
        "AI-Agent + LLM",
        False,
        "need_to_build",
        True,
        "Optional prompts producing human-readable workflow explanations.",
        "Keep prompts versioned and policy-tagged.",
    ),
    (
        "LangGraph workflow shell",
        STAGES_3_THROUGH_14,
        "Orchestrator",
        False,
        "unclear",
        False,
        "Orchestrate stages 3–14 with a durable graph runtime.",
        "Clarify graph boundaries vs existing FastAPI services.",
    ),
    (
        "UI workflow dashboard",
        "all",
        "UI Component",
        True,
        "need_to_build",
        False,
        "Single place to visualize stage state, proofs, and blockers.",
        "Design dashboard layout mapped to the fourteen-stage model.",
    ),
    # v1 workflow spine support — rankers + Qlib adapters (inventory-only)
    (
        "Strategy Ranker",
        [6, 7],
        "Python Script",
        True,
        "need_to_build",
        False,
        "Rank strategy candidates by regime fit, proof status, recent performance, risk, and eligibility.",
        "Implement deterministic ranking inputs and scoring rubric.",
    ),
    (
        "Model Ranker",
        "all",
        "Python Script",
        False,
        "need_to_build",
        False,
        "Rank models by backtest score, paper performance, drift, confidence, and sample size.",
        "Implement deterministic model ranking and surface in research workflows.",
    ),
    (
        "Qlib Integration Adapter",
        "all",
        "Python Script",
        False,
        "need_to_build",
        False,
        "Expose Qlib research/backtest/model outputs to the workflow in a stable schema.",
        "Define adapter contract and mapping for Qlib artifacts.",
    ),
    (
        "Qlib Signal Score Adapter",
        [6, 7],
        "Python Script",
        False,
        "need_to_build",
        False,
        "Convert Qlib model outputs into ranked stock candidates for Stage 6/7 inputs.",
        "Define candidate score schema and integrate with candidate engine.",
    ),
    (
        "Stage 9 → 10 Safe Precheck Handoff",
        [9, 10],
        "Python Script",
        True,
        "present_partial",
        False,
        "Convert Stage 9 execution plans into Stage 10 precheck-only requests (no submission).",
        "Keep handoff offline and strictly no-submit; ensure contract tests remain stable.",
    ),
    (
        "Workflow Runbook aggregator",
        "all",
        "Python Script",
        False,
        "present_partial",
        False,
        "Read-only end-to-end workflow spine status aggregator for visibility/control.",
        "Add frontend runbook/dashboard visibility after backend endpoints are stable.",
    ),
    (
        "Agent Runtime Foundation",
        "all",
        "Python Script",
        True,
        "present_partial",
        False,
        "Phase 0/1 foundation: shared agent contracts, registry, workflow run records, agent run traces, and idempotency. Does not execute tools until Phase 2 wrappers.",
        "Implement Phase 2 agent wrappers that call stage services safely.",
    ),
]


def _build_desired_units() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(_UNITS_SPEC, start=1):
        name, stages_raw, unit_type, baseline, status_s, uses_llm, what, next_action = row
        stages = _expand_stages(stages_raw)
        st = _coerce_status(status_s)
        unit_id = f"unit_{i:03d}"
        out.append(
            {
                "unit_id": unit_id,
                "name": name,
                "stage_numbers": stages,
                "type": unit_type,
                "needed_for_baseline": baseline,
                "status": st,
                "status_label": STATUS_LABELS[st],
                # legacy fields (kept for UI)
                "tested_status": "unknown",
                "promotion_status": "lab",
                "uses_llm": uses_llm,
                "what_it_should_do": what,
                "required_components": [],
                "next_action": next_action,
                # new reconciliation fields (v1)
                "implementation_status": st,
                "backend_status": "missing",
                "frontend_status": "missing",
                "test_status": "untested",
                "route": None,
                "endpoint_family": None,
                "notes": [],
            }
        )
    _apply_inventory_overrides(out)
    return out


def _apply_inventory_overrides(units: list[dict[str, Any]]) -> None:
    """Patch unit metadata to reflect completed v1 workflow spine reality.

    This is inventory-only reconciliation. It must not probe runtime, call external services, or mutate other state.
    """

    # Helper to apply per-unit updates by unit name.
    def apply(
        name: str,
        *,
        backend: str | None = None,
        frontend: str | None = None,
        test: str | None = None,
        implementation_status: str | None = None,
        route: str | None = None,
        endpoint_family: str | None = None,
        notes: list[str] | None = None,
    ) -> None:
        u = next((x for x in units if x.get("name") == name), None)
        if u is None:
            return
        if backend is not None:
            u["backend_status"] = backend
        if frontend is not None:
            u["frontend_status"] = frontend
        if test is not None:
            u["test_status"] = test
            u["tested_status"] = "tested" if test == "tested" else "unknown"
        if implementation_status is not None:
            u["implementation_status"] = _coerce_status(implementation_status)
        if route is not None:
            u["route"] = route
        if endpoint_family is not None:
            u["endpoint_family"] = endpoint_family
        if notes is not None:
            u["notes"] = notes

    # Completed workflow spine (backend + frontend visibility + contract tests exist).
    completed_v1 = {
        "Session time checker": ("/session-router", "/api/session-router"),
        "Market calendar checker": ("/session-router", "/api/session-router"),
        "Session Router Agent": ("/session-router", "/api/session-router"),
        "Workflow Router Agent": ("/workflow-router", "/api/workflow-router"),
        "Baseline workflow rules": ("/workflow-router", "/api/workflow-router"),
        "Adjusted workflow rules": ("/workflow-router", "/api/workflow-router"),
        "Urgency checker": ("/workflow-router", "/api/workflow-router"),
        "Proof-status checker": ("/workflow-router", "/api/workflow-router"),
        "Response eligibility checker": ("/strategy-eligibility", "/api/strategy-eligibility"),
        "Data quality gate": ("/strategy-eligibility", "/api/strategy-eligibility"),
        "Risk budget gate": ("/strategy-eligibility", "/api/strategy-eligibility"),
        "Trigger rule registry": ("/trigger-monitoring", "/api/trigger-monitoring"),
        "Trigger monitor agent": ("/trigger-monitoring", "/api/trigger-monitoring"),
        "Timing window checker": ("/trigger-monitoring", "/api/trigger-monitoring"),
        "Signal expiration checker": ("/trigger-monitoring", "/api/trigger-monitoring"),
        "Execution planner agent": ("/execution-planner", "/api/execution-planner"),
        "Position sizing calculator": ("/execution-planner", "/api/execution-planner"),
        "Stop/target calculator": ("/execution-planner", "/api/execution-planner"),
        "Order type selector": ("/execution-planner", "/api/execution-planner"),
        "Slippage/spread calculator": ("/execution-planner", "/api/execution-planner"),
        "Position monitor agent": ("/position-monitoring", "/api/position-monitoring"),
        "PnL calculator": ("/position-monitoring", "/api/position-monitoring"),
        "Thesis validity checker": ("/position-monitoring", "/api/position-monitoring"),
        "Position risk monitor": ("/position-monitoring", "/api/position-monitoring"),
        "Exit rule evaluator": ("/close-position", "/api/close-position"),
        "Close position agent": ("/close-position", "/api/close-position"),
        "Close order builder": ("/close-position", "/api/close-position"),
        "Outcome labeler": ("/post-trade-evaluation", "/api/post-trade-evaluation"),
        "Performance attribution calculator": ("/post-trade-evaluation", "/api/post-trade-evaluation"),
        "Learning metrics updater": ("/learning-loop", "/api/learning-loop"),
        "Drift detector": ("/learning-loop", "/api/learning-loop"),
        "Promotion/demotion rules": ("/learning-loop", "/api/learning-loop"),
        "Learning loop agent": ("/learning-loop", "/api/learning-loop"),
        "Stage 9 → 10 Safe Precheck Handoff": ("/execution-planner", "/api/execution-planner/precheck-handoff"),
    }

    for unit_name, (ui_route, ep) in completed_v1.items():
        apply(
            unit_name,
            backend="present",
            frontend="present",
            test="tested",
            implementation_status="present_partial",
            route=ui_route,
            endpoint_family=ep,
            notes=["Reconciled: backend+frontend+contract tests present (v1)."],
        )

    # Workflow runbook: backend + tests only (frontend not implemented here)
    apply(
        "Workflow Runbook aggregator",
        backend="present",
        frontend="missing",
        test="tested",
        implementation_status="present_partial",
        route=None,
        endpoint_family="/api/workflow-runbook",
        notes=["Backend runbook endpoints added; frontend dashboard not yet built."],
    )

    # Agent runtime foundation: backend + tests only; no frontend in this pass.
    apply(
        "Agent Runtime Foundation",
        backend="present",
        frontend="missing",
        test="tested",
        implementation_status="present_partial",
        route=None,
        endpoint_family="/api/agent-runtime",
        notes=[
            "Phase 0/1/2: contracts + deterministic tool-calling wrappers + traces + idempotency.",
            "Postgres best-effort persistence (source of truth when available); memory fallback when unavailable.",
            "Redis runtime contract added for locks/idempotency cache/active workflow hot state (optional; non-blocking when unavailable).",
            "No broker calls, no execution submit, no LLM.",
        ],
    )

    apply(
        "Agent Wrapper Runtime",
        backend="present",
        frontend="missing",
        test="tested",
        implementation_status="present_partial",
        route=None,
        endpoint_family="/api/agent-runtime",
        notes=[
            "Phase 2: wraps Stage 3/5/7/8/9/11/12/13/14 services as tool-calling deterministic agents.",
            "Safety: stock-only + day-trading-only; allow_submit forced false; never submits orders; no LLM.",
        ],
    )

    apply(
        "Agent Runtime Persistence",
        backend="present",
        frontend="missing",
        test="tested",
        implementation_status="present_partial",
        route=None,
        endpoint_family="/api/agent-runtime",
        notes=[
            "Postgres is source of truth for workflow runs, agent runs, traces, and idempotency when available.",
            "Redis optional hot state (locks, active workflow state cache, idempotency cache acceleration).",
            "Memory-only is fallback mode when Postgres/Redis are unavailable; startup/tests must not require either.",
        ],
    )


def _summarize_units(units: list[dict[str, Any]]) -> dict[str, Any]:
    present = sum(1 for u in units if _is_present_bucket(u["status"]))
    partial = sum(1 for u in units if _is_partial_bucket(u["status"]))
    missing = sum(1 for u in units if _is_missing_bucket(u["status"]))
    backlog = sum(1 for u in units if _is_backlog_bucket(u["status"]))
    tested = sum(1 for u in units if u.get("tested_status") not in (None, "", "unknown"))
    untested = len(units) - tested
    ready_to_promote = sum(1 for u in units if u.get("promotion_status") == "production_ready")

    backend_present_count = sum(1 for u in units if u.get("backend_status") == "present")
    frontend_present_count = sum(1 for u in units if u.get("frontend_status") == "present")
    tested_count = sum(1 for u in units if u.get("test_status") == "tested")
    missing_count = sum(1 for u in units if u.get("backend_status") != "present" and _is_missing_bucket(u["status"]))
    needs_backend_count = sum(1 for u in units if u.get("backend_status") != "present")
    needs_frontend_count = sum(1 for u in units if u.get("backend_status") == "present" and u.get("frontend_status") != "present")
    ready_for_frontend_count = needs_frontend_count
    return {
        "total_stages": 14,
        "total_units": len(units),
        "present": present,
        "partial": partial,
        "missing": missing,
        "backlog": backlog,
        "tested": tested,
        "untested": untested,
        "ready_to_promote": ready_to_promote,
        # new summary fields for clearer reconciliation
        "backend_present_count": backend_present_count,
        "frontend_present_count": frontend_present_count,
        "tested_count": tested_count,
        "missing_count": missing_count,
        "ready_for_frontend_count": ready_for_frontend_count,
        "needs_backend_count": needs_backend_count,
        "needs_frontend_count": needs_frontend_count,
        "next_action": "Review Strategy Ranker, Model Ranker, Stage 2 data quality integration, Stage 4 market condition scanner, and Stage 6 watchlist builder.",
    }


def _stage_summary_for_units(stage_units: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_units": len(stage_units),
        "present": sum(1 for u in stage_units if _is_present_bucket(u["status"])),
        "partial": sum(1 for u in stage_units if _is_partial_bucket(u["status"])),
        "missing": sum(1 for u in stage_units if _is_missing_bucket(u["status"])),
        "backlog": sum(1 for u in stage_units if _is_backlog_bucket(u["status"])),
    }


def _component_categories(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = {c: {"total": 0, "present": 0, "partial": 0, "missing": 0, "backlog": 0} for c in COMPONENT_CATEGORY_ORDER}
    for u in units:
        cat = inventory_category(u["type"])
        if cat not in buckets:
            cat = "Python Script"
        b = buckets[cat]
        b["total"] += 1
        st = u["status"]
        if _is_present_bucket(st):
            b["present"] += 1
        elif _is_partial_bucket(st):
            b["partial"] += 1
        elif _is_backlog_bucket(st):
            b["backlog"] += 1
        elif _is_missing_bucket(st):
            b["missing"] += 1
    return [{"category": k, **v} for k, v in buckets.items()]


def build_lab_inventory_response() -> dict[str, Any]:
    units = _build_desired_units()

    stages_out: list[dict[str, Any]] = []
    for stage_number, stage_name, stage_key in STAGE_META:
        stage_units = [dict(u) for u in units if stage_number in u["stage_numbers"]]
        stages_out.append(
            {
                "stage_number": stage_number,
                "stage_name": stage_name,
                "stage_key": stage_key,
                "summary": _stage_summary_for_units(stage_units),
                "units": stage_units,
            }
        )

    return {
        "status": "ok",
        "data_mode": "desired_inventory",
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": _summarize_units(units),
        "stages": stages_out,
        "component_categories": _component_categories(units),
    }
