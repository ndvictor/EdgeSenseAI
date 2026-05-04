"""Platform Persistence Status Service.

Centralizes persistence checks so platform_readiness and Data Sources use the same logic.
Provides honest, non-fake status reporting for database and persistence layer.

Safety:
    - Never exposes secrets or credentials
    - Honest reporting (no fake "connected" status)
    - Clear distinction between postgres and memory fallback
"""

from typing import Any

from sqlalchemy import create_engine, text

from app.core.settings import settings


# Required core source-of-truth tables.
CORE_REQUIRED_TABLES = [
    "candidate_universe",
    "decision_workflow_runs",
    "recommendation_lifecycle",
    "paper_trade_outcomes",
    "model_training_examples",
]

# Required workflow durability tables for the remaining 24-step workflow state.
WORKFLOW_DURABILITY_TABLES = [
    "upper_workflow_runs",
    "trigger_rule_runs",
    "event_scanner_runs",
    "signal_scoring_runs",
    "meta_model_ensemble_runs",
    "recommendation_pipeline_runs",
    "journal_outcomes",
    "performance_drift_runs",
    "research_priority_runs",
    "model_strategy_update_runs",
    "memory_update_runs",
]

REQUIRED_TABLES = [
    *CORE_REQUIRED_TABLES,
    *WORKFLOW_DURABILITY_TABLES,
    "schema_migrations",
]


def check_database_url() -> tuple[bool, str]:
    """Check if DATABASE_URL is configured."""
    if settings.database_url:
        return True, "configured"
    return False, "not configured"


def check_postgres_connection() -> tuple[bool, str]:
    """Check if Postgres is reachable."""
    if not settings.database_url:
        return False, "DATABASE_URL not set"
    try:
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 5},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as e:
        return False, f"connection failed"


def check_tables_exist() -> tuple[list[str], list[str]]:
    """Check which required tables exist. Returns (existing, missing)."""
    if not settings.database_url:
        return [], REQUIRED_TABLES.copy()
    try:
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 5},
        )
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            existing = {row[0] for row in result}
            found = [t for t in REQUIRED_TABLES if t in existing]
            missing = [t for t in REQUIRED_TABLES if t not in existing]
            return found, missing
    except Exception:
        return [], REQUIRED_TABLES.copy()


def check_pgvector() -> tuple[bool, str]:
    """Check if pgvector extension is available."""
    if not settings.database_url:
        return False, "DATABASE_URL not set"
    try:
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 5},
        )
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            """))
            if result.fetchone():
                return True, "available"
            return False, "not installed"
    except Exception:
        return False, "check failed"


def get_persistence_status() -> dict[str, Any]:
    """Get complete persistence status.
    
    Returns status information about database connectivity and persistence tables.
    This is used by platform_readiness and data sources APIs.
    
    Returns:
        dict with keys:
            - mode: "postgres" | "memory" | "unavailable"
            - database_connected: bool
            - database_status: str
            - required_tables: list[str]
            - existing_tables: list[str]
            - missing_tables: list[str]
            - pgvector_available: bool
            - pgvector_status: str
    """
    db_url_ok, db_url_msg = check_database_url()
    pg_ok, pg_msg = check_postgres_connection()
    existing_tables, missing_tables = check_tables_exist()
    pgvector_ok, pgvector_msg = check_pgvector()
    
    core_missing = [table for table in CORE_REQUIRED_TABLES if table in missing_tables]
    workflow_missing = [table for table in WORKFLOW_DURABILITY_TABLES if table in missing_tables]

    # Determine persistence mode
    if not db_url_ok:
        mode = "memory"
    elif not pg_ok:
        mode = "memory"
    elif core_missing:
        mode = "memory"
    elif workflow_missing:
        mode = "partial"
    else:
        mode = "postgres"
    
    return {
        "mode": mode,
        "database_connected": pg_ok,
        "database_status": pg_msg if pg_ok else (db_url_msg if not db_url_ok else pg_msg),
        "required_tables": REQUIRED_TABLES,
        "core_required_tables": CORE_REQUIRED_TABLES,
        "workflow_durability_tables": WORKFLOW_DURABILITY_TABLES,
        "existing_tables": existing_tables,
        "missing_tables": missing_tables,
        "missing_core_tables": core_missing,
        "missing_workflow_durability_tables": workflow_missing,
        "pgvector_available": pgvector_ok,
        "pgvector_status": pgvector_msg,
    }


def get_persistence_summary() -> dict[str, Any]:
    """Get a brief summary for API responses.
    
    Returns a concise summary suitable for inclusion in service responses.
    """
    status = get_persistence_status()
    
    return {
        "persistence_mode": status["mode"],
        "database_connected": status["database_connected"],
        "tables_available": f"{len(status['existing_tables'])}/{len(status['required_tables'])}",
        "pgvector_available": status["pgvector_available"],
    }


def is_postgres_available() -> bool:
    """Quick check if postgres is available for persistence."""
    status = get_persistence_status()
    return status["mode"] == "postgres" and status["database_connected"]


def get_database_health_check() -> dict[str, Any]:
    """Get detailed database health check results.
    
    Used by platform_readiness endpoint.
    """
    db_url_ok, db_url_msg = check_database_url()
    pg_ok, pg_msg = check_postgres_connection()
    existing_tables, missing_tables = check_tables_exist()
    pgvector_ok, pgvector_msg = check_pgvector()
    
    # Build detailed health info
    health = {
        "url_present": db_url_ok,
        "url_status": db_url_msg,
        "connected": pg_ok,
        "connection_status": pg_msg,
        "tables": {
            "required": REQUIRED_TABLES,
            "existing": existing_tables,
            "missing": missing_tables,
            "complete": len(missing_tables) == 0,
        },
        "pgvector": {
            "available": pgvector_ok,
            "status": pgvector_msg,
        },
    }
    
    core_tables_exist = all(t in existing_tables for t in CORE_REQUIRED_TABLES)
    workflow_tables_exist = all(t in existing_tables for t in WORKFLOW_DURABILITY_TABLES)
    health["healthy"] = pg_ok and core_tables_exist and workflow_tables_exist
    health["core_tables_complete"] = core_tables_exist
    health["workflow_durability_tables_complete"] = workflow_tables_exist
    health["workflow_durability_tables"] = {
        "required": WORKFLOW_DURABILITY_TABLES,
        "missing": [table for table in WORKFLOW_DURABILITY_TABLES if table not in existing_tables],
    }
    
    return health
