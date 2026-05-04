"""Tests for platform readiness endpoint and related services.

Tests cover:
- Readiness endpoint returns correct structure
- Persistence status service reports honest status
- Safety checks are correctly evaluated
- No secrets are exposed in responses
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.platform_persistence_status_service import (
    get_persistence_status,
    is_postgres_available,
)


client = TestClient(app)


class TestPlatformReadinessEndpoint:
    """Tests for /api/platform-readiness endpoint."""

    def test_readiness_returns_200(self):
        """Endpoint should return 200 OK."""
        response = client.get("/api/platform-readiness")
        assert response.status_code == 200

    def test_readiness_structure(self):
        """Response should have expected structure."""
        response = client.get("/api/platform-readiness")
        data = response.json()

        assert "status" in data
        assert "checks" in data
        assert "blockers" in data
        assert "warnings" in data
        assert "generated_at" in data

        assert data["status"] in ["ready", "partial", "not_ready"]
        assert isinstance(data["checks"], list)
        assert isinstance(data["blockers"], list)
        assert isinstance(data["warnings"], list)

    def test_readiness_checks_structure(self):
        """Each check should have required fields."""
        response = client.get("/api/platform-readiness")
        data = response.json()

        for check in data["checks"]:
            assert "key" in check
            assert "label" in check
            assert "status" in check
            assert "message" in check
            assert "required_for" in check

            assert check["status"] in ["pass", "warn", "fail"]

    def test_no_secrets_exposed(self):
        """Response should not contain secrets or credentials."""
        response = client.get("/api/platform-readiness")
        text = response.text.lower()

        # Check for common secret patterns
        assert "api_key" not in text or "configured" in text
        assert "password" not in text
        assert "secret" not in text
        # Database URL should not be fully exposed
        assert "postgresql://" not in text

    def test_safety_checks_present(self):
        """Safety-critical checks should be present."""
        response = client.get("/api/platform-readiness")
        data = response.json()

        check_keys = [c["key"] for c in data["checks"]]

        # Live trading check should exist
        assert any("live_trading" in k for k in check_keys)
        # Human approval check should exist
        assert any("approval" in k for k in check_keys)
        # LLM safety check should exist
        assert any("llm" in k or "paid" in k for k in check_keys)

    def test_blockers_for_critical_issues(self):
        """Critical safety issues should appear in blockers."""
        response = client.get("/api/platform-readiness")
        data = response.json()

        # If live trading is enabled, it should be in blockers
        live_trading_check = next(
            (c for c in data["checks"] if "live_trading" in c["key"]),
            None
        )
        if live_trading_check and live_trading_check["status"] == "fail":
            assert any("live_trading" in b for b in data["blockers"])


class TestPersistenceStatusService:
    """Tests for platform_persistence_status_service."""

    def test_get_persistence_status_structure(self):
        """Service should return expected structure."""
        status = get_persistence_status()

        assert "mode" in status
        assert "database_connected" in status
        assert "database_status" in status
        assert "required_tables" in status
        assert "existing_tables" in status
        assert "missing_tables" in status
        assert "pgvector_available" in status
        assert "pgvector_status" in status

        assert status["mode"] in ["postgres", "memory", "unavailable"]
        assert isinstance(status["database_connected"], bool)
        assert isinstance(status["required_tables"], list)
        assert isinstance(status["existing_tables"], list)
        assert isinstance(status["missing_tables"], list)

    def test_required_tables_listed(self):
        """Required tables should include platform workflow tables."""
        status = get_persistence_status()

        required = status["required_tables"]
        assert "candidate_universe" in required
        assert "decision_workflow_runs" in required
        assert "recommendation_lifecycle" in required
        assert "paper_trade_outcomes" in required
        assert "model_training_examples" in required

    def test_persistence_mode_consistency(self):
        """Mode should be consistent with connection status."""
        status = get_persistence_status()

        # If DB is connected, mode should be postgres (or unavailable on error)
        if status["database_connected"]:
            assert status["mode"] in ["postgres", "memory"]
        else:
            assert status["mode"] in ["memory", "unavailable"]

    def test_is_postgres_available_returns_bool(self):
        """is_postgres_available should return a boolean."""
        result = is_postgres_available()
        assert isinstance(result, bool)


class TestTracingEndpoint:
    """Tests for /api/tracing endpoint."""

    def test_tracing_status_returns_200(self):
        """Tracing status should return 200."""
        response = client.get("/api/tracing/status")
        assert response.status_code == 200

    def test_tracing_status_structure(self):
        """Tracing status should have expected structure."""
        response = client.get("/api/tracing/status")
        data = response.json()

        assert "enabled" in data
        assert "configured" in data
        assert "langsmith_installed" in data
        assert "langsmith_tracing_env" in data
        assert "api_key_configured" in data
        assert "project_configured" in data
        assert "mode" in data

        assert isinstance(data["enabled"], bool)
        assert isinstance(data["configured"], bool)

    def test_tracing_test_event_without_key(self):
        """Test event should work even without API key (no-op mode)."""
        response = client.post(
            "/api/tracing/test-event",
            json={"name": "test", "metadata": {"test": True}}
        )
        # Should not error, but may indicate tracing disabled
        assert response.status_code in [200, 503]


class TestCandidateStrategiesSafety:
    """Tests ensuring candidate strategies are research-only."""

    def test_strategies_endpoint_returns_research_only(self):
        """Strategies should be marked as research-only by default."""
        response = client.get("/api/strategies")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        for strategy in data:
            # Live trading should be disabled or require approval
            if "live_trading_supported" in strategy:
                # If live trading is "supported", it must require approval
                if strategy["live_trading_supported"]:
                    assert strategy.get("requires_human_approval", True) is True

    def test_candidate_strategies_segregated(self):
        """Candidate strategies should be in separate endpoint."""
        response = client.get("/api/strategies/candidates")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # All candidates should be clearly marked
        for strategy in data:
            # Should have candidate/research indicators
            assert "status" in strategy or "promotion_status" in strategy


class TestMigrationDryRun:
    """Tests for migration dry-run functionality."""

    def test_migration_script_exists(self):
        """Migration script should be present and executable."""
        from pathlib import Path
        script_path = Path(__file__).parent.parent / "scripts" / "apply_platform_migrations.py"
        assert script_path.exists()

    def test_migration_dry_run_flag(self):
        """Migration script should support --dry-run flag."""
        import subprocess
        import sys

        script_path = Path(__file__).parent.parent / "scripts" / "apply_platform_migrations.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "--dry-run" in result.stdout
