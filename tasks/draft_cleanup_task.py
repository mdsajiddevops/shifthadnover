"""
Handover draft 24-hour cleanup task (CTCOAMSHM-7).

Deletes HandoverDraft rows whose updated_at is older than 24 hours.
Dispatched daily by Celery Beat (see celeryconfig.py).
Retries up to 3 times with a 30-second delay on transient DB failures.
"""
import logging
from datetime import datetime, timedelta

from celery_app import celery
from tasks.dlq_handler import on_task_failure as _dlq_on_failure

logger = logging.getLogger(__name__)

try:
    from models.handover_draft import HandoverDraft
    from models.models import db
except Exception:
    HandoverDraft = None  # type: ignore[assignment,misc]
    db = None  # type: ignore[assignment,misc]


@celery.task(
    name='tasks.draft_cleanup_task.cleanup_stale_drafts',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    on_failure=_dlq_on_failure,
)
def cleanup_stale_drafts(self):
    """Delete HandoverDraft rows not updated in the past 24 hours."""
    logger.info("TASK_STARTED task_id=%s task_name=%s", self.request.id, self.name)
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        deleted = (
            HandoverDraft.query
            .filter(HandoverDraft.updated_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.session.commit()
        logger.info(
            "TASK_COMPLETED task_id=%s task_name=%s deleted=%d",
            self.request.id, self.name, deleted,
        )
        return {'status': 'ok', 'deleted': deleted}
    except Exception as exc:
        logger.warning(
            "TASK_RETRY task_id=%s attempt=%d/%d error=%s",
            self.request.id, self.request.retries + 1, self.max_retries, exc,
        )
        db.session.rollback()
        raise self.retry(exc=exc)
