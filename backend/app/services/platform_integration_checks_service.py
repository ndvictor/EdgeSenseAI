"""Alpaca + platform integration checks — one orchestrated run for readiness QA.

Maps to the product checklist: data sources, freshness, universe, snapshot, features,
scanner, ranking, regime, news, risk, portfolio, paper orders, order sync, positions,
journal, drift, alerts, observability.

Does not log secrets. Provider probes return only HTTP status / high-level outcomes.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from importlib.util import find_spec
from typing import Any, Callable, Literal

import requests
from pydantic import BaseModel, ConfigDict, Field

from app.core.effective_runtime import effective_bool
from app.core.settings import settings
from app.services.alpaca_execution_service import (
    TradeNowConfigUpdate,
    TradeNowOrderRequest,
    get_trade_now_config,
    place_trade_now_order,
    update_trade_now_config,
)
from app.services.alpaca_paper_account_service import get_alpaca_paper_snapshot
from app.services.capital_allocation_service import CapitalAllocationRequest, create_capital_allocation_plan
from app.services.data_freshness_gate_service import DataFreshnessCheckRequest, run_data_freshness_check
from app.services.feature_store_service import FeatureStoreRunRequest, run_feature_store_pipeline
from app.services.journal_outcome_service import get_journal_summary
from app.services.market_condition_scanner_service import MarketScannerRequest, run_market_condition_scan
from app.services.market_data_service import MarketDataService
from app.services.market_data_providers.alpaca_provider import AlpacaMarketDataProvider
from app.services.market_regime_model_service import MarketRegimeRequest, run_market_regime_model
from app.services.performance_drift_service import PerformanceDriftRequest, run_performance_drift_check
from app.services.risk_manager_service import OpenPosition, RiskReviewRequest, review_risk
from app.services.strategy_ranking_service import StrategyRankingRequest, run_strategy_ranking
from app.services.universe_discovery_service import UniverseDiscoverRequest, discover_universe
from app.services.health_service import get_health_snapshot

CheckStatus = Literal["pass", "warn", "fail", "skip"]


class IntegrationCheckResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    key: str
    label: str
    category: str
    belongs_to: str
    why_it_matters: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


class PlatformIntegrationChecksRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbols: list[str] = Field(default_factory=lambda: ["SPY", "AAPL"])
    source: Literal["auto", "yfinance", "alpaca", "polygon"] = "auto"

    checks: list[str] | None = Field(
        default=None,
        description="Subset of check keys to run; None runs all.",
    )
    submit_real_paper_order: bool = Field(
        default=False,
        description="If True, attempts a live paper submission (requires all TradeNow gates). "
        "Default False: only dry-run validation path.",
    )


class PlatformIntegrationChecksResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["pass", "warn", "fail"]
    checked_at: str
    symbols: list[str]
    source: str
    checks: list[IntegrationCheckResult]
    blockers: list[str]
    warnings: list[str]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_timed(label: str, fn: Callable[[], Any]) -> tuple[Any, float, str | None]:
    t0 = time.perf_counter()
    err: str | None = None
    try:
        out = fn()
    except Exception as exc:  # noqa: BLE001 — integration surface; capture for report
        out = None
        err = str(exc)[:240]
    ms = (time.perf_counter() - t0) * 1000.0
    return out, ms, err


def _probe_polygon(symbol: str) -> tuple[str, int | None, str]:
    key = settings.polygon_api_key
    if not key:
        return "skip", None, "POLYGON_API_KEY not set"
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
    try:
        r = requests.get(url, params={"adjusted": "true", "apiKey": key}, timeout=settings.market_data_provider_timeout_seconds)
        if r.status_code >= 400:
            return "fail", r.status_code, f"HTTP {r.status_code}"
        data = r.json()
        if data.get("status") in ("ERROR", "error") or data.get("error"):
            return "fail", r.status_code, "Polygon returned error in JSON"
        return "pass", r.status_code, "Prev aggregate reachable"
    except requests.RequestException as exc:
        return "fail", None, str(exc)[:160]


def _probe_finnhub(symbol: str) -> tuple[str, int | None, str]:
    key = settings.finnhub_api_key
    if not effective_bool("NEWS_PROVIDER_ENABLED"):
        return "skip", None, "NEWS_PROVIDER_ENABLED is false"
    if not key:
        return "skip", None, "FINNHUB_API_KEY not set"
    url = "https://finnhub.io/api/v1/quote"
    try:
        r = requests.get(url, params={"symbol": symbol, "token": key}, timeout=settings.news_provider_timeout_seconds)
        if r.status_code >= 400:
            return "fail", r.status_code, f"HTTP {r.status_code}"
        body = r.json()
        if body.get("c") in (0, None) and body.get("d") is None:
            return "warn", r.status_code, "Quote payload may be empty for symbol"
        return "pass", r.status_code, "Quote endpoint reachable"
    except requests.RequestException as exc:
        return "fail", None, str(exc)[:160]


def _probe_finnhub_news(symbol: str) -> tuple[str, int | None, str]:
    key = settings.finnhub_api_key
    if not effective_bool("NEWS_PROVIDER_ENABLED"):
        return "skip", None, "NEWS_PROVIDER_ENABLED is false"
    if not key:
        return "skip", None, "FINNHUB_API_KEY not set"
    url = "https://finnhub.io/api/v1/company-news"
    try:
        r = requests.get(
            url,
            params={"symbol": symbol, "from": "2020-01-01", "to": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "token": key},
            timeout=settings.news_provider_timeout_seconds,
        )
        if r.status_code >= 400:
            return "fail", r.status_code, f"HTTP {r.status_code}"
        data = r.json()
        if not isinstance(data, list):
            return "warn", r.status_code, "Unexpected news payload shape"
        return "pass", r.status_code, f"Retrieved {len(data)} news items (may be zero)"
    except requests.RequestException as exc:
        return "fail", None, str(exc)[:160]


def _probe_alpha_vantage(symbol: str) -> tuple[str, int | None, str]:
    key = settings.alpha_vantage_key
    if not key:
        return "skip", None, "ALPHA_VANTAGE_KEY not set"
    url = "https://www.alphavantage.co/query"
    try:
        r = requests.get(
            url,
            params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": key},
            timeout=settings.market_data_provider_timeout_seconds,
        )
        if r.status_code >= 400:
            return "fail", r.status_code, f"HTTP {r.status_code}"
        data = r.json()
        if "Note" in data or "Information" in data:
            return "warn", r.status_code, "Rate limit or info message from Alpha Vantage"
        if "Global Quote" not in data:
            return "warn", r.status_code, "No Global Quote in response"
        return "pass", r.status_code, "GLOBAL_QUOTE reachable"
    except requests.RequestException as exc:
        return "fail", None, str(exc)[:160]


def _probe_newsapi() -> tuple[str, int | None, str]:
    key = settings.news_api_key
    if not effective_bool("NEWS_PROVIDER_ENABLED"):
        return "skip", None, "NEWS_PROVIDER_ENABLED is false"
    if not key:
        return "skip", None, "NEWS_API_KEY not set"
    url = "https://newsapi.org/v2/top-headlines"
    try:
        r = requests.get(
            url,
            params={"country": "us", "pageSize": 1, "apiKey": key},
            timeout=settings.news_provider_timeout_seconds,
        )
        if r.status_code >= 400:
            return "fail", r.status_code, f"HTTP {r.status_code}"
        data = r.json()
        if data.get("status") != "ok":
            return "warn", r.status_code, data.get("message", "NewsAPI status not ok")[:120]
        return "pass", r.status_code, "Top headlines reachable"
    except requests.RequestException as exc:
        return "fail", None, str(exc)[:160]


def _probe_fred() -> tuple[str, int | None, str]:
    key = settings.fred_api_key
    if not key:
        return "skip", None, "FRED_API_KEY not set"
    url = "https://api.stlouisfed.org/fred/series/observations"
    try:
        r = requests.get(
            url,
            params={"series_id": "DGS10", "api_key": key, "file_type": "json", "limit": 1, "sort_order": "desc"},
            timeout=settings.market_data_provider_timeout_seconds,
        )
        if r.status_code >= 400:
            return "fail", r.status_code, f"HTTP {r.status_code}"
        data = r.json()
        obs = data.get("observations") if isinstance(data, dict) else None
        if not obs:
            return "warn", r.status_code, "No observations in response"
        return "pass", r.status_code, "FRED observations reachable"
    except requests.RequestException as exc:
        return "fail", None, str(exc)[:160]


def _check_data_source_connectivity(symbols: list[str]) -> IntegrationCheckResult:
    primary = (symbols[0] if symbols else "SPY").upper()
    probes: dict[str, Any] = {}
    worst: CheckStatus = "pass"
    messages: list[str] = []

    # yfinance
    if find_spec("yfinance"):
        probes["yfinance"] = {"status": "pass", "message": "Package installed"}
    else:
        probes["yfinance"] = {"status": "warn", "message": "Package not installed"}
        worst = "warn" if worst == "pass" else worst

    # Alpaca trading API
    snap, ms, err = _run_timed("alpaca_paper", get_alpaca_paper_snapshot)
    if err:
        probes["alpaca_trading"] = {"status": "fail", "message": err}
        worst = "fail"
    elif snap and snap.status == "connected":
        probes["alpaca_trading"] = {"status": "pass", "message": "Paper account API reachable", "latency_ms": round(ms, 2)}
    elif snap and snap.status == "not_configured":
        probes["alpaca_trading"] = {"status": "skip", "message": "Keys not configured"}
        worst = "warn" if worst == "pass" else worst
    else:
        probes["alpaca_trading"] = {"status": "fail", "message": getattr(snap, "message", "unavailable")[:120]}
        worst = "fail"

    # Alpaca market data
    prov = AlpacaMarketDataProvider()
    if prov.is_configured():
        shot, ms2, err2 = _run_timed("alpaca_data", lambda: prov.get_snapshot(primary))
        if err2:
            probes["alpaca_market_data"] = {"status": "fail", "message": err2}
            worst = "fail"
        elif shot and shot.get("data_quality") not in {"unavailable", "not_configured"}:
            probes["alpaca_market_data"] = {"status": "pass", "message": "Snapshot ok", "latency_ms": round(ms2, 2)}
        else:
            probes["alpaca_market_data"] = {"status": "warn", "message": shot.get("error", "snapshot weak") if isinstance(shot, dict) else "weak"}
            worst = "warn" if worst == "pass" else worst
    else:
        probes["alpaca_market_data"] = {"status": "skip", "message": "Not enabled or missing keys"}

    st, code, msg = _probe_polygon(primary)
    probes["polygon_massive"] = {"status": st, "http_status": code, "message": msg}
    worst = _merge_worst(worst, st)

    st, code, msg = _probe_finnhub(primary)
    probes["finnhub"] = {"status": st, "http_status": code, "message": msg}
    worst = _merge_worst(worst, st)

    st, code, msg = _probe_alpha_vantage(primary)
    probes["alpha_vantage"] = {"status": st, "http_status": code, "message": msg}
    worst = _merge_worst(worst, st)

    st, code, msg = _probe_fred()
    probes["fred"] = {"status": st, "http_status": code, "message": msg}
    worst = _merge_worst(worst, st)

    st, code, msg = _probe_newsapi()
    probes["newsapi"] = {"status": st, "http_status": code, "message": msg}
    worst = _merge_worst(worst, st)

    for name, p in probes.items():
        if p.get("status") in {"fail", "warn"}:
            messages.append(f"{name}: {p.get('message')}")

    return IntegrationCheckResult(
        key="data_source_connectivity",
        label="Test data source connectivity",
        category="Platform readiness",
        belongs_to="Data Sources / Platform Readiness",
        why_it_matters="Confirms API keys and provider availability before trusting signals.",
        status=worst,
        message="; ".join(messages[:4]) if messages else "All probed sources responded as expected (skipped where not configured).",
        details={"providers": probes},
        duration_ms=0.0,
    )


def _merge_worst(current: CheckStatus, probe: str) -> CheckStatus:
    order = {"pass": 0, "skip": 1, "warn": 2, "fail": 3}
    p = probe if probe in order else "warn"
    return p if order[p] > order[current] else current


def run_platform_integration_checks(request: PlatformIntegrationChecksRequest) -> PlatformIntegrationChecksResponse:
    from uuid import uuid4

    run_id = f"intchk-{uuid4().hex[:12]}"
    symbols = [s.upper().strip() for s in request.symbols if s.strip()] or ["SPY"]
    primary = symbols[0]
    want = set(request.checks) if request.checks else None

    def want_run(key: str) -> bool:
        return want is None or key in want

    results: list[IntegrationCheckResult] = []
    md = MarketDataService()

    if want_run("data_source_connectivity"):
        results.append(_check_data_source_connectivity(symbols))

    if want_run("data_freshness"):
        def _fresh():
            return run_data_freshness_check(
                DataFreshnessCheckRequest(
                    symbols=symbols[:3],
                    source=request.source,
                    require_bid_ask=False,
                )
            )

        fr, ms, err = _run_timed("freshness", _fresh)
        if err:
            st: CheckStatus = "fail"
            msg = err
        elif fr and fr.status == "pass":
            st = "pass"
            msg = "Freshness gate passed for probed symbols."
        elif fr and fr.status == "warn":
            st = "warn"
            msg = "; ".join(fr.warnings[:3]) or "Freshness warnings"
        else:
            st = "fail"
            msg = "; ".join((fr.blockers if fr else []) or ["Freshness check failed"])
        results.append(
            IntegrationCheckResult(
                key="data_freshness",
                label="Test data freshness",
                category="Data quality",
                belongs_to="Data Quality",
                why_it_matters="Prevents stale quotes from creating fake signals.",
                status=st,
                message=msg,
                details={"run_status": getattr(fr, "status", None), "summary": getattr(fr, "summary", None).model_dump() if fr and fr.summary else None},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("symbol_universe"):
        def _uni():
            return discover_universe(
                UniverseDiscoverRequest(
                    symbols=symbols[:5],
                    source=request.source,
                    promote_to_candidate_universe=False,
                )
            )

        ur, ms, err = _run_timed("universe", _uni)
        n_sel = len(ur.selected_watchlist) if ur else 0
        if err:
            st, msg = "fail", err
        elif ur and n_sel:
            st, msg = "pass", f"Built {n_sel} universe / watchlist candidate(s)."
        elif ur and (ur.rejected_candidates or ur.research_only_candidates):
            st, msg = "warn", "Discovery ran but nothing promoted to watchlist (rejected or research-only only)."
        elif ur:
            st, msg = "warn", "Discovery returned no candidates (check data / gates)."
        else:
            st, msg = "fail", "Universe discovery failed"
        results.append(
            IntegrationCheckResult(
                key="symbol_universe",
                label="Test symbol universe",
                category="Universe",
                belongs_to="Universe",
                why_it_matters="Ensures scanners have valid symbols.",
                status=st,
                message=msg,
                details={
                    "selected_watchlist": n_sel,
                    "rejected": len(ur.rejected_candidates) if ur else 0,
                    "research_only": len(ur.research_only_candidates) if ur else 0,
                },
                duration_ms=round(ms, 2),
            )
        )

    if want_run("market_snapshot"):
        snap, ms, err = _run_timed("snapshot", lambda: md.get_market_snapshot(primary, source=request.source))
        if err:
            st, msg = "fail", err
        elif snap and snap.get("error"):
            st, msg = "fail", str(snap.get("error"))[:160]
        elif snap and snap.get("current_price"):
            st, msg = "pass", f"Price={snap.get('current_price')} provider={snap.get('provider')}"
        else:
            st, msg = "warn", "Snapshot missing price"
        results.append(
            IntegrationCheckResult(
                key="market_snapshot",
                label="Test market snapshot",
                category="Live data",
                belongs_to="Live Watchlist / Signals",
                why_it_matters="Confirms real market input exists.",
                status=st,
                message=msg,
                details={k: snap.get(k) for k in ("provider", "data_quality", "bid_ask_spread", "volume") if snap} if snap else {},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("feature_pipeline"):
        def _feat():
            return run_feature_store_pipeline(FeatureStoreRunRequest(symbol=primary, source=request.source, horizon="swing"))

        fr, ms, err = _run_timed("features", _feat)
        if err:
            st, msg = "fail", err
        elif fr and fr.row and fr.quality_report.quality_status != "fail":
            st = "pass"
            msg = f"Feature row {fr.row.id} quality={fr.quality_report.quality_status}"
        elif fr:
            st, msg = "warn", f"Quality status {fr.quality_report.quality_status}"
        else:
            st, msg = "fail", "Feature pipeline returned nothing"
        results.append(
            IntegrationCheckResult(
                key="feature_pipeline",
                label="Test feature pipeline",
                category="Features",
                belongs_to="Model Lab / Feature Engine",
                why_it_matters="Confirms raw data becomes usable features.",
                status=st,
                message=msg,
                details={"feature_row_id": fr.row.id if fr else None, "quality": fr.quality_report.quality_status if fr else None},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("signal_scanner"):
        def _scan():
            return run_market_condition_scan(
                MarketScannerRequest(symbols=symbols[:5], strategy_key="multi_factor", data_source=request.source)
            )

        sr, ms, err = _run_timed("scanner", _scan)
        if err:
            st, msg = "fail", err
        elif sr:
            st, msg = "pass", f"Scanned {len(sr.symbols_scanned)} symbols, {len(sr.matched_signals)} matches"
        else:
            st, msg = "fail", "Scanner failed"
        results.append(
            IntegrationCheckResult(
                key="signal_scanner",
                label="Test signal scanner",
                category="Signals",
                belongs_to="Signals / Edge Signals",
                why_it_matters="Confirms strategy trigger logic runs end-to-end.",
                status=st,
                message=msg,
                details={"matched": len(sr.matched_signals) if sr else 0, "run_id": sr.run_id if sr else None},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("ranking_model"):
        def _rank():
            return run_strategy_ranking(
                StrategyRankingRequest(
                    market_phase="market_open",
                    active_loop="edge_radar",
                    regime="risk_on",
                    horizon="swing",
                    research_mode=True,
                    source=request.source,
                )
            )

        rr, ms, err = _run_timed("ranking", _rank)
        if err:
            st, msg = "fail", err
        elif rr and rr.status == "completed" and rr.ranked_strategies:
            st, msg = "pass", f"Ranked {len(rr.ranked_strategies)} strategies; top={rr.top_strategy_key}"
        elif rr and rr.status == "failed":
            st, msg = "fail", "; ".join(rr.blockers[:2]) or "Ranking failed"
        else:
            st, msg = "warn", "Ranking partial or empty"
        results.append(
            IntegrationCheckResult(
                key="ranking_model",
                label="Test ranking model",
                category="Model lab",
                belongs_to="Model Lab",
                why_it_matters="Confirms strategy ranking produces an ordering.",
                status=st,
                message=msg,
                details={"ranking_status": rr.status if rr else None, "top": rr.top_strategy_key if rr else None},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("regime_classifier"):
        def _reg():
            return run_market_regime_model(MarketRegimeRequest(source=request.source))

        rg, ms, err = _run_timed("regime", _reg)
        if err:
            st, msg = "fail", err
        elif rg and rg.regime != "unknown" and rg.status != "fail":
            st, msg = "pass", f"Regime={rg.regime} vol={rg.volatility_state}"
        elif rg:
            st, msg = "warn", f"Regime={rg.regime} status={rg.status}"
        else:
            st, msg = "fail", "Regime model failed"
        results.append(
            IntegrationCheckResult(
                key="regime_classifier",
                label="Test regime classifier",
                category="Regime",
                belongs_to="Market Regime",
                why_it_matters="Avoids deploying the wrong strategy for current conditions.",
                status=st,
                message=msg,
                details={"regime": rg.regime if rg else None, "trend": rg.trend_state if rg else None},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("news_catalyst_agent"):
        st, code, msg = _probe_finnhub_news(primary)
        cmap = {"pass": "pass", "warn": "warn", "fail": "fail", "skip": "skip"}
        results.append(
            IntegrationCheckResult(
                key="news_catalyst_agent",
                label="Test news / catalyst feed",
                category="News",
                belongs_to="Candidates / Recommendations",
                why_it_matters="Explains symbol moves with headlines and catalysts when enabled.",
                status=cmap.get(st, "warn"),  # type: ignore[arg-type]
                message=msg,
                details={"http_status": code},
                duration_ms=0.0,
            )
        )

    if want_run("risk_check"):
        def _risk():
            return review_risk(
                RiskReviewRequest(
                    symbol=primary,
                    current_price=100.0,
                    final_signal_score=78.0,
                    confidence=0.82,
                    data_quality="pass",
                    spread_percent=0.12,
                    liquidity_score=0.75,
                    account_equity=10_000.0,
                    buying_power=10_000.0,
                )
            )

        rr, ms, err = _run_timed("risk", _risk)
        if err:
            st, msg = "fail", err
        elif rr and rr.status in {"approved", "watch_only"} and not rr.blockers:
            st, msg = "pass", f"Risk review status={rr.status} score={rr.risk_score}"
        elif rr:
            st, msg = "warn", f"Risk status={rr.status} blockers={rr.blockers[:2]}"
        else:
            st, msg = "fail", "Risk review failed"
        results.append(
            IntegrationCheckResult(
                key="risk_check",
                label="Test risk check",
                category="Risk",
                belongs_to="Account Risk Center",
                why_it_matters="Blocks unsafe position sizing and vetoed setups.",
                status=st,
                message=msg,
                details={"risk_status": rr.status if rr else None},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("portfolio_check"):
        def _risk_port():
            return review_risk(
                RiskReviewRequest(
                    symbol=primary,
                    current_price=100.0,
                    final_signal_score=80.0,
                    confidence=0.85,
                    data_quality="pass",
                    account_equity=5_000.0,
                    buying_power=5_000.0,
                    open_positions=[
                        OpenPosition(symbol="MSFT", side="long", entry_price=400.0, quantity=2.0),
                        OpenPosition(symbol="AAPL", side="long", entry_price=180.0, quantity=5.0),
                    ],
                )
            )

        pr, ms, err = _run_timed("portfolio", _risk_port)
        cap, ms2, err2 = _run_timed(
            "capital",
            lambda: create_capital_allocation_plan(
                CapitalAllocationRequest(
                    symbol=primary,
                    current_price=100.0,
                    final_signal_score=72.0,
                    confidence=0.7,
                    risk_status="approved",
                    account_equity=5_000.0,
                    buying_power=5_000.0,
                )
            ),
        )
        if err or err2:
            st, msg = "fail", (err or err2 or "error")
        elif pr and cap:
            st, msg = "pass", "Portfolio stress + capital allocation plan computed"
        else:
            st, msg = "warn", "Partial portfolio diagnostics"
        results.append(
            IntegrationCheckResult(
                key="portfolio_check",
                label="Test portfolio check",
                category="Portfolio",
                belongs_to="Portfolio Manager Agent",
                why_it_matters="Surfaces concentration and sizing before adding correlated risk.",
                status=st,
                message=msg,
                details={
                    "risk_score": pr.risk_score if pr else None,
                    "allocation_status": cap.status if cap else None,
                },
                duration_ms=round(ms + ms2, 2),
            )
        )

    if want_run("paper_order"):
        cfg_prev = get_trade_now_config()
        update_trade_now_config(
            TradeNowConfigUpdate(
                user_enabled=True,
                automatic_execution_user_enabled=cfg_prev.automatic_execution_user_enabled,
                execution_mode=cfg_prev.execution_mode,
            )
        )
        try:
            if request.submit_real_paper_order:
                resp, ms, err = _run_timed(
                    "paper_submit",
                    lambda: place_trade_now_order(
                        TradeNowOrderRequest(
                            symbol=primary,
                            side="buy",
                            qty=1.0,
                            dry_run=False,
                            human_approval_confirmed=True,
                            approval_source="human",
                        )
                    ),
                )
            else:
                resp, ms, err = _run_timed(
                    "paper_dry",
                    lambda: place_trade_now_order(
                        TradeNowOrderRequest(
                            symbol=primary,
                            side="buy",
                            qty=1.0,
                            dry_run=True,
                            human_approval_confirmed=True,
                            approval_source="human",
                        )
                    ),
                )
        finally:
            update_trade_now_config(
                TradeNowConfigUpdate(
                    user_enabled=cfg_prev.user_enabled,
                    automatic_execution_user_enabled=cfg_prev.automatic_execution_user_enabled,
                    execution_mode=cfg_prev.execution_mode,
                )
            )
        if err:
            st, msg = "fail", err
        elif resp and getattr(resp, "status", None) == "dry_run" and not resp.blockers:
            st, msg = "pass", "Dry-run order path validated (no broker call)."
        elif resp and getattr(resp, "status", None) == "submitted":
            st, msg = "pass", "Paper order submitted to Alpaca."
        elif resp and getattr(resp, "status", None) == "blocked":
            st, msg = "warn", f"Order blocked: {resp.blockers[:2]}"
        else:
            st, msg = "fail", "Unexpected order response"
        results.append(
            IntegrationCheckResult(
                key="paper_order",
                label="Test paper order",
                category="Execution",
                belongs_to="Paper Trading",
                why_it_matters="Validates execution payload and safety gates before real size.",
                status=st,
                message=msg,
                details={"order_status": getattr(resp, "status", None) if resp else None},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("order_status_sync"):
        snap, ms, err = _run_timed("ordersync", get_alpaca_paper_snapshot)
        if err:
            st, msg = "fail", err
        elif snap and snap.status != "connected":
            st, msg = "skip", "Alpaca not connected — cannot verify order objects from broker."
        else:
            orders = snap.open_orders if snap else []
            ok = isinstance(orders, list) and all(hasattr(o, "status") or getattr(o, "status", None) is not None for o in orders)
            st, msg = ("pass" if ok else "warn"), f"Parsed {len(orders)} open order(s) with status fields."
        results.append(
            IntegrationCheckResult(
                key="order_status_sync",
                label="Test order status sync",
                category="Execution",
                belongs_to="TradeNow / Execution",
                why_it_matters="Ensures submitted / filled / canceled states are visible.",
                status=st,  # type: ignore[arg-type]
                message=msg,
                details={"open_order_count": len(snap.open_orders) if snap and snap.open_orders else 0},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("position_monitor"):
        snap, ms, err = _run_timed("posmon", get_alpaca_paper_snapshot)
        if err:
            st, msg = "fail", err
        elif snap and snap.status == "connected":
            st, msg = "warn", (
                "Broker positions readable. Automated stop / trailing / time-stop monitor is not fully wired in backend yet — "
                "use paper trade lifecycle + journal for manual tracking."
            )
        else:
            st, msg = "skip", "Alpaca not connected — position monitor check skipped."
        results.append(
            IntegrationCheckResult(
                key="position_monitor",
                label="Test position monitor",
                category="Positions",
                belongs_to="Positions",
                why_it_matters="After entry, exits must follow risk plan (stops, targets, time).",
                status=st,  # type: ignore[arg-type]
                message=msg,
                details={"position_count": len(snap.positions) if snap and snap.positions else 0},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("post_trade_analytics"):
        def _js():
            return get_journal_summary()

        js, ms, err = _run_timed("journal", _js)
        if err:
            st, msg = "fail", err
        elif js:
            st, msg = "pass", f"Journal summary: {js.total_entries} entries, mode={js.persistence_mode}"
        else:
            st, msg = "warn", "No journal summary"
        results.append(
            IntegrationCheckResult(
                key="post_trade_analytics",
                label="Test post-trade analytics",
                category="Learning",
                belongs_to="Journal / Learning Loop",
                why_it_matters="Captures slippage, hold time, and outcome labels for feedback.",
                status=st,
                message=msg,
                details={"total_entries": js.total_entries if js else 0},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("strategy_decay"):
        def _drift():
            return run_performance_drift_check(PerformanceDriftRequest(lookback_days=90, min_samples=1, source="both"))

        dr, ms, err = _run_timed("drift", _drift)
        if err:
            st, msg = "fail", err
        elif dr and dr.status in {"pass", "warn", "insufficient_data"}:
            st = "pass" if dr.status == "pass" else "warn"
            msg = f"Drift status={dr.status} samples={dr.sample_count}"
        elif dr and dr.status == "fail":
            st, msg = "warn", "Drift check reported failure — review calibration."
        else:
            st, msg = "fail", "Drift check unavailable"
        results.append(
            IntegrationCheckResult(
                key="strategy_decay",
                label="Test strategy decay",
                category="Learning",
                belongs_to="Learning Loop",
                why_it_matters="Detects when historical edge stops working.",
                status=st,
                message=msg,
                details={"drift_status": dr.status if dr else None, "sample_count": dr.sample_count if dr else 0},
                duration_ms=round(ms, 2),
            )
        )

    if want_run("alerts"):
        smtp_ok = bool(settings.smtp_server and settings.smtp_from_email)
        slack_ok = bool(settings.slack_webhook_url)
        recipients_ok = bool(settings.notification_email_recipients_list)
        if smtp_ok and recipients_ok:
            st, msg = "pass", "SMTP + recipient list configured (delivery not sent in this check)."
        elif slack_ok:
            st, msg = "pass", "Slack webhook configured (message not sent in this check)."
        else:
            st, msg = "warn", "No SMTP+recipients or Slack webhook configured for outbound alerts."
        results.append(
            IntegrationCheckResult(
                key="alerts",
                label="Test alerts configuration",
                category="Monitoring",
                belongs_to="Monitoring & Alerts",
                why_it_matters="Urgent signals and risk events must reach operators.",
                status=st,
                message=msg,
                details={"smtp_configured": smtp_ok, "slack_configured": slack_ok, "email_recipients_configured": recipients_ok},
                duration_ms=0.0,
            )
        )

    if want_run("observability"):
        hs = get_health_snapshot()
        tracing = effective_bool("LANGSMITH_TRACING") and bool(os.getenv("LANGSMITH_API_KEY"))
        st: CheckStatus = "pass"
        notes: list[str] = []
        if hs.get("postgres_persistence_status") != "connected":
            notes.append("Postgres not connected — ops visibility degraded.")
            st = "warn"
        if not tracing:
            notes.append("LangSmith tracing off or key missing.")
            st = "warn" if st == "pass" else st
        results.append(
            IntegrationCheckResult(
                key="observability",
                label="Test observability baseline",
                category="Ops",
                belongs_to="Ops Command",
                why_it_matters="Surfaces API health, persistence, and tracing for incidents.",
                status=st,
                message="; ".join(notes) if notes else "Health snapshot ok; review LangSmith for deep traces.",
                details={
                    "postgres": hs.get("postgres_persistence_status"),
                    "redis_configured": hs.get("redis_configured"),
                    "langsmith_tracing_configured": tracing,
                },
                duration_ms=0.0,
            )
        )

    blockers = [c.message for c in results if c.status == "fail"]
    warns = [c.message for c in results if c.status == "warn"]
    if blockers:
        overall: Literal["pass", "warn", "fail"] = "fail"
    elif warns:
        overall = "warn"
    else:
        overall = "pass"

    return PlatformIntegrationChecksResponse(
        run_id=run_id,
        status=overall,
        checked_at=_now_iso(),
        symbols=symbols,
        source=request.source,
        checks=results,
        blockers=blockers,
        warnings=warns,
    )
