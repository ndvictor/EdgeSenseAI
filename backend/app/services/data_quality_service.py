from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.market_data_service import MarketDataService
from app.tools.market_data_tools import classify_market_data_source


QualityStatus = Literal["pass", "warn", "fail"]


class DataQualityReport(BaseModel):
    ticker: str
    asset_class: str
    provider: str | None = None
    data_source: str
    quality_status: QualityStatus
    freshness_status: str
    missing_fields: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_MARKET_DATA = MarketDataService()


def _timestamp_status(snapshot: dict[str, Any]) -> tuple[str, list[str]]:
    timestamp = snapshot.get("timestamp") or snapshot.get("last_updated") or snapshot.get("as_of")
    if not timestamp:
        return "unknown", ["Snapshot has no provider timestamp; freshness cannot be fully verified."]
    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError:
        return "unknown", ["Snapshot timestamp could not be parsed."]
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    if age_seconds > 15 * 60:
        return "stale", ["Snapshot timestamp is older than 15 minutes."]
    return "fresh", []


def check_market_data_quality(
    symbol: str,
    asset_class: str = "stock",
    source: str = "auto",
    require_volume: bool | None = None,
    require_spread: bool | None = None,
    snapshot: dict[str, Any] | None = None,
) -> DataQualityReport:
    ticker = symbol.upper()
    snapshot = snapshot or _MARKET_DATA.get_market_snapshot(ticker, source=source)
    data_source = classify_market_data_source(snapshot)
    missing_fields: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    provider = snapshot.get("provider")
    data_quality = snapshot.get("data_quality")
    if not provider:
        blockers.append("No configured provider returned usable data.")
    if data_quality in {"unavailable", "not_configured"}:
        blockers.append(f"Provider data quality is {data_quality}.")
    if snapshot.get("is_mock"):
        warnings.append("Snapshot is mock/demo data and must not be treated as live market data.")

    if snapshot.get("price") is None:
        missing_fields.append("price")
        blockers.append("Price is required for feature generation and model routing.")

    volume_required = require_volume if require_volume is not None else asset_class in {"stock", "option", "crypto"}
    spread_required = require_spread if require_spread is not None else asset_class in {"stock", "option"}
    if volume_required and snapshot.get("volume") is None:
        missing_fields.append("volume")
        warnings.append("Volume is missing; volume and liquidity features will be limited.")
    if spread_required and snapshot.get("bid_ask_spread") is None and (snapshot.get("bid") is None or snapshot.get("ask") is None):
        missing_fields.append("spread")
        warnings.append("Spread fields are missing; tradability and spread-quality checks are limited.")

    if asset_class == "option":
        option_fields = ["expiration", "strike", "option_type", "open_interest", "implied_volatility"]
        missing_option_fields = [field for field in option_fields if snapshot.get(field) is None]
        if missing_option_fields:
            missing_fields.extend(missing_option_fields)
            warnings.append("Options snapshot fields are missing; options-specific models should not run.")

    freshness_status, freshness_warnings = _timestamp_status(snapshot)
    warnings.extend(freshness_warnings)
    if freshness_status == "stale":
        blockers.append("Snapshot is stale.")

    if snapshot.get("tradable") is False:
        blockers.append("Provider marks the asset as not tradable.")
    elif snapshot.get("tradable") is None:
        warnings.append("Tradability status is unknown.")

    quality_status: QualityStatus = "pass"
    if blockers:
        quality_status = "fail"
    elif warnings or missing_fields:
        quality_status = "warn"

    return DataQualityReport(
        ticker=ticker,
        asset_class=asset_class,
        provider=provider,
        data_source=data_source,
        quality_status=quality_status,
        freshness_status=freshness_status,
        missing_fields=sorted(set(missing_fields)),
        blockers=blockers,
        warnings=warnings,
    )
