"""
Email digest Celery task (COMP-007).

Sends a shift handover email digest on a schedule defined in celeryconfig.py.
Retries up to 3 times with a 30-second interval; routes to DLQ on exhaustion.

REQ-003, REQ-006.
"""
import logging
from celery_app import celery
from tasks.dlq_handler import on_task_failure as _dlq_on_failure

logger = logging.getLogger(__name__)


def _run_email_digest():
    """Execute email digest logic, importing service lazily to avoid circular imports."""
    from models.app_config import AppConfig
    if not AppConfig.is_enabled('feature_email_digest'):
        logger.debug('send_email_digest: feature disabled, skipping.')
        return {'skipped': True, 'reason': 'feature_email_digest disabled'}

    # Collect all pending handovers that need email notification.
    from models.models import db
    from models.models import Handover
    from services.email_service import send_handover_email
    from datetime import datetime, timedelta

    # Find handovers submitted in the last digest window that haven't been emailed.
    since = datetime.utcnow() - timedelta(hours=1)
    pending = db.session.query(Handover).filter(
        Handover.submitted_at >= since,
        Handover.email_sent.is_(False),
    ).all() if hasattr(Handover, 'email_sent') else []

    sent = 0
    errors = 0
    for handover in pending:
        try:
            send_handover_email(handover)
            sent += 1
        except Exception as e:
            logger.error('send_email_digest: failed for handover %s: %s', handover.id, e)
            errors += 1

    return {'sent': sent, 'errors': errors, 'total': len(pending)}


@celery.task(
    name='tasks.email_tasks.send_email_digest',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_email_digest(self):
    """Send periodic shift handover email digest to configured recipients."""
    try:
        return _run_email_digest()
    except Exception as exc:
        logger.warning(
            'send_email_digest failed (attempt %d/%d): %s',
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
