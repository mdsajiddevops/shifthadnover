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

# Module-level imports so tests can patch tasks.email_tasks.AppConfig / ShiftEmailService.
try:
    from models.app_config import AppConfig
    from services.shift_email_service import ShiftEmailService
except Exception:
    AppConfig = None  # type: ignore[assignment,misc]
    ShiftEmailService = None  # type: ignore[assignment,misc]


@celery.task(
    name='tasks.email_tasks.send_email_digest',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_email_digest(self):
    """Send periodic shift handover email digest to configured recipients."""
    try:
        if not AppConfig.is_enabled('feature_email_digest'):
            logger.debug('send_email_digest: feature disabled, skipping.')
            return {'skipped': True, 'reason': 'feature_email_digest disabled'}

        service = ShiftEmailService()
        result = service.send_shift_summary_emails()
        logger.info('send_email_digest completed: %s', result)
        return result

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
