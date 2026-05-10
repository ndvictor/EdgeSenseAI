from __future__ import annotations

from app.services.strategy_registry.models import (
    DayTradingStrategyDefinition,
    PromotionRequirements,
)

_DEFAULT_PROMOTION = PromotionRequirements()

_STRATEGIES: dict[str, DayTradingStrategyDefinition] = {
    "relative_volume_momentum_breakout_v1": DayTradingStrategyDefinition(
        strategy_key="relative_volume_momentum_breakout_v1",
        display_name="Relative Volume Momentum Breakout v1",
        setup_type="rvol_momentum_breakout",
        allowed_sessions=["regular"],
        min_price=5.0,
        max_price=500.0,
        max_spread_bps=15.0,
        min_relative_volume=2.0,
        min_avg_dollar_volume=5_000_000.0,
        requires_vwap=True,
        entry_logic_summary=(
            "Enter long when price breaks above a recent resistance or prior swing high with "
            "relative volume materially above baseline while trend context aligns (higher lows "
            "into the breakout). Confirm liquidity is adequate via spread and dollar volume gates."
        ),
        stop_logic_summary=(
            "Stop below the breakout level by a buffer sized to invalidation (e.g., reclaim "
            "below triggered structure or VWAP if VWAP was used as confirmation)."
        ),
        target_logic_summary=(
            "Scale at measured extensions and/or declining RVOL; trail using structure or VWAP "
            "loss as momentum fades intraday."
        ),
        rejection_rules=[
            "Relative volume below minimum gate.",
            "Spread wider than max_spread_bps after halts or fast markets.",
            "Breakout on negligible dollar volume (liquidity trap risk).",
            "Opening drive without stabilization when filters require regular session quality.",
        ],
        required_features=[
            "relative_volume",
            "volume_vs_baseline",
            "spread_bps",
            "last_price",
            "high_low_range",
            "vwap_distance",
            "intraday_structure_break_level",
        ],
        small_account_notes=[
            "Prefer names with tight spreads; wide spreads dominate small size outcomes.",
            "Avoid chasing vertical spikes; wait for pullback retest when RVOL remains elevated.",
        ],
        promotion_requirements=_DEFAULT_PROMOTION,
    ),
    "vwap_pullback_continuation_v1": DayTradingStrategyDefinition(
        strategy_key="vwap_pullback_continuation_v1",
        display_name="VWAP Pullback Continuation v1",
        setup_type="vwap_pullback_continuation",
        allowed_sessions=["regular"],
        min_price=7.0,
        max_price=500.0,
        max_spread_bps=12.0,
        min_relative_volume=1.5,
        min_avg_dollar_volume=8_000_000.0,
        requires_vwap=True,
        entry_logic_summary=(
            "After an identifiable intraday trend or momentum impulse, enter on a controlled "
            "pullback toward VWAP (or a measured retracement) that holds VWAP support on rising "
            "bid depth / constructive tape, then resumes in the trade direction."
        ),
        stop_logic_summary=(
            "Stop if VWAP is lost on a closing basis for the entry timeframe or if structure "
            "invalidates (lower high after entry for longs)."
        ),
        target_logic_summary=(
            "Partial at prior swing extension; remainder trails with VWAP or micro-structure "
            "until time stop or end-of-day flatten per risk policy."
        ),
        rejection_rules=[
            "VWAP unavailable or stale.",
            "Pullback is a distribution pivot (lower highs, rising offers) rather than orderly.",
            "Spread expansion persists beyond max_spread_bps.",
        ],
        required_features=[
            "vwap",
            "vwap_distance",
            "pullback_depth_pct",
            "relative_volume",
            "spread_bps",
            "intraday_trend_state",
        ],
        small_account_notes=[
            "Continuations often offer better reward/risk than blind breakouts; still watch fees vs tick size.",
            "Skip midday chop when VWAP slope flattens and RVOL dies.",
        ],
        promotion_requirements=_DEFAULT_PROMOTION,
    ),
    "filtered_opening_range_breakout_v1": DayTradingStrategyDefinition(
        strategy_key="filtered_opening_range_breakout_v1",
        display_name="Filtered Opening Range Breakout v1",
        setup_type="opening_range_breakout",
        allowed_sessions=["regular"],
        min_price=10.0,
        max_price=400.0,
        max_spread_bps=10.0,
        min_relative_volume=2.5,
        min_avg_dollar_volume=15_000_000.0,
        requires_vwap=True,
        entry_logic_summary=(
            "Define an opening range after the first segment of the regular session; trade "
            "breakouts only when RVOL, spread, and dollar volume filters pass and VWAP aligns "
            "with breakout direction (avoid false breaks on air pockets)."
        ),
        stop_logic_summary=(
            "Stop back inside the opening range invalidation zone or below/above the breakout "
            "candle structure with a fixed max adverse excursion cap."
        ),
        target_logic_summary=(
            "Target prior day levels / measured move from range height; reduce into climax RVOL "
            "spikes and tighten stops."
        ),
        rejection_rules=[
            "Opening range too wide vs ATR filter (event risk / gaps dominating).",
            "Breakout without confirming RVOL expansion.",
            "Immediate fade back through range on first retest when liquidity is thin.",
        ],
        required_features=[
            "opening_range_high",
            "opening_range_low",
            "opening_range_elapsed_minutes",
            "relative_volume",
            "spread_bps",
            "avg_daily_dollar_volume",
            "vwap_alignment_flag",
        ],
        small_account_notes=[
            "First-hour volatility can violate small stops; size down when spread widens.",
            "ORB quality improves when broader market correlation supports direction.",
        ],
        promotion_requirements=_DEFAULT_PROMOTION,
    ),
    "liquidity_reclaim_v1": DayTradingStrategyDefinition(
        strategy_key="liquidity_reclaim_v1",
        display_name="Liquidity Reclaim v1",
        setup_type="liquidity_reclaim",
        allowed_sessions=["regular"],
        min_price=5.0,
        max_price=500.0,
        max_spread_bps=18.0,
        min_relative_volume=1.8,
        min_avg_dollar_volume=6_000_000.0,
        requires_vwap=True,
        entry_logic_summary=(
            "Enter when price reclaims a defined intraday liquidity anchor (commonly VWAP or a "
            "prior balance area) with expanding participation and narrowing spread, suggesting "
            "failed breakdown / inventory correction."
        ),
        stop_logic_summary=(
            "Stop if reclaim fails (loss back under anchor) within the validation window or if "
            "liquidity deteriorates (spread blowout)."
        ),
        target_logic_summary=(
            "Target mean reversion toward session midpoint or prior imbalance level; scale out "
            "if participation fades."
        ),
        rejection_rules=[
            "Reclaim on low RVOL (likely noise).",
            "Anchors flicker intraday due to bad prints—require validated tape.",
            "Macro shock window with discontinuous pricing.",
        ],
        required_features=[
            "anchor_price",
            "reclaim_signal",
            "relative_volume",
            "spread_bps",
            "depth_imbalance_proxy",
            "vwap",
        ],
        small_account_notes=[
            "Reclaims are sensitive to halt/resume sequences; stand down when halts break continuity.",
        ],
        promotion_requirements=_DEFAULT_PROMOTION,
    ),
    "no_trade_v1": DayTradingStrategyDefinition(
        strategy_key="no_trade_v1",
        display_name="No Trade (Explicit Stand-down) v1",
        setup_type="explicit_no_trade",
        allowed_sessions=["premarket", "regular", "after_hours"],
        min_price=0.0,
        max_price=0.0,
        max_spread_bps=9999.0,
        min_relative_volume=0.0,
        min_avg_dollar_volume=0.0,
        requires_vwap=False,
        entry_logic_summary=(
            "Do not initiate new positions; registry entry documents conditions where the engine "
            "should remain flat (risk overlays, data quality failures, or operator-selected "
            "stand-down)."
        ),
        stop_logic_summary=(
            "Not applicable for new entries; manage existing exposure per portfolio policy only."
        ),
        target_logic_summary=(
            "Not applicable for new entries; maintain flat intraday stance until status changes."
        ),
        rejection_rules=[
            "Any inbound setup mapped to this role must not produce new risk-increasing orders.",
        ],
        required_features=[
            "risk_overlay_flags",
            "data_quality_status",
            "session_calendar_state",
        ],
        small_account_notes=[
            "Use this role to preserve capital during unclear regimes or elevated microstructure risk.",
        ],
        promotion_requirements=_DEFAULT_PROMOTION,
    ),
}


def list_strategy_keys() -> list[str]:
    return sorted(_STRATEGIES.keys())


def get_strategy(strategy_key: str) -> DayTradingStrategyDefinition | None:
    return _STRATEGIES.get(strategy_key)


def iter_strategies() -> list[DayTradingStrategyDefinition]:
    return list(_STRATEGIES.values())
