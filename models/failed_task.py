"""
FailedTask — dead-letter queue record (ADR-005).

Written exclusively by tasks/dlq_handler.py when a Celery task exhausts all
retries.  Provides operator-visible records for forensic review without
requiring Celery tooling.
"""
from datetime import datetime
from models.models import db


class FailedTask(db.Model):
    __tablename__ = 'failed_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Celery task identity
    celery_task_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    task_name = db.Column(db.String(255), nullable=False, index=True)
    task_args = db.Column(db.Text, nullable=True)       # JSON-serialised positional args
    task_kwargs = db.Column(db.Text, nullable=True)     # JSON-serialised keyword args

    # Failure details
    error_message = db.Column(db.String(1000), nullable=True)
    error_trace = db.Column(db.Text, nullable=True)     # Full traceback

    # Lifecycle
    status = db.Column(
        db.String(50),
        nullable=False,
        default='failed',
        index=True,
    )  # 'failed' | 'pending_retry' | 'resolved'

    retry_count = db.Column(db.Integer, nullable=False, default=0)
    max_retries = db.Column(db.Integer, nullable=False, default=3)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Operations alert tracking
    alert_dispatched = db.Column(db.Boolean, nullable=False, default=False)
    alert_dispatched_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f'<FailedTask id={self.id} task={self.task_name!r} '
            f'status={self.status!r}>'
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'celery_task_id': self.celery_task_id,
            'task_name': self.task_name,
            'status': self.status,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'alert_dispatched': self.alert_dispatched,
        }
