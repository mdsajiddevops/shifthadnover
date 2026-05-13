"""
CoreAction Repository — COMP-011 (CTCOAMSHM-115, REQ-007, REQ-009)

Encapsulates all DB reads and writes for core_action_records.
Never calls db_session.commit() or db_session.rollback() — the
CoreAction Service (COMP-008) owns the transaction boundary.
"""
import uuid
from datetime import datetime

from models.core_action import CoreActionRecord


class InvalidStateTransitionError(Exception):
    """Raised when a status transition is not permitted."""
    pass


def _get_record(record_id: str, db_session) -> "CoreActionRecord":
    record = db_session.query(CoreActionRecord).filter_by(id=record_id).first()
    if record is None:
        raise InvalidStateTransitionError(f"CoreActionRecord {record_id} not found")
    return record


def create_record(
    resource_id,
    section_id: str,
    actor_user_id: str,
    payload: dict,
    db_session,
) -> CoreActionRecord:
    """Insert a new CoreActionRecord in status='pending'.

    resource_id is converted to string if not already.
    Returns the new record (not yet committed).
    """
    record = CoreActionRecord(
        id=str(uuid.uuid4()),
        resource_id=str(resource_id),
        section_id=section_id,
        actor_user_id=str(actor_user_id),
        status="pending",
        payload=payload,
        version=1,
        created_at=datetime.utcnow(),
    )
    db_session.add(record)
    db_session.flush()  # assign PK; caller owns the commit
    return record


def mark_completed(record_id: str, db_session) -> CoreActionRecord:
    """Transition status from 'pending' → 'completed'.

    Raises InvalidStateTransitionError if the record is not in 'pending' status.
    """
    record = _get_record(record_id, db_session)
    if record.status != "pending":
        raise InvalidStateTransitionError(
            f"Cannot mark_completed: record {record_id} is in status='{record.status}'"
        )
    record.status = "completed"
    record.completed_at = datetime.utcnow()
    return record


def mark_failed(record_id: str, failure_reason: str, db_session) -> CoreActionRecord:
    """Transition status to 'failed' and record the failure reason."""
    record = _get_record(record_id, db_session)
    record.status = "failed"
    record.failure_reason = failure_reason
    return record


def mark_rolled_back(record_id: str, db_session) -> CoreActionRecord:
    """Transition status to 'rolled_back'."""
    record = _get_record(record_id, db_session)
    record.status = "rolled_back"
    return record
