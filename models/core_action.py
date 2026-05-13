"""
CoreAction ORM model — COMP-012 (CTCOAMSHM-115, REQ-007, REQ-009)

Defines the core_action_records table.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index
from models.models import db


class CoreActionRecord(db.Model):
    __tablename__ = "core_action_records"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    resource_id = db.Column(db.String(36), nullable=False, index=True)
    section_id = db.Column(db.String(128), nullable=False)
    actor_user_id = db.Column(db.String(128), db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="pending")
    payload = db.Column(db.JSON, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    failure_reason = db.Column(db.Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','completed','failed','rolled_back')",
            name="ck_core_action_records_status",
        ),
        Index("ix_core_action_records_resource_id", "resource_id"),
        Index("idx_ca_record_actor", "actor_user_id"),
        Index("idx_ca_record_status_created", "status", "created_at"),
    )

    def __repr__(self):
        return f"<CoreActionRecord {self.id} status={self.status}>"
