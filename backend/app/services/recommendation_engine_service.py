from app.schemas import ModelVote, PricePlan, Recommendation, RiskPlan, TradeRecommendation


def build_model_votes() -> list[ModelVote]:
    return []


def _unavailable_top_action() -> TradeRecommendation:
    return TradeRecommendation(
        symbol="",
        asset_class="stock",
        action="watch",
        action_label="No source-backed recommendation",
        horizon="swing",
        confidence=0.0,
        final_score=0,
        urgency="low",
        price_plan=PricePlan(
            current_price=0.0,
            buy_zone_low=0.0,
            buy_zone_high=0.0,
            stop_loss=0.0,
            target_price=0.0,
            target_2_price=0.0,
        ),
        risk_plan=RiskPlan(
            position_size_dollars=0.0,
            max_dollar_risk=0.0,
            max_loss_percent=0.0,
            expected_return_percent=0.0,
            reward_risk_ratio=0.0,
            account_fit="unavailable",
        ),
        model_votes=[],
        final_reason="No source-backed recommendation is available from this legacy service.",
        invalidation_rules=[],
        risk_factors=[],
        data_mode="source_unavailable",
    )


def build_top_action_recommendation() -> TradeRecommendation:
    return _unavailable_top_action()


def build_alternative_recommendations() -> list[Recommendation]:
    return []
