from datetime import datetime
from importlib.util import find_spec
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.settings import settings
from app.services.persistence_service import get_persistence_status

router = APIRouter()


class DataSourceStatus(BaseModel):
    name: str
    key: Optional[str] = None
    status: str
    type: str
    configured: bool
    connected: bool = False
    connection_label: str = "Checked during request"
    configured_label: str = "Credentials"
    used_for: List[str]
    last_checked: str
    message: str
    required_for: List[str] = []


class DataSourcesStatusResponse(BaseModel):
    connected_sources: int
    total_sources: int
    sources: List[DataSourceStatus]


def _package_status(package_name: str, configured_message: str, missing_message: str) -> dict:
    installed = find_spec(package_name) is not None
    if installed:
        return {
            "status": "installed",
            "configured": True,
            "connected": False,
            "configured_label": "Package installed",
            "connection_label": "Checked during ticker request",
            "message": configured_message,
        }
    return {
        "status": "not_installed",
        "configured": False,
        "connected": False,
        "configured_label": "Package installed",
        "connection_label": "Unavailable",
        "message": missing_message,
    }


def _env_status(value: str, configured_message: str, missing_message: str) -> dict:
    if not value:
        return {
            "status": "not_configured",
            "configured": False,
            "connected": False,
            "configured_label": "Credentials",
            "connection_label": "Not available",
            "message": missing_message,
        }
    return {
        "status": "configured",
        "configured": True,
        "connected": False,
        "configured_label": "Credentials",
        "connection_label": "Checked during ticker request",
        "message": configured_message,
    }


def _check_alpaca_market_data() -> dict:
    if not settings.alpaca_market_data_enabled:
        return {
            "status": "disabled",
            "configured": False,
            "connected": False,
            "configured_label": "Enabled + credentials",
            "connection_label": "Disabled",
            "message": "Alpaca market data is disabled. Set ALPACA_MARKET_DATA_ENABLED=true and credentials to use it.",
        }
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        return {
            "status": "missing_credentials",
            "configured": False,
            "connected": False,
            "configured_label": "Enabled + credentials",
            "connection_label": "Missing credentials",
            "message": "Alpaca market data is enabled but credentials are missing.",
        }
    return {
        "status": "configured",
        "configured": True,
        "connected": False,
        "configured_label": "Enabled + credentials",
        "connection_label": "Checked during ticker request",
        "message": "Alpaca market data credentials are configured. Runtime quote checks happen through /api/market-data/snapshot/{symbol}.",
    }


def _mock_status() -> dict:
    return {
        "status": "test_only",
        "configured": True,
        "connected": True,
        "configured_label": "Test provider",
        "connection_label": "Always available",
        "message": "Mock provider is available for explicit UI testing only. Auto mode does not silently use mock data.",
    }


