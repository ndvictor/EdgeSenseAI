from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.settings import settings

router = APIRouter()


class DataSourceStatus(BaseModel):
    name: str
    key: Optional[str] = None
    status: str
    type: str
    configured: bool
    used_for: List[str]
    last_checked: str
    message: str


class DataSourcesStatusResponse(BaseModel):
    connected_sources: int
    total_sources: int
    sources: List[DataSourceStatus]


def _check_yfinance() -> dict:
    try:
        import yfinance as yf
        ticker = yf.Ticker("SPY")
        hist = ticker.history(period="1d")
        if hist is not None and len(hist) > 0:
            return {"status": "connected", "configured": True, "message": "yfinance market data is working"}
        return {"status": "partial", "configured": True, "message": "yfinance returned limited data"}
    except ImportError:
        return {"status": "unavailable", "configured": False, "message": "yfinance is not installed"}
    except Exception as exc:
        return {"status": "error", "configured": True, "message": f"Error checking yfinance: {str(exc)[:100]}"}


def _env_status(value: str, configured_message: str, missing_message: str) -> dict:
    if not value:
        return {"status": "not_configured", "configured": False, "message": missing_message}
    return {"status": "partial", "configured": True, "message": configured_message}


def _check_alpaca_market_data() -> dict:
    if not settings.alpaca_market_data_enabled:
        return {"status": "not_configured", "configured": False, "message": "Alpaca market data is disabled."}
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        return {"status": "not_configured", "configured": False, "message": "Alpaca market data credentials are missing."}
    return {"status": "partial", "configured": True, "message": "Alpaca market data credentials are configured."}


@router.get("/data-sources/status", response_model=DataSourcesStatusResponse)
def get_data_sources_status():
    now = datetime.utcnow().isoformat()
    checks = {
        "yfinance": _check_yfinance(),
        "alpaca": _check_alpaca_market_data(),
        "polygon": _env_status(settings.polygon_api_key, "POLYGON_API_KEY is set.", "Polygon is not configured."),
        "newsapi": _env_status(settings.news_api_key if settings.news_provider_enabled else "", "NEWS_API_KEY is set.", "NewsAPI is not configured or disabled."),
        "finnhub": _env_status(settings.finnhub_api_key if settings.news_provider_enabled else "", "FINNHUB_API_KEY is set.", "Finnhub is not configured or disabled."),
        "openai": _env_status(settings.openai_api_key, "OPENAI_API_KEY is set.", "OpenAI is not configured."),
        "postgresql": _env_status(settings.database_url, "DATABASE_URL is set.", "DATABASE_URL is not configured."),
        "redis": _env_status(settings.redis_url, "REDIS_URL is set.", "REDIS_URL is not configured."),
    }

    source_specs = [
        ("yfinance", "yfinance", "market_data", ["stocks", "crypto", "market_regime", "charting"]),
        ("Alpaca Market Data", "alpaca", "market_data", ["stocks", "quotes"]),
        ("Polygon.io", "polygon", "market_data", ["stocks", "options", "intraday"]),
        ("NewsAPI", "newsapi", "news", ["news", "sentiment", "market_radar"]),
        ("Finnhub", "finnhub", "news", ["news", "sentiment", "market_radar"]),
        ("OpenAI", "openai", "internal", ["agents", "explanations"]),
        ("PostgreSQL", "postgresql", "database", ["feature_store", "recommendations", "paper_trading"]),
        ("Redis", "redis", "database", ["caching", "agent_jobs", "sessions"]),
    ]

    sources = [
        DataSourceStatus(
            name=name,
            key=key,
            type=source_type,
            status=checks[key]["status"],
            configured=checks[key]["configured"],
            used_for=used_for,
            last_checked=now,
            message=checks[key]["message"],
        )
        for name, key, source_type, used_for in source_specs
    ]
    sources.append(DataSourceStatus(name="Options Data", key="options_data", type="options", status="not_configured", configured=False, used_for=["options_analysis", "options_flow_agent"], last_checked=now, message="Dedicated options chain and Greeks provider is not configured yet."))
    sources.append(DataSourceStatus(name="Paper Trading", key="paper_trading", type="internal", status="connected", configured=True, used_for=["paper_trading", "outcome_labels"], last_checked=now, message="Paper trading controls are enabled."))

    connected_count = sum(1 for source in sources if source.status == "connected")
    return DataSourcesStatusResponse(connected_sources=connected_count, total_sources=len(sources), sources=sources)
