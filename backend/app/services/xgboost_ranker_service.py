from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RankerInputRow(BaseModel):
    symbol: str
    feature_score: float
    momentum_score: float
    rvol_score: float
    spread_quality_score: float
    trend_vs_vwap_score: float
    volatility_score: float


class RankerScore(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    score: float
    rank: int
    model_used: str
    explanation: str


class RankerRunResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    model_available: bool
    rows_scored: int
    scores: list[RankerScore]
    notes: list[str]


def run_xgboost_ranker(rows: list[RankerInputRow]) -> RankerRunResult:
    """Score candidates using XGBoost when available, with a deterministic fallback.

    This keeps the workflow functional in development even before xgboost is installed or trained models are persisted.
    """
    try:
        import numpy as np
        from xgboost import XGBRegressor

        X = np.array([
            [
                row.feature_score,
                row.momentum_score,
                row.rvol_score,
                row.spread_quality_score,
                row.trend_vs_vwap_score,
                row.volatility_score,
            ]
            for row in rows
        ])
        # Prototype labels: use composite score as weak target until true outcome labels exist.
        y = np.array([row.feature_score for row in rows])
        model = XGBRegressor(n_estimators=20, max_depth=2, learning_rate=0.1, objective="reg:squarederror")
        model.fit(X, y)
        predictions = model.predict(X)
        model_available = True
        model_used = "xgboost_prototype_fit"
    except Exception:
        predictions = [
            (row.feature_score * 0.45)
            + (row.momentum_score * 0.2)
            + (row.rvol_score * 0.15)
            + (row.spread_quality_score * 0.1)
            + (row.trend_vs_vwap_score * 0.05)
            + (row.volatility_score * 0.05)
            for row in rows
        ]
        model_available = False
        model_used = "weighted_fallback_ranker"

    ranked = sorted(zip(rows, predictions), key=lambda item: float(item[1]), reverse=True)
    scores = [
        RankerScore(
            symbol=row.symbol,
            score=round(float(score), 2),
            rank=index + 1,
            model_used=model_used,
            explanation=(
                "Ranked from engineered feature scores. Production ranker should train on target-before-stop outcomes."
            ),
        )
        for index, (row, score) in enumerate(ranked)
    ]

    return RankerRunResult(
        model_name="XGBoost Meta-Ranker",
        model_available=model_available,
        rows_scored=len(rows),
        scores=scores,
        notes=[
            "If xgboost is installed, this runs a small prototype fit using weak labels.",
            "If xgboost is unavailable, the workflow remains functional with a deterministic fallback ranker.",
            "Production training requires persisted labels from backtesting and paper-trading outcomes.",
        ],
    )
