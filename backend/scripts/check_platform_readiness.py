#!/usr/bin/env python3
"""
Platform Readiness CLI Checker.

Run backend readiness checks from CLI without starting API.
Checks persistence, configuration, and safety settings.

Usage:
    python check_platform_readiness.py           # Human-readable table
    python check_platform_readiness.py --json    # JSON output
    python check_platform_readiness.py --strict  # Exit non-zero if required checks fail

Safety:
    - Never prints credentials or secrets
    - Honest reporting of DB/pgvector status
    - Memory fallback allowed in non-strict mode
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text

from app.core.settings import settings


CORE_REQUIRED_TABLES = [
    "candidate_universe",
    "decision_workflow_runs",
    "recommendation_lifecycle",
    "paper_trade_outcomes",
    "model_training_examples",
]
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
REQUIRED_TABLES = [*CORE_REQUIRED_TABLES, *WORKFLOW_DURABILITY_TABLES]


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
        return False, f"connection failed: {e}"


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
    except Exception as e:
        return False, f"check failed: {e}"


def check_redis() -> tuple[bool, str]:
    """Check if Redis URL is configured."""
    if settings.redis_url:
        return True, "configured"
    return False, "not configured"


def check_langsmith() -> tuple[bool, str, dict]:
    """Check LangSmith tracing configuration."""
    langsmith_tracing = getattr(settings, 'langsmith_tracing', False)
    langsmith_api_key = getattr(settings, 'langsmith_api_key', None)
    langsmith_project = getattr(settings, 'langsmith_project', None)

    configured = bool(langsmith_tracing and langsmith_api_key and langsmith_project)

    details = {
        "tracing_enabled": langsmith_tracing,
        "api_key_present": bool(langsmith_api_key),
        "project_set": bool(langsmith_project),
    }

    if configured:
        return True, "configured", details
    elif langsmith_tracing:
        return False, "tracing enabled but missing API key or project", details
    else:
        return False, "not configured (no-op mode)", details


def check_live_trading() -> tuple[bool, str]:
    """Check if live trading is disabled (must be False for safety)."""
    live_enabled = getattr(settings, 'live_trading_enabled', False)
    if live_enabled:
        return False, "ENABLED (SAFETY RISK!)"
    return True, "disabled (safe)"


def check_human_approval() -> tuple[bool, str]:
    """Check if human approval is required."""
    required = getattr(settings, 'require_human_approval', True)
    if required:
        return True, "required"
    return False, "not required (SAFETY RISK!)"


def check_paid_llm_calls() -> tuple[bool, str]:
    """Check if paid LLM calls are disabled."""
    paid_calls = getattr(settings, 'llm_paid_calls_enabled', False)
    if paid_calls:
        return False, "ENABLED (COST RISK!)"
    return True, "disabled (safe)"


def run_all_checks() -> dict:
    """Run all readiness checks and return results."""
    db_url_ok, db_url_msg = check_database_url()
    pg_ok, pg_msg = check_postgres_connection()
    existing_tables, missing_tables = check_tables_exist()
    pgvector_ok, pgvector_msg = check_pgvector()
    redis_ok, redis_msg = check_redis()
    langsmith_ok, langsmith_msg, langsmith_details = check_langsmith()
    live_trading_ok, live_trading_msg = check_live_trading()
    human_approval_ok, human_approval_msg = check_human_approval()
    paid_llm_ok, paid_llm_msg = check_paid_llm_calls()

    missing_core = [table for table in CORE_REQUIRED_TABLES if table in missing_tables]
    missing_workflow = [table for table in WORKFLOW_DURABILITY_TABLES if table in missing_tables]

    # Determine persistence mode
    if pg_ok and not missing_core and not missing_workflow:
        persistence_mode = "postgres"
    elif pg_ok and not missing_core and missing_workflow:
        persistence_mode = "partial"
    else:
        persistence_mode = "memory"

    # Collect blockers (required for operation)
    blockers = []
    if not live_trading_ok:
        blockers.append("live_trading must be disabled")
    if not human_approval_ok:
        blockers.append("human_approval must be required")
    if not paid_llm_ok:
        blockers.append("paid_llm_calls must be disabled")

    # Collect warnings (not blocking but notable)
    warnings = []
    if not db_url_ok:
        warnings.append("DATABASE_URL not configured - using memory fallback")
    elif not pg_ok:
        warnings.append("Database unreachable - using memory fallback")
    elif missing_core:
        warnings.append(f"Missing core persistence tables: {', '.join(missing_core)}")
    elif missing_workflow:
        warnings.append(f"Missing workflow durability tables: {', '.join(missing_workflow)}")
    if not redis_ok:
        warnings.append("Redis not configured - caching disabled")
    if not langsmith_ok and langsmith_details.get("tracing_enabled"):
        warnings.append("LangSmith tracing enabled but incomplete configuration")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "persistence_mode": persistence_mode,
        "database": {
            "url_present": db_url_ok,
            "url_status": db_url_msg,
            "postgres_connected": pg_ok,
            "postgres_status": pg_msg,
            "required_tables": REQUIRED_TABLES,
            "core_required_tables": CORE_REQUIRED_TABLES,
            "workflow_durability_tables": WORKFLOW_DURABILITY_TABLES,
            "existing_tables": existing_tables,
            "missing_tables": missing_tables,
            "missing_core_tables": missing_core,
            "missing_workflow_durability_tables": missing_workflow,
        },
        "redis": {
            "configured": redis_ok,
            "status": redis_msg,
        },
        "pgvector": {
            "available": pgvector_ok,
            "status": pgvector_msg,
        },
        "langsmith_tracing": {
            "configured": langsmith_ok,
            "status": langsmith_msg,
            "details": langsmith_details,
        },
        "safety": {
            "live_trading_disabled": live_trading_ok,
            "live_trading_status": live_trading_msg,
            "human_approval_required": human_approval_ok,
            "human_approval_status": human_approval_msg,
            "paid_llm_calls_disabled": paid_llm_ok,
            "paid_llm_status": paid_llm_msg,
        },
        "blockers": blockers,
        "warnings": warnings,
    }


def print_human_readable(results: dict) -> None:
    """Print results in human-readable table format."""
    print("=" * 70)
    print("PLATFORM READINESS CHECK")
    print("=" * 70)
    print(f"Checked at: {results['checked_at']}")
    print(f"Persistence mode: {results['persistence_mode']}")

    print("\n" + "-" * 70)
    print("PERSISTENCE")
    print("-" * 70)

    db = results["database"]
    print(f"  DATABASE_URL:         {db['url_status']}")
    print(f"  Postgres connection:  {db['postgres_status']}")
    print(f"  Required tables:      {len(db['existing_tables'])}/{len(db['required_tables'])}")
    if db['existing_tables']:
        print(f"    Existing:           {', '.join(db['existing_tables'])}")
    if db['missing_tables']:
        print(f"    Missing:            {', '.join(db['missing_tables'])}")

    print(f"  pgvector extension:   {results['pgvector']['status']}")

    print("\n" + "-" * 70)
    print("CACHING & OBSERVABILITY")
    print("-" * 70)
    print(f"  Redis:                {results['redis']['status']}")
    print(f"  LangSmith tracing:    {results['langsmith_tracing']['status']}")

    print("\n" + "-" * 70)
    print("SAFETY CHECKS")
    print("-" * 70)
    safety = results["safety"]
    print(f"  Live trading:         {safety['live_trading_status']}")
    print(f"  Human approval:       {safety['human_approval_status']}")
    print(f"  Paid LLM calls:       {safety['paid_llm_status']}")

    print("\n" + "-" * 70)
    print("BLOCKERS")
    print("-" * 70)
    if results["blockers"]:
        for blocker in results["blockers"]:
            print(f"  [BLOCKER] {blocker}")
    else:
        print("  None - platform is safe to operate")

    print("\n" + "-" * 70)
    print("WARNINGS")
    print("-" * 70)
    if results["warnings"]:
        for warning in results["warnings"]:
            print(f"  [WARNING] {warning}")
    else:
        print("  None")

    print("\n" + "=" * 70)
    if results["blockers"]:
        print("RESULT: NOT READY (blockers present)")
    elif results["warnings"]:
        print("RESULT: PARTIAL (warnings present but not blocking)")
    else:
        print("RESULT: READY")
    print("=" * 70)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check platform readiness without starting API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python check_platform_readiness.py           # Human-readable output
    python check_platform_readiness.py --json   # JSON output
    python check_platform_readiness.py --strict # Exit non-zero if not ready
        """
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if required checks fail (for CI/production)",
    )
    args = parser.parse_args()

    results = run_all_checks()

    if args.json:
        # Remove sensitive details before printing
        safe_results = results.copy()
        if "details" in safe_results.get("langsmith_tracing", {}):
            # Keep details but ensure no actual keys are exposed
            safe_details = safe_results["langsmith_tracing"]["details"]
            safe_details.pop("api_key", None)
            safe_details.pop("api_key_present", None)
        print(json.dumps(safe_results, indent=2))
    else:
        print_human_readable(results)

    # Determine exit code
    if args.strict and results["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
