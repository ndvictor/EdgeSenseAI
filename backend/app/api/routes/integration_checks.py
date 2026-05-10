"""Run end-to-end integration checks (Alpaca, data stack, signals, risk, paper flow)."""

from fastapi import APIRouter

from app.services.platform_integration_checks_service import (
    PlatformIntegrationChecksRequest,
    PlatformIntegrationChecksResponse,
    run_platform_integration_checks,
)

router = APIRouter()

# Keys accepted by PlatformIntegrationChecksRequest.checks
INTEGRATION_CHECK_CATALOG = [
    {"key": "data_source_connectivity", "label": "Test data source connectivity", "belongs_to": "Data Sources / Platform Readiness"},
    {"key": "data_freshness", "label": "Test data freshness", "belongs_to": "Data Quality"},
    {"key": "symbol_universe", "label": "Test symbol universe", "belongs_to": "Universe"},
    {"key": "market_snapshot", "label": "Test market snapshot", "belongs_to": "Live Watchlist / Signals"},
    {"key": "feature_pipeline", "label": "Test feature pipeline", "belongs_to": "Model Lab / Feature Engine"},
    {"key": "signal_scanner", "label": "Test signal scanner", "belongs_to": "Signals / Edge Signals"},
    {"key": "ranking_model", "label": "Test ranking model", "belongs_to": "Model Lab"},
    {"key": "regime_classifier", "label": "Test regime classifier", "belongs_to": "Market Regime"},
    {"key": "news_catalyst_agent", "label": "Test news / catalyst feed", "belongs_to": "Candidates / Recommendations"},
    {"key": "risk_check", "label": "Test risk check", "belongs_to": "Account Risk Center"},
    {"key": "portfolio_check", "label": "Test portfolio check", "belongs_to": "Portfolio Manager Agent"},
    {"key": "paper_order", "label": "Test paper order", "belongs_to": "Paper Trading"},
    {"key": "order_status_sync", "label": "Test order status sync", "belongs_to": "TradeNow / Execution"},
    {"key": "position_monitor", "label": "Test position monitor", "belongs_to": "Positions"},
    {"key": "post_trade_analytics", "label": "Test post-trade analytics", "belongs_to": "Journal / Learning Loop"},
    {"key": "strategy_decay", "label": "Test strategy decay", "belongs_to": "Learning Loop"},
    {"key": "alerts", "label": "Test alerts configuration", "belongs_to": "Monitoring & Alerts"},
    {"key": "observability", "label": "Test observability baseline", "belongs_to": "Ops Command"},
]


@router.get("/integration-checks/catalog")
def get_integration_checks_catalog():
    """List available integration checks (for UI or runbooks)."""
    return {"checks": INTEGRATION_CHECK_CATALOG, "count": len(INTEGRATION_CHECK_CATALOG)}


@router.post("/integration-checks/run", response_model=PlatformIntegrationChecksResponse)
def post_integration_checks_run(request: PlatformIntegrationChecksRequest):
    """Execute integration checks using configured real providers.

    Default paper order is dry-run only. Set submit_real_paper_order=true only when all TradeNow
    gates are intentionally enabled for a real paper probe.
    """
    return run_platform_integration_checks(request)
