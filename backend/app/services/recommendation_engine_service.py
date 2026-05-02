from app.schemas import ModelVote, PricePlan, Recommendation, RiskPlan, TradeRecommendation


def build_model_votes() -> list[ModelVote]:
    return [
        ModelVote(
            model="ARIMAX Directional Forecast",
            signal="bullish",
            confidence=0.74,
            explanation="Prototype forecast favors upside continuation after volume-adjusted breakout.",
        ),
        ModelVote(
            model="Kalman Trend Filter",
            signal="bullish",
            confidence=0.79,
            explanation="Adaptive trend estimate remains positive and price is not excessively extended.",
        ),
        ModelVote(
            model="GARCH Volatility Fit",
            signal="neutral",
            confidence=0.68,
            explanation="Volatility is elevated but still compatible with the proposed stop distance.",
        ),
        ModelVote(
            model="HMM Regime Filter",
            signal="bullish",
            confidence=0.71,
            explanation="Prototype regime state supports momentum trades over mean-reversion trades.",
        ),
        ModelVote(
            model="XGBoost Meta-Ranker",
            signal="bullish",
            confidence=0.83,
            explanation="Candidate ranks highest after combining momentum, liquidity, reward/risk, and account fit.",
        ),
    ]


def build_top_action_recommendation() -> TradeRecommendation:
    return TradeRecommendation(
        symbol="AMD",
        asset_class="stock",
        action="buy",
        action_label="BUY WATCHLIST",
        horizon="swing",
        confidence=0.81,
        final_score=84,
        urgency="high",
        price_plan=PricePlan(
            current_price=162.40,
            buy_zone_low=161.20,
            buy_zone_high=163.00,
            stop_loss=157.80,
            target_price=171.50,
            target_2_price=176.00,
        ),
        risk_plan=RiskPlan(
            position_size_dollars=250.0,
            max_dollar_risk=18.0,
            max_loss_percent=1.8,
            expected_return_percent=5.6,
            reward_risk_ratio=2.7,
            account_fit="feasible_for_small_account",
        ),
        model_votes=build_model_votes(),
        final_reason=(
            "AMD is the current top actionable candidate because trend, options-flow context, volatility fit, "
            "and account feasibility align. This is a research-mode recommendation contract using prototype data, "
            "not a live brokerage order."
        ),
        invalidation_rules=[
            "Do not enter if price breaks below 161.20 before entry confirmation.",
            "Exit or avoid if price closes below 157.80 stop level.",
            "Avoid if spread/liquidity deteriorates or market regime flips risk-off.",
            "Avoid chasing above 163.00 unless a new setup recalculates the buy zone.",
        ],
        risk_factors=[
            "Prototype data, not live market feed yet.",
            "Semiconductor names can reverse quickly with index weakness.",
            "Gap risk can exceed planned stop loss.",
        ],
    )


def build_alternative_recommendations() -> list[Recommendation]:
    return [
        Recommendation(
            symbol="AMD",
            asset_class="option",
            horizon="swing",
            final_decision="buy_watchlist",
            final_score=84,
            confidence=0.81,
            reward_risk_ratio=2.7,
            account_fit="feasible_for_small_account",
            model_stack=["ARIMAX", "Kalman", "GARCH", "HMM", "XGBoost"],
            reason="Top candidate after directional, trend, volatility, regime, ranking, and account-fit checks.",
            risk_factors=["prototype data", "gap risk", "sector reversal risk"],
        ),
        Recommendation(
            symbol="BTC-USD",
            asset_class="crypto",
            horizon="intraday",
            final_decision="watch_only",
            final_score=74,
            confidence=0.68,
            reward_risk_ratio=2.8,
            account_fit="risk_review",
            model_stack=["ARIMAX", "Kalman", "GARCH", "XGBoost"],
            reason="Momentum is strong but volatility regime is elevated for a small account.",
            risk_factors=["liquidation cascade", "volatility spike"],
        ),
    ]
