"""
Audit Log Writer — COMP-016 (CTCOAMSHM-115, REQ-010, REQ-007)

Append-only writer for CoreAction audit entries.  Never calls commit/rollback —
the CoreAction Service owns the transaction boundary.
"""
from datetime import datetime

from models.core_action_audit import CoreActionAuditEntry, _VALID_EVENT_TYPES

_PERMISSION_EVENTS = {"permission_denied", "lock_denied"}
_LIFECYCLE_EVENTS = _VALID_EVENT_TYPES - _PERMISSION_EVENTS


def write_permission_denied(
    actor_user_id: str,
    resource_id,
    denied_operation: str,
    details: dict | None,
    db_session,
) -> CoreActionAuditEntry:
    """Write a permission_denied audit entry.

    core_action_id is None because denial events are recorded before any
    CoreActionRecord row exists.
    """
    entry = CoreActionAuditEntry(
        core_action_id=None,
        event_type="permission_denied",
        actor_user_id=str(actor_user_id),
        resource_id=str(resource_id) if resource_id is not None else None,
        denied_operation=denied_operation,
        details=details,
        recorded_at=datetime.utcnow(),
    )
    db_session.add(entry)
    return entry


def write_action_lifecycle(
    core_action_id,
    event_type: str,
    actor_user_id: str,
    resource_id,
    details: dict | None,
    db_session,
) -> CoreActionAuditEntry:
    """Write an action lifecycle audit entry.

    Raises ValueError for unknown event_type values so the constraint is
    enforced at the application layer before any DB write is attempted.
    """
    if event_type not in _VALID_EVENT_TYPES:
        raise ValueError(
            f"Unknown event_type '{event_type}'. "
            f"Must be one of: {sorted(_VALID_EVENT_TYPES)}"
        )
    entry = CoreActionAuditEntry(
        core_action_id=str(core_action_id) if core_action_id is not None else None,
        event_type=event_type,
        actor_user_id=str(actor_user_id),
        resource_id=str(resource_id) if resource_id is not None else None,
        denied_operation=None,
        details=details,
        recorded_at=datetime.utcnow(),
    )
    db_session.add(entry)
    return entry
