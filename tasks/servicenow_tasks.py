"""
ServiceNow polling Celery task (COMP-008).

Periodically fetches updated incidents and CTasks from ServiceNow and
caches them locally.  Retries up to 3 times with a 30-second interval;
routes to DLQ on exhaustion.

REQ-003, REQ-006.
"""
import logging
from celery_app import celery
from tasks.dlq_handler import on_task_failure as _dlq_on_failure

logger = logging.getLogger(__name__)

# Module-level imports so tests can patch tasks.servicenow_tasks.AppConfig / ServiceNowService.
try:
    from models.app_config import AppConfig
    from services.servicenow_service import ServiceNowService
except Exception:
    AppConfig = None  # type: ignore[assignment,misc]
    ServiceNowService = None  # type: ignore[assignment,misc]


@celery.task(
    name='tasks.servicenow_tasks.poll_servicenow',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def poll_servicenow(self):
    """Poll ServiceNow for new/updated incidents and CTasks and sync them locally."""
    try:
        if not AppConfig.is_enabled('feature_servicenow_sync'):
            logger.debug('poll_servicenow: feature disabled, skipping.')
            return {'skipped': True, 'reason': 'feature_servicenow_sync disabled'}

        service = ServiceNowService()

        if not service.is_configured():
            logger.debug('poll_servicenow: ServiceNow not configured, skipping.')
            return {'skipped': True, 'reason': 'ServiceNow not configured'}

        result = service.sync_incidents_and_ctasks()
        logger.info('poll_servicenow completed: %s', result)
        return result

    except Exception as exc:
        logger.warning(
            'poll_servicenow failed (attempt %d/%d): %s',
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
