"""
Unit tests for services/sse_publisher.py
"""
import json
import pytest
from unittest.mock import MagicMock, patch


class TestPublishCoreActionEvent:
    def _make_session(self):
        session = MagicMock()
        return session

    def _call(self, session, actor="user_123", resource_id="res-456"):
        from services.sse_publisher import publish_core_action_event
        publish_core_action_event(
            core_action_id="ca-001",
            event_type="core_action_change",
            resource_id=resource_id,
            actor=actor,
            db_session=session,
        )

    def test_adds_handover_change_to_session(self):
        session = self._make_session()
        self._call(session)
        session.add.assert_called_once()

    def test_stores_actor_and_resource_id_in_new_value(self):
        session = self._make_session()
        self._call(session, actor="user_abc", resource_id="res-xyz")
        change = session.add.call_args[0][0]
        meta = json.loads(change.new_value)
        assert meta["actor"] == "user_abc"
        assert meta["resource_id"] == "res-xyz"

    def test_item_id_is_core_action_id(self):
        session = self._make_session()
        self._call(session)
        change = session.add.call_args[0][0]
        assert change.item_id == "ca-001"

    def test_change_type_is_core_action_change(self):
        session = self._make_session()
        self._call(session)
        change = session.add.call_args[0][0]
        assert change.change_type == "core_action_change"

    def test_shift_id_sentinel_is_zero(self):
        session = self._make_session()
        self._call(session)
        change = session.add.call_args[0][0]
        assert change.shift_id == 0

    def test_never_calls_commit(self):
        session = self._make_session()
        self._call(session)
        session.commit.assert_not_called()
