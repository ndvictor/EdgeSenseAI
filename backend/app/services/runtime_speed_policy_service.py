from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ExecutionLane(str, Enum):
    HOT_PATH = "hot_path"
    WARM_PATH = "warm_path"
    COLD_PATH = "cold_path"


class RuntimeBudget(BaseModel):
    lane: ExecutionLane
    max_symbols_per_scan: int
    scan_interval_seconds: int
    feature_refresh_seconds: int
    model_score_interval_seconds: int
    allow_llm_in_loop: bool
    allow_network_provider_calls: bool
    latency_budget_ms: int
    notes: list[str] = Field(default_factory=list)


class RuntimeSpeedPolicyResponse(BaseModel):
    status: str
    hot_path: RuntimeBudget
    warm_path: RuntimeBudget
    cold_path: RuntimeBudget
    safety_notes: list[str]


def get_runtime_speed_policy() -> RuntimeSpeedPolicyResponse:
    return RuntimeSpeedPolicyResponse(
        status="configured",
        hot_path=RuntimeBudget(
            lane=ExecutionLane.HOT_PATH,
            max_symbols_per_scan=100,
            scan_interval_seconds=15,
            feature_refresh_seconds=30,
            model_score_interval_seconds=60,
            allow_llm_in_loop=False,
            allow_network_provider_calls=False,
            latency_budget_ms=500,
            notes=[
                "Use cached snapshots, feature rows, and deterministic rules only.",
                "Do not call LLM providers inside the fast loop.",
                "Escalate only matched candidates to slower validation lanes.",
            ],
        ),
        warm_path=RuntimeBudget(
            lane=ExecutionLane.WARM_PATH,
            max_symbols_per_scan=500,
            scan_interval_seconds=60,
            feature_refresh_seconds=120,
            model_score_interval_seconds=180,
            allow_llm_in_loop=False,
            allow_network_provider_calls=True,
            latency_budget_ms=3000,
            notes=[
                "Use provider refreshes and deeper model scoring.",
                "Keep LLM calls out of repeated loops.",
            ],
        ),
        cold_path=RuntimeBudget(
            lane=ExecutionLane.COLD_PATH,
            max_symbols_per_scan=5000,
            scan_interval_seconds=300,
            feature_refresh_seconds=900,
            model_score_interval_seconds=1800,
            allow_llm_in_loop=True,
            allow_network_provider_calls=True,
            latency_budget_ms=30000,
            notes=[
                "Use for research, backtesting, summaries, and explanations.",
                "LLM calls must remain budget gated.",
            ],
        ),
        safety_notes=[
            "Live execution remains disabled.",
            "Human approval remains required.",
            "No final decision is delegated to a model.",
            "No hidden placeholder data should be presented as source-backed.",
        ],
    )