@router.get("/data-sources/status", response_model=DataSourcesStatusResponse)
def get_data_sources_status():
    now = datetime.utcnow().isoformat()
    persistence = get_persistence_status()
    checks = {
        "yfinance": _package_status(
            "yfinance",
            "yfinance package is installed. This means the adapter can run, not that Yahoo live data is currently reachable. Live connectivity is tested when you request a ticker.",
            "yfinance is not installed in the backend environment.",
        ),
        "alpaca": _check_alpaca_market_data(),
        "polygon": _env_status(settings.polygon_api_key, "POLYGON_API_KEY is set.", "Polygon is not configured."),
        "alpha_vantage": _env_status(settings.alpha_vantage_key, "ALPHA_VANTAGE_KEY is set.", "Alpha Vantage is not configured."),
        "iex": _env_status(settings.iex_cloud_key, "IEX_CLOUD_KEY is set.", "IEX Cloud is not configured."),
        "fred": _env_status(settings.fred_api_key, "FRED_API_KEY is set.", "FRED is not configured."),
        "newsapi": _env_status(settings.news_api_key if settings.news_provider_enabled else "", "NEWS_API_KEY is set.", "NewsAPI is not configured or disabled."),
        "finnhub": _env_status(settings.finnhub_api_key if settings.news_provider_enabled else "", "FINNHUB_API_KEY is set.", "Finnhub is not configured or disabled."),
        "benzinga": _env_status(settings.benzinga_api_key if settings.news_provider_enabled else "", "BENZINGA_API_KEY is set.", "Benzinga is not configured or disabled."),
        "openai": _env_status(settings.openai_api_key, "OPENAI_API_KEY is set.", "OpenAI is not configured."),
        "postgresql": {
            "status": persistence["postgres_persistence_status"],
            "configured": bool(settings.database_url),
            "connected": persistence["postgres_persistence_status"] == "connected",
            "configured_label": "DATABASE_URL",
            "connection_label": "Connected" if persistence["postgres_persistence_status"] == "connected" else "Not connected",
            "message": f"DATABASE_URL configured. pgvector={persistence['pgvector_status']}. {persistence.get('message') or ''}",
        },
        "redis": _env_status(settings.redis_url, "REDIS_URL is set.", "REDIS_URL is not configured."),
        "mock": _mock_status(),
    }

    source_specs = [
        ("yfinance", "yfinance", "market_data", ["stocks", "crypto", "market_regime", "charting"], ["research_charting"]),
        ("Alpaca Market Data", "alpaca", "market_data", ["stocks", "quotes", "intraday"], ["reliable_stock_quotes"]),
        ("Polygon.io", "polygon", "market_data", ["stocks", "options", "intraday"], ["production_intraday", "options_flow"]),
        ("Alpha Vantage", "alpha_vantage", "market_data", ["stocks", "fundamentals"], ["fallback_market_data"]),
        ("IEX Cloud", "iex", "market_data", ["stocks", "quotes"], ["fallback_quotes"]),
        ("FRED", "fred", "macro", ["rates", "macro", "regime"], ["macro_agent"]),
        ("NewsAPI", "newsapi", "news", ["news", "sentiment", "market_radar"], ["news_sentiment_agent"]),
        ("Finnhub", "finnhub", "news", ["news", "sentiment", "earnings"], ["news_sentiment_agent"]),
        ("Benzinga", "benzinga", "news", ["news", "events", "market_radar"], ["market_radar_agent"]),
        ("OpenAI", "openai", "internal", ["agents", "explanations"], ["llm_explanations"]),
        ("PostgreSQL", "postgresql", "database", ["feature_store", "recommendations", "paper_trading"], ["persistence"]),
        ("Redis", "redis", "database", ["caching", "agent_jobs", "sessions"], ["background_jobs"]),
        ("Mock Provider", "mock", "testing", ["ui_testing", "offline_demo"], ["explicit_testing_only"]),
    ]

    sources = [
        DataSourceStatus(
            name=name,
            key=key,
            type=source_type,
            status=checks[key]["status"],
            configured=checks[key]["configured"],
            connected=checks[key]["connected"],
            configured_label=checks[key].get("configured_label", "Credentials"),
            connection_label=checks[key].get("connection_label", "Checked during request"),
            used_for=used_for,
            required_for=required_for,
            last_checked=now,
            message=checks[key]["message"],
        )
        for name, key, source_type, used_for, required_for in source_specs
    ]
    sources.append(
        DataSourceStatus(
            name="Options Chain / Greeks Provider",
            key="options_data",
            type="options",
            status="not_configured",
            configured=False,
            connected=False,
            configured_label="Credentials",
            connection_label="Not available",
            used_for=["options_analysis", "options_flow_agent"],
            required_for=["options_flow", "iv_rank", "greeks", "gamma_exposure"],
            last_checked=now,
            message="Dedicated options chain and Greeks provider is not configured yet. Prefer Polygon Options or Tradier.",
        )
    )
    sources.append(
        DataSourceStatus(
            name="Paper Trading Engine",
            key="paper_trading",
            type="internal",
            status="configured" if settings.paper_trading_enabled else "not_configured",
            configured=settings.paper_trading_enabled,
            connected=settings.paper_trading_enabled,
            configured_label="Feature flag",
            connection_label="Enabled" if settings.paper_trading_enabled else "Disabled",
            used_for=["paper_trading", "outcome_labels"],
            required_for=["paper_trading_feedback_loop"],
            last_checked=now,
            message="Paper trading is enabled." if settings.paper_trading_enabled else "Paper trading is disabled.",
        )
    )

    connected_count = sum(1 for source in sources if source.connected)
    return DataSourcesStatusResponse(connected_sources=connected_count, total_sources=len(sources), sources=sources)
