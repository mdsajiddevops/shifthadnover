"""
Audit service (COMP-014).

Provides:
  - log_action(): lightweight single-row audit log write (used throughout the app).
  - submit_handover_with_audit(): executes a handover record write and an
    audit log write atomically within a single SQLAlchemy transaction.
    Either both records are committed or neither is (REQ-015).
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Module-level imports so tests can patch services.audit_service.db / current_user / etc.
try:
    from flask_login import current_user
    from flask import request
    from models.models import db
    from models.audit_log import AuditLog
except Exception:
    current_user = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    db = None  # type: ignore[assignment]
    AuditLog = None  # type: ignore[assignment,misc]


def log_action(action: str, details: str | None = None) -> None:
    """Write a single audit log entry and commit.

    This is the lightweight path used by route handlers that do not need the
    full atomic handover transaction (e.g. view events, admin actions).
    """
    user_id = getattr(current_user, 'id', None)
    username = getattr(current_user, 'username', None)
    db.session.add(AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        details=details or f"Path: {request.path}",
    ))
    db.session.commit()


def submit_handover_with_audit(
    handover_record,
    action: str,
    details: str | None = None,
) -> None:
    """Persist a handover record and an audit log entry atomically.

    Both the handover_record and the AuditLog row are added to the same
    SQLAlchemy session and committed together.  If any step fails the
    entire transaction is rolled back and the exception is re-raised so
    the caller can surface a clear error to the client (REQ-015).

    Args:
        handover_record: Any SQLAlchemy model instance to be added/flushed.
        action:          Audit log action label.
        details:         Optional human-readable details string.

    Raises:
        Exception: Re-raised after rollback if either write fails.
    """
    user_id = getattr(current_user, 'id', None)
    username = getattr(current_user, 'username', None)

    audit_entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        details=details or f"Path: {request.path}",
        timestamp=datetime.utcnow(),
    )

    try:
        db.session.add(handover_record)
        db.session.add(audit_entry)
        db.session.commit()
        logger.debug(
            'submit_handover_with_audit: committed handover=%r audit=%r',
            handover_record,
            action,
        )
    except Exception as exc:
        db.session.rollback()
        logger.error(
            'submit_handover_with_audit: transaction rolled back — %s', exc
        )
        raise
