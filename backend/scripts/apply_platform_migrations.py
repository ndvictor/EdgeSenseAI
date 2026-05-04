#!/usr/bin/env python3
"""
Apply platform workflow migrations.

Reads DATABASE_URL from settings.
Applies SQL files in backend/db/migrations in lexicographic order.
Skips already applied migrations.
Prints applied/skipped migration names.
Fails loudly on SQL error.

CLI Flags:
    --strict: Exit non-zero if DB is unreachable (for CI/production)
    --dry-run: Show what would be applied without executing
    --only: Apply only a specific migration file

Safety:
    - Never prints credentials
    - Clear pass/fail reporting
    - Memory fallback allowed in non-strict mode
"""

import argparse
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
        print("  Status: DATABASE_URL not configured")
        return None
    try:
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 5},
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as exc:
        print(f"  Status: Connection failed - {exc}")
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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Apply platform workflow migrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python apply_platform_migrations.py              # Normal run
    python apply_platform_migrations.py --dry-run   # Preview only
    python apply_platform_migrations.py --strict    # Fail if DB unreachable
    python apply_platform_migrations.py --only 002_platform_workflow_persistence.sql
        """
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if DATABASE_URL is set but DB is unreachable (for CI/production)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be applied without executing",
    )
    parser.add_argument(
        "--only",
        type=str,
        help="Apply only a specific migration file (by name)",
    )
    return parser.parse_args()


def main() -> int:
    """Main migration runner."""
    args = parse_args()

    print("=" * 60)
    print("Platform Workflow Migrations")
    print("=" * 60)

    # Configuration report
    print("\n[1] Configuration Check")
    print("-" * 40)
    db_url_present = bool(settings.database_url)
    print(f"  DATABASE_URL present: {'yes' if db_url_present else 'no'}")
    if args.strict:
        print("  Mode: STRICT (will fail if DB unreachable)")
    if args.dry_run:
        print("  Mode: DRY RUN (no changes will be made)")
    if args.only:
        print(f"  Filter: Only applying {args.only}")

    # Connection check
    print("\n[2] Connection Check")
    print("-" * 40)
    engine = get_engine()

    if engine is None:
        if db_url_present and args.strict:
            print("\n  RESULT: DB unreachable with --strict flag")
            print("  Migration FAILED")
            return 1
        print("\n  WARNING: DATABASE_URL not configured or connection failed.")
        print("  The platform will use in-memory fallback.")
        return 0

    print("  Status: Connected successfully")

    # Ensure migrations table exists (skip in dry-run mode)
    if not args.dry_run:
        print("\n[3] Schema Migrations Table")
        print("-" * 40)
        ensure_schema_migrations_table(engine)
        print("  Status: schema_migrations table ready")
    else:
        print("\n[3] Schema Migrations Table (dry-run, skipped)")
        print("-" * 40)

    # Get already applied migrations
    applied = get_applied_migrations(engine)
    print("\n[4] Migration Status")
    print("-" * 40)
    print(f"  Already applied: {len(applied)} migration(s)")
    if applied:
        for v in sorted(applied):
            print(f"    - {v}")

    # Find migration files
    if not MIGRATIONS_DIR.exists():
        print(f"\n  ERROR: Migrations directory not found: {MIGRATIONS_DIR}")
        return 1

    all_migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    # Filter if --only specified
    if args.only:
        migration_files = [f for f in all_migration_files if f.name == args.only or f.stem == args.only]
        if not migration_files:
            print(f"\n  ERROR: Migration '{args.only}' not found in {MIGRATIONS_DIR}")
            print(f"  Available: {[f.name for f in all_migration_files]}")
            return 1
    else:
        migration_files = all_migration_files

    print(f"\n[5] Migration Files Found: {len(migration_files)}")
    print("-" * 40)
    for f in migration_files:
        status = "[ALREADY APPLIED]" if f.stem in applied else "[PENDING]"
        print(f"  {status} {f.name}")

    # Execute migrations
    print("\n[6] Applying Migrations")
    print("-" * 40)

    applied_count = 0
    skipped_count = 0
    failed = False

    for migration_file in migration_files:
        version = migration_file.stem

        if version in applied:
            print(f"  [SKIP] {migration_file.name} (already applied)")
            skipped_count += 1
            continue

        sql_content = migration_file.read_text()

        if args.dry_run:
            print(f"  [DRY-RUN] Would apply: {migration_file.name}")
            applied_count += 1
            continue

        print(f"  [APPLY] {migration_file.name}...", end=" ")
        if apply_migration(engine, version, sql_content):
            print("OK")
            applied_count += 1
        else:
            print("FAILED")
            failed = True
            break

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total migrations:    {len(migration_files)}")
    print(f"  Already applied:     {skipped_count}")
    print(f"  Newly applied:       {applied_count}")
    if args.dry_run:
        print(f"  Mode:                DRY RUN (no changes made)")
    print(f"  Database connected:  yes")

    if failed:
        print("\n  RESULT: FAILED")
        return 1

    print("\n  RESULT: SUCCESS")

    # Final status
    print("\n" + "=" * 60)
    if args.dry_run:
        print("Dry run completed - no changes made.")
    else:
        print("Migration completed successfully.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
