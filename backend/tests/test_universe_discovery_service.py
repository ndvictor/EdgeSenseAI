from app.services.universe_discovery_service import UniverseDiscoverRequest, discover_universe


def test_low_float_breakout_is_research_only_and_execution_blocked():
    resp = discover_universe(
        UniverseDiscoverRequest(
            symbols=["AAPL"],
            asset_class="stock",
            horizon="day_trade",
            market_phase="market_open",
            scanner_groups=["low_float_breakout_group"],
            source="mock",
            allow_mock=True,
            small_account_mode=True,
            promote_to_candidate_universe=False,
        )
    )
    assert resp.status in ("completed", "partial")
    assert resp.research_only_candidates
    c = resp.research_only_candidates[0]
    assert c.research_only is True
    assert c.execution_allowed is False


def test_missing_bid_ask_blocks_execution_but_discovery_completes():
    # yfinance typically lacks bid/ask; that should create blockers on candidate but still return a response.
    resp = discover_universe(
        UniverseDiscoverRequest(
            symbols=["AAPL"],
            asset_class="stock",
            horizon="swing",
            market_phase="market_open",
            scanner_groups=["relative_strength_rotation_group"],
            source="yfinance",
            allow_mock=False,
            small_account_mode=True,
            promote_to_candidate_universe=False,
        )
    )
    assert resp.status in ("completed", "partial")
    assert resp.selected_watchlist or resp.rejected_candidates
    one = (resp.selected_watchlist + resp.rejected_candidates)[0]
    assert one.execution_allowed is False
    assert any("Bid/ask or spread unavailable" in b for b in one.blockers)


def test_mock_data_blocks_execution_and_adds_blocker():
    resp = discover_universe(
        UniverseDiscoverRequest(
            symbols=["AAPL"],
            asset_class="stock",
            horizon="swing",
            market_phase="market_open",
            scanner_groups=["opening_range_breakout_group"],
            source="mock",
            allow_mock=True,
            small_account_mode=True,
            promote_to_candidate_universe=False,
        )
    )
    assert resp.status in ("completed", "partial")
    one = (resp.selected_watchlist + resp.rejected_candidates + resp.research_only_candidates)[0]
    assert any("Mock data cannot be used for execution" in b for b in one.blockers)


def test_no_promotion_when_flag_false():
    resp = discover_universe(
        UniverseDiscoverRequest(
            symbols=["AAPL", "MSFT"],
            asset_class="stock",
            horizon="swing",
            market_phase="market_open",
            scanner_groups=["opening_range_breakout_group"],
            source="mock",
            allow_mock=True,
            small_account_mode=True,
            promote_to_candidate_universe=False,
        )
    )
    assert not any("Promoted" in w for w in resp.warnings)


def test_score_includes_timing_and_data_quality_adjustment():
    resp_open = discover_universe(
        UniverseDiscoverRequest(
            symbols=["AAPL"],
            asset_class="stock",
            horizon="day_trade",
            market_phase="market_open_first_30_min",
            scanner_groups=["opening_range_breakout_group"],
            source="mock",
            allow_mock=True,
            small_account_mode=True,
            promote_to_candidate_universe=False,
        )
    )
    resp_closed = discover_universe(
        UniverseDiscoverRequest(
            symbols=["AAPL"],
            asset_class="stock",
            horizon="day_trade",
            market_phase="market_closed",
            scanner_groups=["opening_range_breakout_group"],
            source="mock",
            allow_mock=True,
            small_account_mode=True,
            promote_to_candidate_universe=False,
        )
    )
    c1 = (resp_open.selected_watchlist + resp_open.rejected_candidates + resp_open.research_only_candidates)[0]
    c2 = (resp_closed.selected_watchlist + resp_closed.rejected_candidates + resp_closed.research_only_candidates)[0]
    # Not guaranteed which is larger, but should differ by phase weighting.
    assert c1.universe_score != c2.universe_score

