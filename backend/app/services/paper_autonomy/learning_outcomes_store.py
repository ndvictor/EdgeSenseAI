"""In-memory list of recent paper-trade outcomes for learning_loop_agent.

Holds at most ``MAX_HISTORY`` outcomes per (strategy_key) bucket. Tests reset
this between runs.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.services.paper_autonomy.models import PaperLearningOutcome


MAX_HISTORY = 200

_MEMORY: dict[str, list[PaperLearningOutcome]] = defaultdict(list)


def reset() -> None:
    _MEMORY.clear()


def append(outcome: PaperLearningOutcome) -> PaperLearningOutcome:
    bucket = _MEMORY[outcome.strategy_key]
    bucket.append(outcome)
    if len(bucket) > MAX_HISTORY:
        del bucket[0 : len(bucket) - MAX_HISTORY]
    return outcome


def list_for_strategy(strategy_key: str, *, limit: int = 50) -> list[PaperLearningOutcome]:
    bucket = list(_MEMORY.get(strategy_key, []))
    bucket.sort(key=lambda o: o.created_at, reverse=True)
    return bucket[:limit]


def list_recent(*, limit: int = 50) -> list[PaperLearningOutcome]:
    """Return the most-recent outcomes across all strategies, newest first."""
    flat: list[PaperLearningOutcome] = []
    for bucket in _MEMORY.values():
        flat.extend(bucket)
    flat.sort(key=lambda o: o.created_at, reverse=True)
    return flat[:limit]


def list_strategy_keys() -> list[str]:
    return sorted(_MEMORY.keys())


def to_recent_outcomes_payload(strategy_key: str, *, limit: int = 50) -> list[dict[str, Any]]:
    """Format outcomes for ``LearningLoopEvaluateRequest.recent_outcomes``."""
    out: list[dict[str, Any]] = []
    for o in list_for_strategy(strategy_key, limit=limit):
        out.append(
            {
                "trade_id": o.trade_id,
                "outcome_label": o.outcome_label,
                "outcome_status": o.outcome_status,
                "realized_pnl": float(o.realized_pnl),
                "r_multiple": float(o.actual_return_r),
                "slippage_status": o.slippage_status,
                "rule_compliant": bool(o.rule_compliant),
            }
        )
    return out
