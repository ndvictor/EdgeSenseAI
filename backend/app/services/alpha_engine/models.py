from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CandidateFeatureRow(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbol: str | None
    last_price: float | None = None
    volume: float | None = None
    avg_volume: float | None = None
    relative_volume: float | None = None
    day_change_pct: float | None = None
    spread_bps: float | None = None
    vwap: float | None = None
    price_above_vwap: bool | None = None
    opening_range_high: float | None = None
    opening_range_low: float | None = None
    premarket_high: float | None = None
    premarket_low: float | None = None
    high_of_day: float | None = None
    low_of_day: float | None = None
    trend_score: float | None = None
    liquidity_score: float | None = None
    volatility_score: float | None = None
    session_state: str | None = None
    source: str = "provider"
    synthetic: bool = False
    mock: bool = False
    provider_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlphaEntryPlan(BaseModel):
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    risk_per_share: float | None = None
    risk_dollars: float | None = None
    expected_r: float | None = None
    position_size_estimate: int | None = None
    plan_type: str | None = None
    notes: list[str] = Field(default_factory=list)


class AlphaRecommendation(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    symbol: str | None = None
    strategy_key: str | None = None
    setup_type: str | None = None
    scanner_score: float | None = None
    model_score: float | None = None
    evidence_score: float | None = None
    small_account_score: float | None = None
    strategy_fit_score: float | None = None
    final_score: float | None = None
    confidence: float | None = None
    entry_plan: AlphaEntryPlan = Field(default_factory=AlphaEntryPlan)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str = ""
    mock_data_used: bool = False
    synthetic_data_used: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    llm_used_for_trade_decision: bool = False
    recommendation_id: str | None = None
    predicted_return_pct: float | None = None
    predicted_return_r: float | None = None
    predicted_win_probability: float | None = None
    predicted_expected_value_r: float | None = None
    prediction_horizon_minutes: int | None = None
    prediction_model_key: str | None = None
    prediction_reason: str | None = None


class AlphaPredictionOutcome(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    recommendation_id: str | None = None
    symbol: str | None = None
    strategy_key: str | None = None
    prediction_model_key: str | None = None
    predicted_return_pct: float | None = None
    predicted_return_r: float | None = None
    predicted_win_probability: float | None = None
    predicted_expected_value_r: float | None = None
    prediction_horizon_minutes: int | None = None
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    actual_return_pct: float | None = None
    actual_return_r: float | None = None
    max_favorable_excursion_r: float | None = None
    max_adverse_excursion_r: float | None = None
    hit_target: bool = False
    hit_stop: bool = False
    prediction_error_r: float | None = None
    evaluated_at: str = ""


class AlphaEngineRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    candidates: list[CandidateFeatureRow]
    account_equity: float = 1000.0
    max_risk_dollars: float = 5.0
    max_daily_loss_dollars: float = 15.0
    session_state: str | None = None
    market_regime: str | None = None
    proof_status_by_strategy: dict[str, Any] = Field(default_factory=dict)
    model_score_by_symbol: dict[str, float] = Field(default_factory=dict)
    evidence_score_by_strategy: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlphaCandidateScore(BaseModel):
    symbol: str
    strategy_key: str
    setup_type: str
    final_score: float
    confidence: float
    entry_plan: AlphaEntryPlan
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str
    component_scores: dict[str, float] = Field(default_factory=dict)
