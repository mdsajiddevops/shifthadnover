"""
Section Lock Coordinator — COMP-013 (CTCOAMSHM-115, REQ-009)

Wraps the existing SectionLock model with acquire/release operations for
CoreAction concurrency control.  All DB ops use the caller-supplied db_session
so this coordinator participates in the caller's transaction boundary.
"""
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from models.collaboration import SectionLock

LOCK_TTL_SECONDS_DEFAULT = 300


class LockConflictError(Exception):
    """Raised when a section is already locked by another actor."""

    def __init__(self, locked_by: str, expires_at=None):
        self.locked_by = locked_by
        self.expires_at = expires_at
        super().__init__(f"Section is locked by {locked_by}")


class LockNotFoundError(Exception):
    """Raised when the requested lock does not exist."""
    pass


class LockNotOwnedError(Exception):
    """Raised when the requesting actor does not own the lock."""

    def __init__(self, owned_by: str):
        self.owned_by = owned_by
        super().__init__(f"Lock is owned by {owned_by}")


def acquire_lock(
    section_id: str,
    resource_id,
    actor_user_id: str,
    db_session,
    lock_ttl_seconds: int = LOCK_TTL_SECONDS_DEFAULT,
) -> dict:
    """Try to acquire a lock on (section_id, resource_id) for actor_user_id.

    Uses a query-then-insert pattern guarded by the unique constraint on
    (shift_id, section_type, item_id) in the underlying SectionLock table.
    Concurrent duplicate inserts are caught via IntegrityError and re-raised
    as LockConflictError so callers always see a clean 409.

    Returns a dict with lock_id, section_id, and expires_at on success.
    Raises LockConflictError if the section is held by another user.
    """
    resource_id_str = str(resource_id)
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=lock_ttl_seconds)

    existing = (
        db_session.query(SectionLock)
        .filter(
            SectionLock.section_type == section_id,
            SectionLock.item_id == resource_id_str,
        )
        .first()
    )

    if existing:
        if existing.expires_at < now:
            existing.user_id = actor_user_id
            existing.locked_at = now
            existing.expires_at = expires_at
            db_session.add(existing)
            return {
                "lock_id": str(existing.id),
                "section_id": section_id,
                "expires_at": expires_at.isoformat() + "Z",
            }
        if str(existing.user_id) == str(actor_user_id):
            existing.expires_at = expires_at
            db_session.add(existing)
            return {
                "lock_id": str(existing.id),
                "section_id": section_id,
                "expires_at": expires_at.isoformat() + "Z",
            }
        raise LockConflictError(
            locked_by=str(existing.user_id),
            expires_at=existing.expires_at.isoformat() + "Z" if existing.expires_at else None,
        )

    lock = SectionLock(
        shift_id=0,
        user_id=actor_user_id,
        section_type=section_id,
        item_id=resource_id_str,
        expires_at=expires_at,
    )
    db_session.add(lock)
    try:
        db_session.flush()
    except IntegrityError:
        # Concurrent insert won the race — treat as a lock conflict
        db_session.rollback()
        existing = (
            db_session.query(SectionLock)
            .filter(
                SectionLock.section_type == section_id,
                SectionLock.item_id == resource_id_str,
            )
            .first()
        )
        locked_by = str(existing.user_id) if existing else "unknown"
        exp = existing.expires_at.isoformat() + "Z" if existing and existing.expires_at else None
        raise LockConflictError(locked_by=locked_by, expires_at=exp)

    return {
        "lock_id": str(lock.id),
        "section_id": section_id,
        "expires_at": expires_at.isoformat() + "Z",
    }


def release_lock(lock_id, actor_user_id: str, db_session) -> dict:
    """Release the lock identified by lock_id if owned by actor_user_id.

    Returns a dict with lock_id and section_id on success.
    Raises LockNotFoundError if the lock does not exist.
    Raises LockNotOwnedError if the lock is owned by a different actor.
    """
    lock = db_session.query(SectionLock).filter(SectionLock.id == lock_id).first()
    if lock is None:
        raise LockNotFoundError(f"Lock {lock_id} not found")
    if str(lock.user_id) != str(actor_user_id):
        raise LockNotOwnedError(owned_by=str(lock.user_id))
    section_id = lock.section_type
    db_session.delete(lock)
    return {"lock_id": str(lock_id), "section_id": section_id}
