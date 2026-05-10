"""Precheck steps: data quality, strategy, account, execution gates."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.effective_runtime import effective_bool
from app.execution.edgesense_execution_config import EdgeSenseExecutionConfig, load_edgesense_execution_config
from app.execution.schemas import ExecutionRequest, PrecheckStepResult, PrecheckSummary
from app.services.alpaca_paper_account_service import get_alpaca_paper_snapshot
from app.services.market_data_service import MarketDataService
from app.strategies.registry import get_strategy


def _alpaca_headers() -> dict[str, str]:
    key = os.getenv("ALPACA_API_KEY") or os.getenv("ALPACA_API_KEY_ID") or ""
    sec = os.getenv("ALPACA_SECRET_KEY") or os.getenv("ALPACA_API_SECRET_KEY") or ""
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def _paper_base() -> str:
    return (
        os.getenv("ALPACA_PAPER_TRADING_BASE_URL")
        or os.getenv("APCA_API_BASE_URL")
        or "https://paper-api.alpaca.markets"
    ).rstrip("/")


def fetch_market_clock() -> dict[str, Any]:
    base = _paper_base()
    try:
        r = requests.get(f"{base}/v2/clock", headers=_alpaca_headers(), timeout=5)
        if r.status_code >= 400:
            return {"ok": False, "error": f"http_{r.status_code}"}
        return {"ok": True, "body": r.json()}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)[:120]}


def normalize_asset_class(ac: str) -> str:
    a = ac.lower()
    if a == "etf":
        return "stock"
    return a


def run_data_quality_precheck(req: ExecutionRequest, source: str = "auto") -> PrecheckStepResult:
    blockers: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {}
    ts: dict[str, str] = {}

    md = MarketDataService()
    snap = md.get_market_snapshot(req.symbol.strip(), source=source)
    details["provider"] = snap.get("provider")
    details["data_quality"] = snap.get("data_quality")
    ts["checked_at"] = datetime.now(timezone.utc).isoformat()

    if snap.get("error"):
        blockers.append(f"market_data_error:{snap.get('error')[:80]}")
    if not snap.get("current_price"):
        blockers.append("missing_reference_price")
    if snap.get("is_mock"):
        blockers.append("non_real_market_data_not_allowed_for_execution")

    spread = snap.get("bid_ask_spread")
    if spread is None and req.order_type in {"limit", "market"}:
        warnings.append("bid_ask_spread_unavailable")

    cfg = load_edgesense_execution_config()
    if spread is not None and spread > cfg.max_spread_pct:
        blockers.append(f"spread_too_wide_{spread:.3f}")

    vol = snap.get("volume")
    if vol is not None and vol <= 0:
        warnings.append("zero_volume_reported")

    # Trading halt: not available from generic snapshot — logged only
    warnings.append("trading_halt_status_not_available_from_provider")

    return PrecheckStepResult(
        name="data_quality_precheck",
        passed=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        details=details,
        source_timestamps=ts,
    )


def run_strategy_eligibility_precheck(req: ExecutionRequest) -> PrecheckStepResult:
    blockers: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {}

    if not req.strategy_id:
        warnings.append("strategy_id_not_provided_skipped_eligibility")
        return PrecheckStepResult(name="strategy_eligibility_precheck", passed=True, blockers=[], warnings=warnings, details=details)

    st = get_strategy(req.strategy_id)
    if not st:
        blockers.append("strategy_not_found")
        return PrecheckStepResult(name="strategy_eligibility_precheck", passed=False, blockers=blockers, warnings=warnings, details=details)

    details["strategy_key"] = st.strategy_key
    details["status"] = st.status
    details["promotion_status"] = st.promotion_status

    if st.disabled_reason:
        blockers.append(f"strategy_disabled:{st.disabled_reason}")
    if st.status in {"rejected", "paused"}:
        blockers.append(f"strategy_status_blocked:{st.status}")

    rac = normalize_asset_class(req.asset_class)
    if st.asset_class != rac:
        blockers.append("strategy_asset_class_mismatch")

    allowed_stages = {"active", "testing", "paper_active"}
    if st.promotion_status not in allowed_stages and st.status not in {"active", "approved"}:
        blockers.append("strategy_not_eligible_stage")

    if st.promotion_status == "candidate" or st.status == "candidate":
        if not req.metadata.get("allow_candidate_strategy_execution"):
            blockers.append("candidate_strategy_requires_explicit_metadata_flag")

    # Learning loop drawdown — stub: check metadata
    if req.metadata.get("strategy_disabled_by_learning_loop"):
        blockers.append("strategy_disabled_by_learning_loop")

    return PrecheckStepResult(
        name="strategy_eligibility_precheck",
        passed=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        details=details,
    )


def run_account_feasibility_precheck(req: ExecutionRequest, reference_price: float | None) -> PrecheckStepResult:
    blockers: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {}

    snap = get_alpaca_paper_snapshot()
    details["alpaca_status"] = snap.status
    if snap.status != "connected":
        blockers.append("alpaca_account_not_connected")
        return PrecheckStepResult(name="account_feasibility_precheck", passed=False, blockers=blockers, warnings=warnings, details=details)

    acct = snap.account
    bp = acct.buying_power if acct else None
    cash = acct.cash if acct else None
    equity = acct.equity if acct else None
    details["buying_power"] = bp
    details["cash"] = cash
    details["equity"] = equity

    if acct and acct.trading_blocked:
        blockers.append("account_trading_blocked")

    qty = req.quantity
    px = req.limit_price or reference_price
    est = None
    if qty is not None and px is not None:
        est = float(qty) * float(px)
    if est is not None and bp is not None and est > float(bp) * 1.001:
        blockers.append("estimated_order_exceeds_buying_power")

    # PDT / pattern day trader — surface as warning when flagged
    if acct and acct.pattern_day_trader:
        warnings.append("pattern_day_trader_account_rules_apply")

    return PrecheckStepResult(
        name="account_feasibility_precheck",
        passed=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        details=details,
    )


def run_execution_precheck(req: ExecutionRequest, effective_mode: str, cfg: EdgeSenseExecutionConfig) -> PrecheckStepResult:
    blockers: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"effective_mode": effective_mode}

    if effective_bool("EMERGENCY_STOP"):
        blockers.append("emergency_stop_active")
    if not effective_bool("EXECUTION_ENABLED"):
        blockers.append("execution_disabled")

    if req.asset_class.lower() not in cfg.allowed_asset_classes and normalize_asset_class(req.asset_class) not in cfg.allowed_asset_classes:
        # cfg has stock, option, crypto
        ac = normalize_asset_class(req.asset_class)
        if ac not in cfg.allowed_asset_classes:
            blockers.append("asset_class_not_allowed")

    if effective_mode == "paper" and not effective_bool("PAPER_TRADING_ENABLED"):
        blockers.append("paper_trading_not_enabled")

    if effective_mode == "live":
        if not cfg.live_trading_enabled or not effective_bool("LIVE_TRADING_ENABLED"):
            blockers.append("live_trading_not_enabled")
    if effective_mode == "live_disabled":
        blockers.append("execution_mode_live_disabled")

    if req.order_type in {"limit", "stop_limit"} and req.limit_price is None:
        blockers.append("limit_price_required")
    if req.order_type in {"stop", "stop_limit"} and req.stop_price is None:
        blockers.append("stop_price_required")

    clock = fetch_market_clock()
    details["market_clock"] = clock
    if clock.get("ok") and isinstance(clock.get("body"), dict):
        body = clock["body"]
        if body.get("is_open") is False and not req.metadata.get("allow_market_closed_execution"):
            blockers.append("market_closed")
    elif not clock.get("ok"):
        warnings.append("market_clock_unavailable_cannot_verify_session")

    if cfg.order_timeout_seconds <= 0:
        blockers.append("invalid_order_timeout")

    return PrecheckStepResult(
        name="execution_precheck",
        passed=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        details=details,
    )


def resolve_effective_mode(req: ExecutionRequest, cfg: EdgeSenseExecutionConfig | None = None) -> tuple[str, list[str]]:
    cfg = cfg or load_edgesense_execution_config()
    warnings: list[str] = []
    raw = (req.execution_mode or cfg.execution_mode or "paper").lower()
    if raw not in {"paper", "simulated", "live_disabled", "live"}:
        raw = "paper"
        warnings.append("invalid_execution_mode_defaulted_to_paper")
    # Product default: paper-first
    if raw == "live" and (not cfg.live_trading_enabled or not effective_bool("LIVE_TRADING_ENABLED")):
        return "paper", warnings + ["live_requested_downgraded_to_paper_env_gate"]
    return raw, warnings


def combine_prechecks(steps: list[PrecheckStepResult]) -> PrecheckSummary:
    all_blockers: list[str] = []
    all_warnings: list[str] = []
    for s in steps:
        all_blockers.extend(s.blockers)
        all_warnings.extend(s.warnings)
    return PrecheckSummary(
        passed=all(len(s.blockers) == 0 for s in steps),
        steps=steps,
        blockers=sorted(set(all_blockers)),
        warnings=sorted(set(all_warnings)),
    )


def run_all_prechecks(req: ExecutionRequest, *, data_source: str = "auto") -> tuple[PrecheckSummary, str, float | None]:
    """Returns precheck summary, effective execution mode, reference price."""
    cfg = load_edgesense_execution_config()
    eff, mode_warnings = resolve_effective_mode(req, cfg)

    dq = run_data_quality_precheck(req, source=data_source)
    ref = None
    if dq.details.get("data_quality"):
        # price from last step details - re-fetch minimal
        md = MarketDataService()
        s = md.get_market_snapshot(req.symbol.strip(), source=data_source)
        ref = s.get("current_price") or s.get("price")

    st_el = run_strategy_eligibility_precheck(req)
    acct = run_account_feasibility_precheck(req, ref)

    from app.portfolio_manager.portfolio_precheck import run_portfolio_precheck
    from app.risk.risk_prechecks import run_edgesense_risk_precheck

    snap = get_alpaca_paper_snapshot()
    positions = list(snap.positions) if snap.status == "connected" else []
    eq = snap.account.equity if snap.account else None
    prop_notional = None
    if req.quantity is not None and ref is not None:
        prop_notional = float(req.quantity) * float(ref)

    spread = None
    md2 = MarketDataService()
    s2 = md2.get_market_snapshot(req.symbol.strip(), source=data_source)
    spread = s2.get("bid_ask_spread")

    port = run_portfolio_precheck(
        symbol=req.symbol,
        positions=positions,
        equity=eq,
        proposed_additional_notional=prop_notional,
        cfg=cfg,
    )

    exempt_sl = bool(req.metadata.get("exempt_stop_loss"))
    risk = run_edgesense_risk_precheck(
        symbol=req.symbol,
        asset_class=normalize_asset_class(req.asset_class),
        side=req.side,
        quantity=req.quantity,
        limit_price=req.limit_price,
        stop_loss_price=req.stop_loss_price,
        spread_pct=spread,
        reference_price=float(ref) if ref is not None else None,
        buying_power=snap.account.buying_power if snap.account else None,
        equity=eq,
        confidence=req.confidence_score,
        exempt_stop_loss=exempt_sl,
        cfg=cfg,
    )

    ex = run_execution_precheck(req, eff, cfg)

    steps = [dq, st_el, acct, port, risk, ex]
    summary = combine_prechecks(steps)
    summary.warnings = sorted(set(summary.warnings + mode_warnings))
    return summary, eff, float(ref) if ref is not None else None
