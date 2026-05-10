"""Safety and audit boundaries for DeepAgents advisory orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import re
from copy import deepcopy
from typing import Any

from app.services.deepagents_runtime.schemas import DeepAgentDecision, EvidencePack


@dataclass(frozen=True)
class DeepAgentSafetyResult:
    sanitized_inputs: dict[str, Any]
    blockers: list[str]
    warnings: list[str]


def enforce_deep_agent_safety(*, inputs: dict[str, Any], context: dict[str, Any]) -> DeepAgentSafetyResult:
    """Normalize inputs and apply conservative gates before any tool or subagent dispatch."""
    blockers: list[str] = []
    warnings: list[str] = []
    sanitized = dict(inputs or {})

    if bool(sanitized.get("allow_submit")):
        sanitized["allow_submit"] = False
        warnings.append("deep_agent_allow_submit_forced_false")

    if bool(sanitized.get("submitted_order")) or bool(sanitized.get("broker_called")):
        blockers.append("deep_agent_submit_or_broker_claim_blocked")

    return DeepAgentSafetyResult(
        sanitized_inputs=sanitized,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )


class DecisionAuditor:
    """Reject DeepAgent output that invents facts or crosses execution boundaries."""

    FORBIDDEN_ACTIONS = (
        "submit_order",
        "place_order",
        "send_order",
        "broker_called=true",
        "submitted_order=true",
        "live execution",
        "live_trade",
        "disable approval",
        "mark_active",
        "activate_strategy",
        "activate_model",
        "promote_strategy",
        "promote_model",
    )
    # The DeepAgent watchlist decision may only declare a candidate_source from
    # this list. Anything else (universe_selection, candidate_universe, default,
    # fallback, etc.) is auto-rejected because allowed_symbols can only come
    # from real scanner-linked rows.
    ALLOWED_CANDIDATE_SOURCES = frozenset({"scanner", "worker_output_scanner", "manual_request", "none"})
    FORBIDDEN_CANDIDATE_SOURCES = frozenset(
        {"universe_selection", "candidate_universe", "default", "fallback", "static_universe", "static_default"}
    )
    PRICE_KEYS_IN_RANKINGS = ("price", "last_price", "latest_price", "current_price", "close")
    COMMON_NON_SYMBOL_WORDS = frozenset(
        {
            # Tech / domain acronyms that often appear in evidence prose.
            "AI", "API", "ATR", "BPS", "BUY", "CFD", "CSV", "DATA", "DEMO", "ETF",
            "ETP", "EV", "FILL", "FX", "GAP", "HIGH", "IPO", "JSON", "LLM", "LOW",
            "MACD", "NEAR", "OHLC", "OPEN", "PASS", "PNL", "PIVOT", "PLAN", "PLUS",
            "REAL", "RISK", "ROI", "RSI", "RVOL", "SAFE", "SELL", "SMA", "STDEV",
            "TICK", "TIME", "TREND", "USD", "VAR", "VWAP", "YES", "ZONE",
            # Most common short English words; over-list rather than miss.
            "AGO", "ALL", "ALSO", "AND", "ANY", "ARE", "AS", "AT", "BACK", "BE",
            "BEEN", "BEST", "BOTH", "BUT", "BY", "CAN", "EACH", "EVEN", "EVER",
            "FOR", "FROM", "GET", "HAD", "HAS", "HAVE", "HER", "HERE", "HIM",
            "HIS", "HOW", "IF", "IN", "INTO", "IS", "IT", "ITS", "JUST", "LIKE",
            "LONG", "MADE", "MAKE", "MANY", "MAY", "ME", "MORE", "MOST", "MUST",
            "MY", "NEW", "NO", "NOT", "NOW", "OF", "OK", "OLD", "ON", "ONE",
            "ONLY", "OR", "OUR", "OUT", "OVER", "PART", "SAME", "SEE", "SEEM",
            "SHE", "SO", "SOME", "SUCH", "TAKE", "THAN", "THAT", "THE", "THEM",
            "THEN", "THEY", "THIS", "TO", "TWO", "UP", "US", "USE", "USED",
            "VERY", "WAS", "WAY", "WAYS", "WE", "WELL", "WERE", "WHAT", "WHEN",
            "WHO", "WHY", "WILL", "WITH", "WORK", "YEAR", "YOU", "YOUR",
        }
    )

    @staticmethod
    def audit(decision: DeepAgentDecision, evidence: EvidencePack) -> DeepAgentDecision:
        audited = deepcopy(decision)
        allowed = {symbol.upper() for symbol in evidence.allowed_symbols}
        text_parts = [
            audited.thesis or "",
            " ".join(audited.bull_case or []),
            " ".join(audited.bear_case or []),
            " ".join(audited.missing_evidence or []),
            " ".join(audited.risk_notes or []),
            " ".join(audited.soft_warnings or []),
            " ".join(audited.hard_blockers or []),
            audited.recommended_next_action or "",
            " ".join(audited.data_used.symbols or []),
        ]
        # Preserve original case for prose-level ticker detection — uppercase
        # prose words like "LEADS" or "GATE" would otherwise look like tickers
        # after a global ``.upper()``. A real symbol claim in prose almost
        # always already appears in uppercase.
        text_original = " ".join(text_parts)
        text_upper = text_original.upper()

        if not allowed and audited.decision in {"candidate_selected", "candidates_selected"}:
            audited.hard_blockers.append("recommendation_with_zero_candidates")
            audited.reasoning_status = "audit_rejected"
            audited.decision = "no_qualified_setup"

        for symbol in audited.data_used.symbols or []:
            sym = str(symbol).upper().strip()
            if sym and sym not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{sym}")
                audited.reasoning_status = "audit_rejected"

        for sym in re.findall(r"\b[A-Z]{2,5}\b", text_original):
            if sym in DecisionAuditor.COMMON_NON_SYMBOL_WORDS:
                continue
            if allowed and sym not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{sym}")
                audited.reasoning_status = "audit_rejected"

        known_prices = {symbol.upper(): [float(v) for v in values] for symbol, values in evidence.known_prices.items()}
        for raw_symbol, raw_price in (audited.data_used.prices or {}).items():
            sym = str(raw_symbol).upper().strip()
            try:
                price = float(raw_price)
            except (TypeError, ValueError):
                audited.hard_blockers.append(f"invented_price:{sym}:{raw_price}")
                audited.reasoning_status = "audit_rejected"
                continue
            if sym not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{sym}")
                audited.reasoning_status = "audit_rejected"
                continue
            if price not in known_prices.get(sym, []):
                audited.hard_blockers.append(f"invented_price:{sym}:{price:g}")
                audited.reasoning_status = "audit_rejected"

        if any(term in text_upper for term in ("MOCK", "SYNTHETIC", "FAKE", "DEMO DATA")):
            audited.hard_blockers.append("reasoning_referenced_non_real_data")
            audited.reasoning_status = "audit_rejected"

        for phrase in DecisionAuditor.FORBIDDEN_ACTIONS:
            if phrase.upper() in text_upper:
                audited.hard_blockers.append(f"forbidden_action:{phrase}")
                audited.reasoning_status = "audit_rejected"

        if audited.submitted_order or audited.broker_called:
            audited.hard_blockers.append("forbidden_broker_or_submit_claim")
            audited.reasoning_status = "audit_rejected"

        # Validate the structured watchlist decision fields.
        for sym in list(audited.usable_symbols or []):
            up = str(sym).upper().strip()
            if not up or up not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{up or sym}")
                audited.reasoning_status = "audit_rejected"

        for entry in list(audited.rejected_symbols or []):
            if not isinstance(entry, dict):
                audited.hard_blockers.append("rejected_symbol_entry_not_dict")
                audited.reasoning_status = "audit_rejected"
                continue
            up = str(entry.get("symbol") or "").upper().strip()
            if up and up not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{up}")
                audited.reasoning_status = "audit_rejected"

        for entry in list(audited.candidate_rankings or []):
            if not isinstance(entry, dict):
                audited.hard_blockers.append("candidate_ranking_entry_not_dict")
                audited.reasoning_status = "audit_rejected"
                continue
            up = str(entry.get("symbol") or "").upper().strip()
            if not up or up not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{up or entry.get('symbol')}")
                audited.reasoning_status = "audit_rejected"
                continue
            for price_key in DecisionAuditor.PRICE_KEYS_IN_RANKINGS:
                if price_key not in entry:
                    continue
                try:
                    price = float(entry[price_key])
                except (TypeError, ValueError):
                    audited.hard_blockers.append(f"invented_price:{up}:{entry[price_key]}")
                    audited.reasoning_status = "audit_rejected"
                    continue
                if price not in known_prices.get(up, []):
                    audited.hard_blockers.append(f"invented_price:{up}:{price:g}")
                    audited.reasoning_status = "audit_rejected"

        # Validate candidate_source explicitly. ``None``/empty/"none" are fine.
        cs_raw = (audited.candidate_source or "").strip().lower() if isinstance(audited.candidate_source, str) else ""
        if cs_raw in DecisionAuditor.FORBIDDEN_CANDIDATE_SOURCES:
            audited.hard_blockers.append(f"forbidden_candidate_source:{cs_raw}")
            audited.reasoning_status = "audit_rejected"
        elif cs_raw and cs_raw not in DecisionAuditor.ALLOWED_CANDIDATE_SOURCES:
            audited.hard_blockers.append(f"forbidden_candidate_source:{cs_raw}")
            audited.reasoning_status = "audit_rejected"

        # The agent must never claim candidates exist when allowed_symbols is empty.
        if not allowed and (
            audited.usable_symbols or audited.candidate_rankings or audited.rejected_symbols
        ):
            audited.hard_blockers.append("agent_invented_candidates_with_zero_evidence")
            audited.reasoning_status = "audit_rejected"

        if audited.agent_key == "alpha_engine_agent":
            DecisionAuditor._audit_alpha_decision(audited, evidence, allowed, known_prices, text_upper)
        if audited.agent_key == "small_account_feasibility_agent":
            DecisionAuditor._audit_account_feasibility_decision(audited, evidence, allowed, text_upper)

        audited.submitted_order = False
        audited.broker_called = False
        audited.llm_used_for_trade_decision = False
        if audited.reasoning_status == "audit_rejected":
            audited.decision = "no_qualified_setup" if not allowed else "blocked"
            audited.confidence = 0.0
            audited.hard_blockers = sorted(set(audited.hard_blockers))
            audited.soft_warnings = sorted(set(audited.soft_warnings + ["deepagent_reasoning_audit_rejected"]))
            # Strip agentic decisions: the rejected output must never become the watchlist result.
            audited.usable_symbols = []
            audited.rejected_symbols = []
            audited.candidate_rankings = []
            audited.candidate_source = "none"
            audited.symbol = None
            audited.strategy_key = None
            audited.setup_type = None
            audited.entry_plan = {}
            audited.recommendation_id = None
            audited.predicted_return_pct = None
            audited.predicted_return_r = None
            audited.predicted_win_probability = None
            audited.predicted_expected_value_r = None
            audited.prediction_horizon_minutes = None
            audited.prediction_model_key = None
            audited.prediction_reason = None
            audited.account_feasibility_decision = None
            audited.small_account_decision = None
            audited.fractional_feasible = None
            audited.fractional_trading_enabled = None
            audited.position_size_shares = None
            audited.position_size_notional = None
            audited.risk_dollars = None
            audited.risk_per_share = None
            audited.max_loss_if_stopped = None
            audited.expected_profit_dollars = None
            audited.expected_value_dollars = None
            audited.notional_usage_pct = None
            audited.buying_power_usage_pct = None
            audited.liquidity_participation_pct = None
            audited.spread_cost_estimate = None
            audited.slippage_cost_estimate = None
            audited.expected_r_after_costs = None
            audited.feasible_symbols = []
            audited.infeasible_symbols = []
        return audited

    @staticmethod
    def _collect_strategy_keys(value: Any) -> set[str]:
        keys: set[str] = set()
        if isinstance(value, str) and value.strip():
            keys.add(value.strip())
        elif isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str) and key.strip() and key.endswith("_v1"):
                    keys.add(key.strip())
                if key in {"strategy_key", "selected_strategy_key", "alpha_strategy_key"} and isinstance(item, str) and item.strip():
                    keys.add(item.strip())
                else:
                    keys.update(DecisionAuditor._collect_strategy_keys(item))
        elif isinstance(value, list):
            for item in value:
                keys.update(DecisionAuditor._collect_strategy_keys(item))
        return keys

    @staticmethod
    def _has_trained_model_evidence(evidence: EvidencePack, symbol: str | None, strategy_key: str | None) -> bool:
        registry = evidence.model_registry or {}
        raw = registry.get("trained_model_evidence")
        if raw is True:
            return True
        if isinstance(raw, dict):
            candidates = ["global"]
            if symbol:
                candidates.extend([symbol, symbol.upper()])
            if strategy_key:
                candidates.append(strategy_key)
            if any(bool(raw.get(key)) for key in candidates):
                return True
        selected = registry.get("selected_model_key")
        selected_many = registry.get("selected_model_keys")
        if isinstance(selected, str) and selected.strip():
            return True
        if isinstance(selected_many, list) and any(str(item).strip() for item in selected_many):
            return True
        return False

    @staticmethod
    def _audit_alpha_decision(
        audited: DeepAgentDecision,
        evidence: EvidencePack,
        allowed: set[str],
        known_prices: dict[str, list[float]],
        text_upper: str,
    ) -> None:
        symbol = str(audited.symbol or "").upper().strip()
        if audited.decision == "candidate_selected":
            if not symbol:
                audited.hard_blockers.append("alpha_selected_symbol_missing")
                audited.reasoning_status = "audit_rejected"
            elif symbol not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{symbol}")
                audited.reasoning_status = "audit_rejected"
        elif symbol and symbol not in allowed:
            audited.hard_blockers.append(f"hallucinated_symbol:{symbol}")
            audited.reasoning_status = "audit_rejected"

        if not allowed and (symbol or audited.strategy_key or audited.entry_plan):
            audited.hard_blockers.append("alpha_recommendation_with_zero_candidates")
            audited.reasoning_status = "audit_rejected"

        strategy_key = str(audited.strategy_key or "").strip()
        if strategy_key:
            allowed_strategy_keys = DecisionAuditor._collect_strategy_keys(evidence.strategy_registry)
            if strategy_key not in allowed_strategy_keys:
                audited.hard_blockers.append(f"unknown_strategy_key:{strategy_key}")
                audited.reasoning_status = "audit_rejected"

        entry_plan = audited.entry_plan if isinstance(audited.entry_plan, dict) else {}
        if entry_plan:
            if not symbol or symbol not in allowed:
                audited.hard_blockers.append("alpha_entry_plan_without_allowed_symbol")
                audited.reasoning_status = "audit_rejected"
            for price_key in ("entry", "stop", "target"):
                raw_price = entry_plan.get(price_key)
                if raw_price is None:
                    continue
                try:
                    price = float(raw_price)
                except (TypeError, ValueError):
                    audited.hard_blockers.append(f"invented_price:{symbol}:{raw_price}")
                    audited.reasoning_status = "audit_rejected"
                    continue
                if symbol and price not in known_prices.get(symbol, []):
                    audited.hard_blockers.append(f"invented_price:{symbol}:{price:g}")
                    audited.reasoning_status = "audit_rejected"

        prediction_model_key = str(audited.prediction_model_key or "").strip()
        claims_trained_model = (
            bool(prediction_model_key and prediction_model_key != "heuristic_alpha_v1")
            or "TRAINED MODEL" in text_upper
            or "MODEL INFERENCE" in text_upper
        )
        if claims_trained_model and not DecisionAuditor._has_trained_model_evidence(evidence, symbol or None, strategy_key or None):
            audited.hard_blockers.append("trained_model_claim_without_evidence")
            audited.reasoning_status = "audit_rejected"

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _numbers_close(left: Any, right: Any, *, rel_tol: float = 0.002, abs_tol: float = 0.01) -> bool:
        lval = DecisionAuditor._float_or_none(left)
        rval = DecisionAuditor._float_or_none(right)
        if lval is None and rval is None:
            return True
        if lval is None or rval is None:
            return False
        return abs(lval - rval) <= max(abs_tol, abs(rval) * rel_tol)

    @staticmethod
    def _audit_account_feasibility_decision(
        audited: DeepAgentDecision,
        evidence: EvidencePack,
        allowed: set[str],
        text_upper: str,
    ) -> None:
        tool = evidence.tool_result or {}
        if not tool:
            audited.hard_blockers.append("missing_fractional_sizing_tool_result")
            audited.reasoning_status = "audit_rejected"
            return

        symbol = str(audited.symbol or "").upper().strip()
        alpha = evidence.alpha_recommendation or {}
        alpha_symbol = str(alpha.get("symbol") or "").upper().strip()
        if not symbol:
            symbol = alpha_symbol
        if symbol:
            if symbol not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{symbol}")
                audited.reasoning_status = "audit_rejected"
            elif alpha_symbol and symbol != alpha_symbol:
                audited.hard_blockers.append(f"feasibility_symbol_changed_from_alpha:{symbol}")
                audited.reasoning_status = "audit_rejected"

        tool_decision = str(tool.get("account_feasibility_decision") or "").strip().lower()
        agent_account_decision = str(audited.account_feasibility_decision or "").strip().lower()
        if agent_account_decision and tool_decision and agent_account_decision != tool_decision:
            audited.hard_blockers.append("account_feasibility_decision_contradicts_tool_result")
            audited.reasoning_status = "audit_rejected"

        if audited.decision == "feasible" and tool_decision == "blocked":
            audited.hard_blockers.append("feasible_decision_contradicts_blocked_tool_result")
            audited.reasoning_status = "audit_rejected"
        if audited.decision in {"infeasible", "blocked"} and tool_decision in {"feasible", "degraded"}:
            audited.hard_blockers.append("infeasible_decision_contradicts_feasible_tool_result")
            audited.reasoning_status = "audit_rejected"

        if audited.decision in {"infeasible", "blocked"} and (
            "PRICE TOO HIGH" in text_upper
            or "SHARE PRICE TOO HIGH" in text_upper
            or any("price" in str(item).lower() and "high" in str(item).lower() for item in audited.hard_blockers)
        ) and tool_decision in {"feasible", "degraded"}:
            audited.hard_blockers.append("blocked_solely_because_share_price_high")
            audited.reasoning_status = "audit_rejected"

        for field in (
            "position_size_shares",
            "position_size_notional",
            "risk_dollars",
            "risk_per_share",
            "max_loss_if_stopped",
            "expected_profit_dollars",
            "expected_value_dollars",
            "notional_usage_pct",
            "buying_power_usage_pct",
            "liquidity_participation_pct",
            "spread_cost_estimate",
            "slippage_cost_estimate",
            "expected_r_after_costs",
        ):
            actual = getattr(audited, field)
            if actual is None or field not in tool:
                continue
            if not DecisionAuditor._numbers_close(actual, tool.get(field)):
                audited.hard_blockers.append(f"{field}_contradicts_fractional_sizing_tool")
                audited.reasoning_status = "audit_rejected"

        for field in ("fractional_feasible", "fractional_trading_enabled"):
            actual = getattr(audited, field)
            if actual is not None and field in tool and bool(actual) != bool(tool.get(field)):
                audited.hard_blockers.append(f"{field}_contradicts_fractional_sizing_tool")
                audited.reasoning_status = "audit_rejected"

        alpha_entry_plan = alpha.get("entry_plan") if isinstance(alpha.get("entry_plan"), dict) else {}
        entry_plan = audited.entry_plan if isinstance(audited.entry_plan, dict) else {}
        for price_key in ("entry", "stop", "target"):
            if price_key not in entry_plan or entry_plan.get(price_key) is None:
                continue
            if price_key not in alpha_entry_plan or alpha_entry_plan.get(price_key) is None:
                audited.hard_blockers.append(f"feasibility_{price_key}_not_in_alpha_evidence")
                audited.reasoning_status = "audit_rejected"
                continue
            if not DecisionAuditor._numbers_close(entry_plan.get(price_key), alpha_entry_plan.get(price_key)):
                audited.hard_blockers.append(f"feasibility_{price_key}_changed_from_alpha_evidence")
                audited.reasoning_status = "audit_rejected"
