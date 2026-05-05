"""Tests for learning-loop resolution_path labeling (target/stop/timed/invalidation)."""

import pytest

from app.services.journal_outcome_service import (
    JournalEntryCreateRequest,
    create_journal_entry,
)


@pytest.fixture(autouse=True)
def clear_journal_memory(monkeypatch):
    """Isolate in-memory journal store between tests."""
    from app.services import journal_outcome_service as mod

    mod._JOURNAL_ENTRIES.clear()
    mod._JOURNAL_CREATE_REQUESTS.clear()
    yield
    mod._JOURNAL_ENTRIES.clear()
    mod._JOURNAL_CREATE_REQUESTS.clear()


def test_long_stop_before_target_resolution():
    req = JournalEntryCreateRequest(
        source_type="paper_trade",
        symbol="TEST",
        entry_price=100.0,
        exit_price=99.0,
        stop_loss=99.0,
        target_price=102.0,
    )
    out = create_journal_entry(req)
    assert out.resolution_path == "stop_first"
    assert out.outcome_label == "loss"


def test_long_target_before_stop_resolution():
    req = JournalEntryCreateRequest(
        source_type="paper_trade",
        symbol="TEST",
        entry_price=100.0,
        exit_price=102.0,
        stop_loss=99.0,
        target_price=102.0,
    )
    out = create_journal_entry(req)
    assert out.resolution_path == "target_first"
    assert out.outcome_label == "win"


def test_long_timed_exit_between_bands():
    req = JournalEntryCreateRequest(
        source_type="paper_trade",
        symbol="TEST",
        entry_price=100.0,
        exit_price=100.5,
        stop_loss=99.0,
        target_price=102.0,
    )
    out = create_journal_entry(req)
    assert out.resolution_path == "timed_exit"
    assert out.outcome_label == "win"


def test_short_stop_first():
    req = JournalEntryCreateRequest(
        source_type="paper_trade",
        symbol="TEST",
        entry_price=100.0,
        exit_price=101.0,
        target_price=98.0,
        stop_loss=101.0,
    )
    out = create_journal_entry(req)
    assert out.resolution_path == "stop_first"
    assert out.outcome_label == "loss"


def test_invalidation_before_entry_no_fill():
    req = JournalEntryCreateRequest(
        source_type="no_trade",
        symbol="TEST",
        actual_outcome="invalidated — setup broke before entry",
    )
    out = create_journal_entry(req)
    assert out.resolution_path == "invalidation_before_entry"


def test_explicit_resolution_override():
    req = JournalEntryCreateRequest(
        source_type="paper_trade",
        symbol="TEST",
        entry_price=100.0,
        exit_price=100.0,
        stop_loss=99.0,
        target_price=102.0,
        resolution_path="stop_first",
    )
    out = create_journal_entry(req)
    assert out.resolution_path == "stop_first"
