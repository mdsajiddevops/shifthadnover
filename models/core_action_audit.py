"""
CoreAction Audit Log ORM model — COMP-017 (CTCOAMSHM-115, REQ-010)

Defines the core_action_audit_entries table (append-only).
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, event
from models.models import db

_VALID_EVENT_TYPES = frozenset({
    "permission_denied",
    "lock_denied",
    "action_initiated",
    "action_completed",
    "action_failed",
    "action_rolled_back",
})


class CoreActionAuditEntry(db.Model):
    __tablename__ = "core_action_audit_entries"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    # Nullable — denial events are written before a core_action_records row exists
    core_action_id = db.Column(
        db.String(36),
        db.ForeignKey("core_action_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = db.Column(db.String(64), nullable=False)
    actor_user_id = db.Column(db.String(128), nullable=False)
    resource_id = db.Column(db.String(36), nullable=True)
    denied_operation = db.Column(db.String(128), nullable=True)
    details = db.Column(db.JSON, nullable=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('permission_denied','lock_denied','action_initiated',"
            "'action_completed','action_failed','action_rolled_back')",
            name="ck_core_action_audit_event_type",
        ),
        Index("ix_core_action_audit_core_action_id", "core_action_id"),
        Index("ix_core_action_audit_actor", "actor_user_id"),
        Index("idx_ca_audit_event_type", "event_type"),
        Index("idx_ca_audit_recorded_at", "recorded_at"),
    )

    def __repr__(self):
        return f"<CoreActionAuditEntry {self.id} event={self.event_type}>"


# Append-only enforcement — ORM-level guard against UPDATE and DELETE
@event.listens_for(CoreActionAuditEntry, "before_update")
def _block_update(mapper, connection, target):
    raise RuntimeError("CoreActionAuditEntry is append-only — updates are not permitted")


@event.listens_for(CoreActionAuditEntry, "before_delete")
def _block_delete(mapper, connection, target):
    raise RuntimeError("CoreActionAuditEntry is append-only — deletes are not permitted")
