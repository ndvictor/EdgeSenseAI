from app.services.watchlist_ttl_service import assign_watchlist_ttl_minutes


def test_opening_range_breakout_shorter_ttl_first_30_minutes():
    d = assign_watchlist_ttl_minutes(
        scanner_group="opening_range_breakout_group",
        market_phase="market_open_first_30_min",
        strategy_key="opening_range_breakout",
        signal_strength=70,
        data_quality="good",
        risk_level="medium",
        research_only=False,
    )
    assert 15 <= d.ttl_minutes <= 30


def test_relative_strength_rotation_can_be_trading_day_ttl():
    d = assign_watchlist_ttl_minutes(
        scanner_group="relative_strength_rotation_group",
        market_phase="market_open",
        strategy_key="relative_strength_rotation",
        signal_strength=65,
        data_quality="good",
        risk_level="medium",
        research_only=False,
    )
    assert d.ttl_minutes >= 360


def test_low_float_breakout_is_short_ttl():
    d = assign_watchlist_ttl_minutes(
        scanner_group="low_float_breakout_group",
        market_phase="market_open",
        strategy_key="low_float_breakout",
        signal_strength=90,
        data_quality="good",
        risk_level="very_high",
        research_only=True,
    )
    assert 5 <= d.ttl_minutes <= 15

