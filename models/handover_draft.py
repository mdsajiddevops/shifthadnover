"""
HandoverDraft — persistent Yjs document state for collaborative handover editing.

One row per shift. Stores the serialized Yjs document binary (Y.encodeStateAsUpdate)
written by the WebSocket relay on every sync-step-2 received from a client.

The 24-hour cleanup task (tasks/draft_cleanup_task.py) deletes rows where
updated_at < NOW() - 24h.
"""
from datetime import datetime
from models.models import db


class HandoverDraft(db.Model):
    __tablename__ = 'handover_draft'

    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(
        db.Integer,
        db.ForeignKey('shift.id'),
        nullable=False,
        unique=True,
        index=True,
    )
    # Raw Yjs document state (Y.encodeStateAsUpdate bytes). NULL until the first
    # client sends a sync-step-2.
    ydoc_state = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
    )

    shift = db.relationship('Shift', backref=db.backref('handover_draft', uselist=False))
