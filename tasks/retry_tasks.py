"""
Task retry sweep Celery task (COMP-009).

Periodically queries the failed_tasks table for records in 'pending_retry'
status and re-enqueues them.  Retries this sweep task itself up to 3 times
on transient DB failures.

REQ-006: dead-letter records can be manually promoted to 'pending_retry' by an
operator to trigger a re-attempt via this sweep.
"""
import json
import logging
from datetime import datetime

from celery_app import celery
from tasks.dlq_handler import on_task_failure as _dlq_on_failure

logger = logging.getLogger(__name__)

# Module-level imports so tests can patch tasks.retry_tasks.FailedTask / db.
try:
    from models.failed_task import FailedTask
    from models.models import db
except Exception:
    FailedTask = None  # type: ignore[assignment]
    db = None  # type: ignore[assignment]


@celery.task(
    name='tasks.retry_tasks.retry_failed_tasks',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def retry_failed_tasks(self):
    """Re-enqueue failed_tasks records that an operator has promoted to pending_retry."""
    try:
        pending = FailedTask.query.filter_by(status='pending_retry').all()
        requeued = 0
        errors = 0

        for record in pending:
            try:
                celery.send_task(
                    record.task_name,
                    args=json.loads(record.task_args or '[]'),
                    kwargs=json.loads(record.task_kwargs or '{}'),
                )
                record.status = 'requeued'
                record.updated_at = datetime.utcnow()
                requeued += 1
                logger.info(
                    'retry_failed_tasks: re-enqueued %s (id=%d)',
                    record.task_name,
                    record.id,
                )
            except Exception as task_exc:
                logger.error(
                    'retry_failed_tasks: failed to re-enqueue id=%d: %s',
                    record.id,
                    task_exc,
                )
                errors += 1

        db.session.commit()
        return {'requeued': requeued, 'errors': errors, 'total': len(pending)}

    except Exception as exc:
        logger.warning(
            'retry_failed_tasks sweep failed (attempt %d/%d): %s',
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
        )
        try:
            raise self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            _dlq_on_failure(
                task_id=self.request.id,
                task_name=self.name,
                args=self.request.args,
                kwargs=self.request.kwargs,
                exc=exc,
                retry_count=self.request.retries,
                max_retries=self.max_retries,
            )
            raise
