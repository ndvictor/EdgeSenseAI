from app.services.market_phase_weighting_service import MarketPhaseUniverseScorer


def test_market_phase_weights_change_by_phase():
    pre = MarketPhaseUniverseScorer("pre_market")
    open30 = MarketPhaseUniverseScorer("market_open_first_30_min")
    midday = MarketPhaseUniverseScorer("midday")

    # Unequal components: different phases should yield different score due to weights.
    components = dict(
        signal_strength=90,
        volume_score=60,
        liquidity_score=70,
        regime_fit=40,
        timing_fit=85,
        risk_fit=55,
        data_quality_score=65,
        spread_penalty=0,
        stale_signal_penalty=0,
        small_account_penalty=0,
        research_only_penalty=0,
    )

    s_pre = pre.score(**components)
    s_open30 = open30.score(**components)
    s_midday = midday.score(**components)
    assert s_pre != s_open30
    assert s_open30 != s_midday


def test_score_penalties_reduce_score():
    scorer = MarketPhaseUniverseScorer("market_open")
    base = scorer.score(
        signal_strength=80,
        volume_score=80,
        liquidity_score=80,
        regime_fit=80,
        timing_fit=80,
        risk_fit=80,
        data_quality_score=80,
        spread_penalty=0,
        stale_signal_penalty=0,
        small_account_penalty=0,
        research_only_penalty=0,
    )
    penalized = scorer.score(
        signal_strength=80,
        volume_score=80,
        liquidity_score=80,
        regime_fit=80,
        timing_fit=80,
        risk_fit=80,
        data_quality_score=80,
        spread_penalty=10,
        stale_signal_penalty=10,
        small_account_penalty=10,
        research_only_penalty=10,
    )
    assert penalized < base

