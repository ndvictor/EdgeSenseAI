"""Data ingestion status/readiness layer.

Data Ingestion sits between Data Sources and Data Quality / Feature Store.
This module does not start ingestion jobs yet; it only summarizes readiness.
"""

# from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataIngestionSummary(BaseModel):
    total_sources: int = 7
    active_sources: int = 0
    warning_sources: int = 0
    error_sources: int = 0
    records_ingested_today: int = 0
    last_ingested_at: str | None = None
    next_action: str


class DataIngestionSource(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    key: str
    name: str
    provider_type: str
    status: Literal["ready", "warning", "error", "disabled"]
    ingestion_mode: Literal["pull", "stream", "webhook", "manual"]
    data_types: list[str]
    symbols_tracked: int = 0
    records_ingested_today: int = 0
    last_ingested_at: str | None = None
    freshness_seconds: int | None = None
    latency_ms: int | None = None
    errors: list[str] = Field(default_factory=list)
    next_action: str


class PipelinePosition(BaseModel):
    previous_stage: str = "data_sources"
    current_stage: str = "data_ingestion"
    next_stage: str = "data_quality"
    downstream_stage: str = "feature_store"


class DataIngestionStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok"] = "ok"
    data_mode: Literal["summary"] = "summary"
    updated_at: str
    summary: DataIngestionSummary
    sources: list[DataIngestionSource]
    pipeline_position: PipelinePosition = Field(default_factory=PipelinePosition)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _map_source_status(raw_status: str | None, configured: bool | None) -> Literal["ready", "warning", "error", "disabled"]:
    status = (raw_status or "").lower()
    if status in {"disabled"}:
        return "disabled"
    if status in {"missing_credentials", "not_configured", "not_installed"}:
        return "warning"
    if status in {"configured", "ready", "installed", "test_only"}:
        return "ready"
    if configured is False and status:
        return "warning"
    if not status:
        return "warning"
    return "warning"


def build_data_ingestion_status() -> DataIngestionStatusResponse:
    """
    Summarize ingestion readiness and state across providers.

    Uses existing data source status checks when available, without duplicating
    provider credential logic. Does not start ingestion jobs.
    """

    keyed: dict[str, object] = {}
    try:
        # Lazy import to avoid services importing route modules at import-time.
        from app.api.routes.data_sources import get_data_sources_status  # type: ignore

        ds_status = get_data_sources_status()
        for item in ds_status.sources:
            key = getattr(item, "key", None)
            if key:
                keyed[str(key)] = item
    except Exception:
        keyed = {}

    def _get(key: str) -> dict:
        item = keyed.get(key)
        if not item:
            return {}
        return {
            "status": getattr(item, "status", None),
            "configured": getattr(item, "configured", None),
            "connected": getattr(item, "connected", None),
            "message": getattr(item, "message", None),
        }

    alpaca = _get("alpaca")
    polygon = _get("polygon")
    yfinance = _get("yfinance")
    options_data = _get("options_data")
    paper_trading = _get("paper_trading")

    news_candidates = [_get("newsapi"), _get("finnhub"), _get("benzinga")]
    any_news_configured = any(bool(c.get("configured")) for c in news_candidates if c)
    news_status = "configured" if any_news_configured else "not_configured"

    alpaca_state = _map_source_status(alpaca.get("status"), alpaca.get("configured"))
    polygon_state = _map_source_status(polygon.get("status"), polygon.get("configured"))
    yfinance_state = _map_source_status(yfinance.get("status"), yfinance.get("configured"))
    options_state = _map_source_status(options_data.get("status"), options_data.get("configured"))
    paper_state = _map_source_status(paper_trading.get("status"), paper_trading.get("configured"))

    account_state: Literal["ready", "warning", "error", "disabled"] = "ready" if alpaca_state == "ready" else "warning"

    sources: list[DataIngestionSource] = [
        DataIngestionSource(
            key="alpaca",
            name="Alpaca",
            provider_type="market_data",
            status=alpaca_state,
            ingestion_mode="pull",
            data_types=["quotes", "bars", "trades", "account_state"],
            next_action=(
                "Wire scheduled pulls for quotes/bars/trades; then persist snapshots for downstream feature store."
                if alpaca_state == "ready"
                else "Enable Alpaca market data and set credentials to ingest quotes/bars/trades."
            ),
        ),
        DataIngestionSource(
            key="polygon",
            name="Polygon",
            provider_type="market_data",
            status=polygon_state,
            ingestion_mode="pull",
            data_types=["market_data", "options_data", "intraday"],
            next_action=(
                "Wire Polygon intraday pulls and options chain ingestion; then persist normalized rows."
                if polygon_state == "ready"
                else "Set POLYGON_API_KEY and select Polygon for intraday/options ingestion."
            ),
        ),
        DataIngestionSource(
            key="yfinance",
            name="yfinance",
            provider_type="market_data",
            status=yfinance_state,
            ingestion_mode="pull",
            data_types=["quotes", "bars", "history"],
            next_action=("Use yfinance as research/fallback ingestion (pull mode)." if yfinance_state == "ready" else "Install yfinance and use as fallback ingestion source for research."),
        ),
        DataIngestionSource(
            key="news",
            name="News",
            provider_type="news",
            status=_map_source_status(news_status, any_news_configured),
            ingestion_mode="pull",
            data_types=["news", "catalyst_data", "sentiment"],
            next_action=(
                "Wire scheduled catalyst/news pulls and persist enriched events for downstream scoring."
                if any_news_configured
                else "Enable NEWS_PROVIDER_ENABLED and configure at least one news provider key (NewsAPI/Finnhub/Benzinga)."
            ),
        ),
        DataIngestionSource(
            key="options_data",
            name="Options Data",
            provider_type="options",
            status=options_state,
            ingestion_mode="pull",
            data_types=["options_chain", "iv", "greeks", "flow"],
            next_action=(
                "Wire options chain + IV/Greeks pulls and persist daily option surfaces."
                if options_state == "ready"
                else "Pick an options chain/Greeks provider (Polygon Options recommended) and configure credentials."
            ),
        ),
        DataIngestionSource(
            key="account_state",
            name="Account State",
            provider_type="account",
            status=account_state,
            ingestion_mode="pull",
            data_types=["broker_account_snapshots"],
            next_action=(
                "Persist broker account snapshots (equity/buying power/cash) for risk + execution gates."
                if account_state == "ready"
                else "Connect broker account snapshot ingestion (paper account snapshots supported)."
            ),
        ),
        DataIngestionSource(
            key="paper_trading",
            name="Paper Trading",
            provider_type="internal",
            status=paper_state,
            ingestion_mode="manual",
            data_types=["paper_orders", "paper_fills", "paper_positions"],
            next_action=(
                "Persist paper fills/orders/positions to label outcomes for learning loop."
                if paper_state == "ready"
                else "Enable PAPER_TRADING_ENABLED to record paper orders/fills/positions."
            ),
        ),
    ]

    active_sources = sum(1 for s in sources if s.status == "ready")
    warning_sources = sum(1 for s in sources if s.status == "warning")
    error_sources = sum(1 for s in sources if s.status == "error")

    next_action = (
        "Configure at least one market data provider (Alpaca or Polygon) and enable paper trading to begin ingestion visibility."
        if active_sources == 0
        else "Wire scheduled pulls + persistence for configured providers; then add symbol-level ingestion counters and freshness metrics."
    )

    return DataIngestionStatusResponse(
        updated_at=_now_iso(),
        summary=DataIngestionSummary(
            total_sources=len(sources),
            active_sources=active_sources,
            warning_sources=warning_sources,
            error_sources=error_sources,
            records_ingested_today=0,
            last_ingested_at=None,
            next_action=next_action,
        ),
        sources=sources,
    )

"""Data ingestion status/readiness layer.

Data Ingestion sits between Data Sources and Data Quality / Feature Store.
This module does not start ingestion jobs yet; it only summarizes readiness.
"""

# from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataIngestionSummary(BaseModel):
    total_sources: int = 7
    active_sources: int = 0
    warning_sources: int = 0
    error_sources: int = 0
    records_ingested_today: int = 0
    last_ingested_at: str | None = None
    next_action: str


class DataIngestionSource(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    key: str
    name: str
    provider_type: str
    status: Literal["ready", "warning", "error", "disabled"]
    ingestion_mode: Literal["pull", "stream", "webhook", "manual"]
    data_types: list[str]
    symbols_tracked: int = 0
    records_ingested_today: int = 0
    last_ingested_at: str | None = None
    freshness_seconds: int | None = None
    latency_ms: int | None = None
    errors: list[str] = Field(default_factory=list)
    next_action: str


class PipelinePosition(BaseModel):
    previous_stage: str = "data_sources"
    current_stage: str = "data_ingestion"
    next_stage: str = "data_quality"
    downstream_stage: str = "feature_store"


class DataIngestionStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok"] = "ok"
    data_mode: Literal["summary"] = "summary"
    updated_at: str
    summary: DataIngestionSummary
    sources: list[DataIngestionSource]
    pipeline_position: PipelinePosition = Field(default_factory=PipelinePosition)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _index_by_key(items: list) -> dict[str, object]:
    keyed: dict[str, object] = {}
    for item in items:
        key = getattr(item, "key", None)
        if key:
            keyed[str(key)] = item
    return keyed


def _map_source_status(raw_status: str | None, configured: bool | None) -> Literal["ready", "warning", "error", "disabled"]:
    status = (raw_status or "").lower()
    if status in {"disabled"}:
        return "disabled"
    if status in {"missing_credentials", "not_configured", "not_installed"}:
        return "warning"
    if status in {"configured", "ready", "installed", "test_only"}:
        return "ready"
    if configured is False and status:
        return "warning"
    if not status:
        return "warning"
    return "warning"


def build_data_ingestion_status() -> DataIngestionStatusResponse:
    """
    Summarize ingestion readiness and state across providers.

    Uses existing data source status checks when available, without duplicating
    provider credential logic. Does not start ingestion jobs.
    """

    # Import lazily to avoid services importing route modules at import-time.
    try:
        from app.api.routes.data_sources import get_data_sources_status  # type: ignore

        ds_status = get_data_sources_status()
        keyed = _index_by_key(ds_status.sources)
    except Exception:
        ds_status = None
        keyed = {}

    def _get(key: str):
        item = keyed.get(key)
        if not item:
            return None
        return {
            "status": getattr(item, "status", None),
            "configured": getattr(item, "configured", None),
            "connected": getattr(item, "connected", None),
            "message": getattr(item, "message", None),
        }

    alpaca = _get("alpaca") or {}
    polygon = _get("polygon") or {}
    yfinance = _get("yfinance") or {}
    options_data = _get("options_data") or {}
    paper_trading = _get("paper_trading") or {}

    # Consolidate news into a single stage: any configured provider counts as ready-ish.
    news_candidates = [
        ("newsapi", _get("newsapi") or {}),
        ("finnhub", _get("finnhub") or {}),
        ("benzinga", _get("benzinga") or {}),
    ]
    any_news_configured = any(bool(c.get("configured")) for _, c in news_candidates if c)
    news_status = "configured" if any_news_configured else "not_configured"

    alpaca_state = _map_source_status(alpaca.get("status"), alpaca.get("configured"))
    polygon_state = _map_source_status(polygon.get("status"), polygon.get("configured"))
    yfinance_state = _map_source_status(yfinance.get("status"), yfinance.get("configured"))
    options_state = _map_source_status(options_data.get("status"), options_data.get("configured"))
    paper_state = _map_source_status(paper_trading.get("status"), paper_trading.get("configured"))

    # Account-state ingestion is conceptually separate from market data pulls.
    # For now, gate on Alpaca being configured; do not call broker endpoints here.
    account_state = "ready" if alpaca_state == "ready" else "warning"

    # Improve next action messages deterministically.
    alpaca_next = (
        "Enable Alpaca market data and set credentials to ingest quotes/bars/trades."
        if alpaca_state != "ready"
        else "Wire scheduled pulls for quotes/bars/trades; then persist snapshots for downstream feature store."
    )
    polygon_next = (
        "Set POLYGON_API_KEY and select Polygon for intraday/options ingestion."
        if polygon_state != "ready"
        else "Wire Polygon intraday pulls and options chain ingestion; then persist normalized rows."
    )
    yfinance_next = (
        "Install yfinance and use as fallback ingestion source for research."
        if yfinance_state != "ready"
        else "Use yfinance as research/fallback ingestion (pull mode)."
    )
    news_next = (
        "Enable NEWS_PROVIDER_ENABLED and configure at least one news provider key (NewsAPI/Finnhub/Benzinga)."
        if not any_news_configured
        else "Wire scheduled catalyst/news pulls and persist enriched events for downstream scoring."
    )
    options_next = (
        "Pick an options chain/Greeks provider (Polygon Options recommended) and configure credentials."
        if options_state != "ready"
        else "Wire options chain + IV/Greeks pulls and persist daily option surfaces."
    )
    account_next = (
        "Connect broker account snapshot ingestion (paper account snapshots supported)."
        if account_state != "ready"
        else "Persist broker account snapshots (equity/buying power/cash) for risk + execution gates."
    )
    paper_next = (
        "Enable PAPER_TRADING_ENABLED to record paper orders/fills/positions."
        if paper_state != "ready"
        else "Persist paper fills/orders/positions to label outcomes for learning loop."
    )

    sources: list[DataIngestionSource] = [
        DataIngestionSource(
            key="alpaca",
            name="Alpaca",
            provider_type="market_data",
            status=alpaca_state,
            ingestion_mode="pull",
            data_types=["quotes", "bars", "trades", "account_state"],
            next_action=alpaca_next,
            errors=[],
        ),
        DataIngestionSource(
            key="polygon",
            name="Polygon",
            provider_type="market_data",
            status=polygon_state,
            ingestion_mode="pull",
            data_types=["market_data", "options_data", "intraday"],
            next_action=polygon_next,
            errors=[],
        ),
        DataIngestionSource(
            key="yfinance",
            name="yfinance",
            provider_type="market_data",
            status=yfinance_state,
            ingestion_mode="pull",
            data_types=["quotes", "bars", "history"],
            next_action=yfinance_next,
            errors=[],
        ),
        DataIngestionSource(
            key="news",
            name="News",
            provider_type="news",
            status=_map_source_status(news_status, any_news_configured),
            ingestion_mode="pull",
            data_types=["news", "catalyst_data", "sentiment"],
            next_action=news_next,
            errors=[],
        ),
        DataIngestionSource(
            key="options_data",
            name="Options Data",
            provider_type="options",
            status=options_state,
            ingestion_mode="pull",
            data_types=["options_chain", "iv", "greeks", "flow"],
            next_action=options_next,
            errors=[],
        ),
        DataIngestionSource(
            key="account_state",
            name="Account State",
            provider_type="account",
            status=account_state,  # type: ignore[arg-type]
            ingestion_mode="pull",
            data_types=["broker_account_snapshots"],
            next_action=account_next,
            errors=[],
        ),
        DataIngestionSource(
            key="paper_trading",
            name="Paper Trading",
            provider_type="internal",
            status=paper_state,
            ingestion_mode="manual",
            data_types=["paper_orders", "paper_fills", "paper_positions"],
            next_action=paper_next,
            errors=[],
        ),
    ]

    active_sources = sum(1 for s in sources if s.status == "ready")
    warning_sources = sum(1 for s in sources if s.status == "warning")
    error_sources = sum(1 for s in sources if s.status == "error")

    # Deterministic, status-only summary — no jobs started here.
    next_action = (
        "Configure at least one market data provider (Alpaca or Polygon) and enable paper trading to begin ingestion visibility."
        if active_sources == 0
        else "Wire scheduled pulls + persistence for configured providers; then add symbol-level ingestion counters and freshness metrics."
    )

    return DataIngestionStatusResponse(
        updated_at=_now_iso(),
        summary=DataIngestionSummary(
            total_sources=len(sources),
            active_sources=active_sources,
            warning_sources=warning_sources,
            error_sources=error_sources,
            records_ingested_today=0,
            last_ingested_at=None,
            next_action=next_action,
        ),
        sources=sources,
    )

