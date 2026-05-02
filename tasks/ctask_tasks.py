"""
CTask auto-assignment Celery task (COMP-010).

Dispatched every 2 minutes by Celery Beat (see celeryconfig.py).
Retries up to 3 times with a 30-second interval on transient failures.
After all retries are exhausted the on_failure hook routes the record to the
DLQ (tasks/dlq_handler.py).

REQ-003: all scheduled execution happens in Celery, not in-process.
REQ-006: max_retries=3, countdown=30.
"""
import logging
from celery_app import celery
from tasks.dlq_handler import on_task_failure as _dlq_on_failure

logger = logging.getLogger(__name__)


@celery.task(
    name='tasks.ctask_tasks.run_ctask_assignment',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_ctask_assignment(self):
    """Process unassigned ServiceNow CTasks and assign them to on-shift engineers."""
    try:
        from models.app_config import AppConfig
        if not AppConfig.is_enabled('feature_ctask_assignment'):
            logger.debug('run_ctask_assignment: feature disabled, skipping.')
            return {'skipped': True, 'reason': 'feature_ctask_assignment disabled'}

        from services.ctask_assignment_service import CTaskAssignmentService
        service = CTaskAssignmentService()
        result = service.process_unassigned_ctasks()
        logger.info('run_ctask_assignment completed: %s', result)
        return result

    except Exception as exc:
        logger.warning(
            'run_ctask_assignment failed (attempt %d/%d): %s',
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
