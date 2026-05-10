"""Production workflow discovery: never hydrate from manual-env / demo / stale untagged worker rows."""

from __future__ import annotations

from typing import Any

RUN_SOURCE_PRODUCTION_SCANNER = "production_scheduled_scanner"
RUN_SOURCE_PRODUCTION_INGESTION = "production_scheduled_ingestion"
RUN_SOURCE_PRODUCTION_PIPELINE = "production_scheduled_pipeline"
RUN_SOURCE_MANUAL_ENV = "manual_env"
RUN_SOURCE_CANDIDATE_UNIVERSE_FALLBACK = "candidate_universe_fallback"
RUN_SOURCE_DEMO = "demo"
RUN_SOURCE_TEST = "test"
RUN_SOURCE_DEV = "dev"

CANDIDATE_SOURCE_SCANNER = "scanner"
CANDIDATE_SOURCE_MANUAL_ENV = "manual_env"
CANDIDATE_SOURCE_MANUAL_REQUEST = "manual"
CANDIDATE_SOURCE_NONE = "none"
CANDIDATE_SOURCE_CANDIDATE_UNIVERSE = "candidate_universe"

# Feature rows / snapshots with these run_source values must not drive symbols=[] production discovery.
FORBIDDEN_RUN_SOURCES_FOR_PRODUCTION_DISCOVERY: frozenset[str] = frozenset(
    {
        RUN_SOURCE_MANUAL_ENV,
        RUN_SOURCE_CANDIDATE_UNIVERSE_FALLBACK,
        RUN_SOURCE_DEMO,
        RUN_SOURCE_TEST,
        RUN_SOURCE_DEV,
    }
)


def feature_row_allowed_for_production_discovery(row: dict[str, Any]) -> bool:
    """Untagged legacy rows are rejected in production so stale demo/env snapshots cannot hydrate."""
    rs = str(row.get("run_source") or "").strip()
    if not rs:
        return False
    return rs not in FORBIDDEN_RUN_SOURCES_FOR_PRODUCTION_DISCOVERY


def filter_feature_rows_for_production_discovery(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows if feature_row_allowed_for_production_discovery(r)]
