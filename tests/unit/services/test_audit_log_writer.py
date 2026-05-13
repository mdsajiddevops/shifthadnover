"""T-032 — Unit tests for Audit Log Writer (COMP-016, REQ-010, REQ-007)."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, call


def _make_session():
    return MagicMock()


class TestWritePermissionDenied:
    def test_adds_entry_with_correct_fields(self):
        from services.audit_log_writer import write_permission_denied

        session = _make_session()
        entry = write_permission_denied(
            actor_user_id="user_1",
            resource_id="res-001",
            denied_operation="CORE_ACTION_EXECUTE",
            details={"reason": "role insufficient"},
            db_session=session,
        )

        assert entry.event_type == "permission_denied"
        assert entry.actor_user_id == "user_1"
        assert entry.resource_id == "res-001"
        assert entry.denied_operation == "CORE_ACTION_EXECUTE"
        assert entry.core_action_id is None
        assert isinstance(entry.recorded_at, datetime)
        session.add.assert_called_once_with(entry)

    def test_does_not_call_commit(self):
        from services.audit_log_writer import write_permission_denied

        session = _make_session()
        write_permission_denied("u", "r", "op", None, session)
        session.commit.assert_not_called()


class TestWriteActionLifecycle:
    def test_action_completed_entry_has_correct_fields(self):
        from services.audit_log_writer import write_action_lifecycle

        session = _make_session()
        entry = write_action_lifecycle(
            core_action_id="ca-001",
            event_type="action_completed",
            actor_user_id="user_1",
            resource_id="res-001",
            details=None,
            db_session=session,
        )

        assert entry.event_type == "action_completed"
        assert entry.core_action_id == "ca-001"
        assert entry.actor_user_id == "user_1"
        assert entry.resource_id == "res-001"
        assert isinstance(entry.recorded_at, datetime)
        session.add.assert_called_once_with(entry)

    def test_unknown_event_type_raises_before_db_write(self):
        from services.audit_log_writer import write_action_lifecycle

        session = _make_session()
        with pytest.raises(ValueError, match="Unknown event_type"):
            write_action_lifecycle("ca", "INVALID_EVENT", "u", "r", None, session)
        session.add.assert_not_called()

    def test_does_not_call_commit(self):
        from services.audit_log_writer import write_action_lifecycle

        session = _make_session()
        write_action_lifecycle("ca", "action_initiated", "u", "r", None, session)
        session.commit.assert_not_called()

    def test_two_writes_produce_distinct_entries(self):
        from services.audit_log_writer import write_action_lifecycle

        session = _make_session()
        e1 = write_action_lifecycle("ca", "action_initiated", "u", "r", None, session)
        e2 = write_action_lifecycle("ca", "action_completed", "u", "r", None, session)

        assert e1 is not e2
        assert e1.event_type != e2.event_type
        assert session.add.call_count == 2


class TestAppendOnlyContract:
    def test_writer_has_no_update_method(self):
        import services.audit_log_writer as module
        assert not hasattr(module, "update")
        assert not hasattr(module, "delete")
        assert not hasattr(module, "overwrite")
