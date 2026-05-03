#!/usr/bin/env python3
"""
Apply platform workflow migrations.

Reads DATABASE_URL from settings.
Applies SQL files in backend/db/migrations in lexicographic order.
Skips already applied migrations.
Prints applied/skipped migration names.
Fails loudly on SQL error.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.settings import settings


MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"


def get_engine() -> Engine | None:
    """Create database engine."""
    if not settings.database_url:
        print("ERROR: DATABASE_URL not configured")
        return None
    try:
        return create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 5},
        )
    except Exception as exc:
        print(f"ERROR: Failed to create engine: {exc}")
        return None


def ensure_schema_migrations_table(engine: Engine) -> None:
    """Create schema_migrations table if not exists."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.commit()


def get_applied_migrations(engine: Engine) -> set[str]:
    """Get set of already applied migration versions."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM schema_migrations"))
            return {row[0] for row in result}
    except Exception:
        return set()


def apply_migration(engine: Engine, version: str, sql_content: str) -> bool:
    """Apply a single migration. Returns True on success."""
    try:
        with engine.connect() as conn:
            # Execute the migration SQL
            conn.execute(text(sql_content))
            # Record the migration
            conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version},
            )
            conn.commit()
        return True
    except Exception as exc:
        print(f"ERROR: Migration {version} failed: {exc}")
        return False


def main() -> int:
    """Main migration runner."""
    print("=" * 60)
    print("Platform Workflow Migrations")
    print("=" * 60)

    engine = get_engine()
    if engine is None:
        print("\nMigration aborted: DATABASE_URL not configured or connection failed.")
        print("The platform will use in-memory fallback.")
        return 0  # Not a failure - memory fallback is valid

    # Ensure migrations table exists
    ensure_schema_migrations_table(engine)

    # Get already applied migrations
    applied = get_applied_migrations(engine)
    print(f"\nAlready applied: {len(applied)} migrations")

    # Find migration files
    if not MIGRATIONS_DIR.exists():
        print(f"\nERROR: Migrations directory not found: {MIGRATIONS_DIR}")
        return 1

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("\nNo migration files found.")
        return 0

    print(f"\nFound {len(migration_files)} migration file(s)")
    print("-" * 60)

    applied_count = 0
    skipped_count = 0
    failed = False

    for migration_file in migration_files:
        version = migration_file.stem  # e.g., "002_platform_workflow_persistence"

        if version in applied:
            print(f"[SKIP] {migration_file.name}")
            skipped_count += 1
            continue

        print(f"[APPLY] {migration_file.name}...", end=" ")
        sql_content = migration_file.read_text()

        if apply_migration(engine, version, sql_content):
            print("OK")
            applied_count += 1
        else:
            print("FAILED")
            failed = True
            break

    print("-" * 60)
    print(f"\nResults: {applied_count} applied, {skipped_count} skipped")

    if failed:
        print("\nMigration FAILED. Check the error above.")
        return 1

    print("\nMigration completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
