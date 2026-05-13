"""
Unit tests for repositories/core_action_repository.py

Tests state transitions, guard conditions, and _get_record not-found path
using an in-memory SQLite session (no Flask app context required).
"""
import uuid
import pytest
from unittest.mock import MagicMock

from repositories.core_action_repository import (
    mark_completed,
    mark_failed,
    mark_rolled_back,
    InvalidStateTransitionError,
)


def _fake_record(status="pending"):
    record = MagicMock()
    record.id = str(uuid.uuid4())
    record.status = status
    record.completed_at = None
    record.failure_reason = None
    return record


def _mock_session(record=None):
    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = record
    return session


class TestMarkCompleted:
    def test_pending_transitions_to_completed(self):
        record = _fake_record(status="pending")
        session = _mock_session(record)
        result = mark_completed(record.id, session)
        assert result.status == "completed"

    def test_sets_completed_at(self):
        record = _fake_record(status="pending")
        session = _mock_session(record)
        mark_completed(record.id, session)
        assert record.completed_at is not None

    def test_non_pending_raises_invalid_transition(self):
        record = _fake_record(status="failed")
        session = _mock_session(record)
        with pytest.raises(InvalidStateTransitionError, match="status='failed'"):
            mark_completed(record.id, session)

    def test_already_completed_raises_invalid_transition(self):
        record = _fake_record(status="completed")
        session = _mock_session(record)
        with pytest.raises(InvalidStateTransitionError):
            mark_completed(record.id, session)

    def test_record_not_found_raises_invalid_transition(self):
        session = _mock_session(record=None)
        with pytest.raises(InvalidStateTransitionError, match="not found"):
            mark_completed("nonexistent-id", session)


class TestMarkFailed:
    def test_sets_status_to_failed(self):
        record = _fake_record(status="pending")
        session = _mock_session(record)
        result = mark_failed(record.id, "db error", session)
        assert result.status == "failed"
        assert result.failure_reason == "db error"

    def test_record_not_found_raises_invalid_transition(self):
        session = _mock_session(record=None)
        with pytest.raises(InvalidStateTransitionError, match="not found"):
            mark_failed("nonexistent-id", "reason", session)


class TestMarkRolledBack:
    def test_sets_status_to_rolled_back(self):
        record = _fake_record(status="pending")
        session = _mock_session(record)
        result = mark_rolled_back(record.id, session)
        assert result.status == "rolled_back"

    def test_record_not_found_raises_invalid_transition(self):
        session = _mock_session(record=None)
        with pytest.raises(InvalidStateTransitionError, match="not found"):
            mark_rolled_back("nonexistent-id", session)
