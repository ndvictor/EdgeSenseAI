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


# Required tables for full persistence
REQUIRED_TABLES = [
    "candidate_universe",
    "decision_workflow_runs",
    "recommendation_lifecycle",
    "paper_trade_outcomes",
    "model_training_examples",
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
    
    # Determine persistence mode
    if not db_url_ok:
        mode = "memory"
    elif not pg_ok:
        mode = "memory"
    elif missing_tables:
        # Partial persistence - some tables exist but not all
        if len(existing_tables) >= 3:  # Threshold for "postgres" mode
            mode = "postgres"
        else:
            mode = "memory"
    else:
        mode = "postgres"
    
    return {
        "mode": mode,
        "database_connected": pg_ok,
        "database_status": pg_msg if pg_ok else (db_url_msg if not db_url_ok else pg_msg),
        "required_tables": REQUIRED_TABLES,
        "existing_tables": existing_tables,
        "missing_tables": missing_tables,
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
    
    # Overall healthy if connected and has at least core tables
    core_tables = ["candidate_universe", "decision_workflow_runs", "recommendation_lifecycle"]
    core_tables_exist = all(t in existing_tables for t in core_tables)
    health["healthy"] = pg_ok and core_tables_exist
    
    return health
