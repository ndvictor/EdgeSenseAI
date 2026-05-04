"""Tests for persistence fallback behavior.

Tests that services gracefully fall back to memory when DB is unavailable.
"""

import pytest
from unittest.mock import patch

from app.services.candidate_universe_service import (
    get_candidate_universe_summary,
    get_persistence_mode as candidate_persistence_mode,
)
from app.services.decision_workflow_service import (
    build_default_decision_workflow,
    get_persistence_mode as decision_persistence_mode,
)
from app.services.journal_outcome_service import (
    create_journal_entry,
    get_journal_summary,
    get_persistence_mode as journal_persistence_mode,
    JournalEntryCreateRequest,
)
from app.services.memory_update_service import (
    get_persistence_mode as memory_persistence_mode,
    store_memory,
)


class TestPersistenceFallback:
    """Tests for graceful fallback to memory when DB unavailable."""

    @patch("app.services.candidate_universe_service.get_database_table_status")
    def test_candidate_universe_fallback(self, mock_status):
        """Candidate universe should work when DB is down."""
        mock_status.return_value = {"connected": False}

        # Should report memory mode
        mode = candidate_persistence_mode()
        assert mode == "memory"

        # Summary should still work
        summary = get_candidate_universe_summary()
        assert "persistence_mode" in summary
        assert summary["persistence_mode"] == "memory"

    @patch("app.services.decision_workflow_service.get_database_table_status")
    def test_decision_workflow_fallback(self, mock_status):
        """Decision workflow should work when DB is down."""
        mock_status.return_value = {"connected": False}

        # Should report memory mode
        mode = decision_persistence_mode()
        assert mode == "memory"

        # Workflow should still run (though with no symbols)
        result = build_default_decision_workflow()
        assert result is not None
        assert result.status in ["completed_with_candidates", "completed_no_actionable_candidates", "no_symbols_selected"]

    @patch("app.services.journal_outcome_service.get_database_table_status")
    def test_journal_outcome_fallback(self, mock_status):
        """Journal should work when DB is down."""
        mock_status.return_value = {"connected": False}

        # Should report memory mode
        mode = journal_persistence_mode()
        assert mode == "memory"

        # Create entry should still work
        request = JournalEntryCreateRequest(
            source_type="manual_observation",
            symbol="TEST",
        )
        entry = create_journal_entry(request)
        assert entry is not None
        assert entry.id is not None

        # Summary should include persistence mode
        summary = get_journal_summary()
        assert "persistence_mode" in summary
        assert summary["persistence_mode"] == "memory"

    @patch("app.services.memory_update_service.get_database_table_status")
    def test_memory_update_fallback(self, mock_status):
        """Memory update should work when DB is down."""
        mock_status.return_value = {"connected": False}

        # Should report memory mode
        mode = memory_persistence_mode()
        assert mode == "memory"

        # Store should still work (fallback to memory)
        result = store_memory(
            source_type="test",
            title="Test Entry",
            content="Test content",
        )
        assert result is not None

    def test_all_services_report_persistence_mode(self):
        """All services should have get_persistence_mode function."""
        # Import and verify each service has the function
        from app.services.candidate_universe_service import get_persistence_mode as f1
        from app.services.decision_workflow_service import get_persistence_mode as f2
        from app.services.journal_outcome_service import get_persistence_mode as f3
        from app.services.memory_update_service import get_persistence_mode as f4
        from app.services.recommendation_lifecycle_service import get_persistence_mode as f5

        # Call each and verify they return string
        for fn in [f1, f2, f3, f4, f5]:
            mode = fn()
            assert isinstance(mode, str)
            assert mode in ["postgres", "memory"]
