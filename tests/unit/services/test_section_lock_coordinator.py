"""T-030 — Unit tests for Section Lock Coordinator (COMP-013, REQ-009)."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

SECTION_ID = "incidents"
RESOURCE_ID = "resource-001"
ACTOR_A = "user_1"
ACTOR_B = "user_2"


def _make_mock_lock(user_id, expires_delta_seconds=300, lock_id=1):
    lock = MagicMock()
    lock.id = lock_id
    lock.user_id = user_id
    lock.expires_at = datetime.utcnow() + timedelta(seconds=expires_delta_seconds)
    lock.section_type = SECTION_ID
    lock.item_id = RESOURCE_ID
    return lock


def _make_db_session(existing_lock=None):
    session = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = existing_lock
    query_mock.filter.return_value = filter_mock
    session.query.return_value = query_mock
    return session


class TestAcquireLock:
    def test_acquire_unlocked_resource_returns_lock_info(self):
        from services.section_lock_coordinator import acquire_lock

        session = _make_db_session(existing_lock=None)

        with patch("services.section_lock_coordinator.SectionLock") as MockLock:
            new_lock = MagicMock()
            new_lock.id = 42
            MockLock.return_value = new_lock

            result = acquire_lock(SECTION_ID, RESOURCE_ID, ACTOR_A, session)

        assert result["section_id"] == SECTION_ID
        assert "lock_id" in result
        assert "expires_at" in result
        assert isinstance(result["expires_at"], str)
        assert session.add.called

    def test_acquire_locked_by_another_raises_conflict(self):
        from services.section_lock_coordinator import acquire_lock, LockConflictError

        existing = _make_mock_lock(user_id=ACTOR_B, expires_delta_seconds=200)
        session = _make_db_session(existing_lock=existing)

        with pytest.raises(LockConflictError) as exc_info:
            acquire_lock(SECTION_ID, RESOURCE_ID, ACTOR_A, session)

        assert exc_info.value.locked_by == ACTOR_B
        assert exc_info.value.expires_at is not None

    def test_acquire_expired_lock_takes_over(self):
        from services.section_lock_coordinator import acquire_lock

        expired = _make_mock_lock(user_id=ACTOR_B, expires_delta_seconds=-10)
        session = _make_db_session(existing_lock=expired)

        result = acquire_lock(SECTION_ID, RESOURCE_ID, ACTOR_A, session)

        assert "lock_id" in result
        assert session.add.called

    def test_commit_is_never_called_by_coordinator(self):
        from services.section_lock_coordinator import acquire_lock

        session = _make_db_session(existing_lock=None)

        with patch("services.section_lock_coordinator.SectionLock"):
            acquire_lock(SECTION_ID, RESOURCE_ID, ACTOR_A, session)

        session.commit.assert_not_called()


class TestReleaseLock:
    def test_release_by_owner_returns_lock_info(self):
        from services.section_lock_coordinator import release_lock

        existing = _make_mock_lock(user_id=ACTOR_A, lock_id=99)
        session = _make_db_session(existing_lock=existing)

        result = release_lock(lock_id=99, actor_user_id=ACTOR_A, db_session=session)

        assert result["lock_id"] == "99"
        assert "section_id" in result
        session.delete.assert_called_once_with(existing)

    def test_release_by_non_owner_raises_not_owned(self):
        from services.section_lock_coordinator import release_lock, LockNotOwnedError

        existing = _make_mock_lock(user_id=ACTOR_A, lock_id=99)
        session = _make_db_session(existing_lock=existing)

        with pytest.raises(LockNotOwnedError):
            release_lock(lock_id=99, actor_user_id=ACTOR_B, db_session=session)

        session.delete.assert_not_called()

    def test_release_nonexistent_lock_raises_not_found(self):
        from services.section_lock_coordinator import release_lock, LockNotFoundError

        session = _make_db_session(existing_lock=None)

        with pytest.raises(LockNotFoundError):
            release_lock(lock_id=999, actor_user_id=ACTOR_A, db_session=session)

        session.delete.assert_not_called()

    def test_commit_is_never_called_by_coordinator(self):
        from services.section_lock_coordinator import release_lock

        existing = _make_mock_lock(user_id=ACTOR_A, lock_id=99)
        session = _make_db_session(existing_lock=existing)

        release_lock(lock_id=99, actor_user_id=ACTOR_A, db_session=session)

        session.commit.assert_not_called()
