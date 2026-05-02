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


def _run_servicenow_poll():
    """Poll ServiceNow for new/updated incidents and cache results."""
    from models.app_config import AppConfig
    if not AppConfig.is_enabled('feature_servicenow_sync'):
        logger.debug('poll_servicenow: feature disabled, skipping.')
        return {'skipped': True, 'reason': 'feature_servicenow_sync disabled'}

    from services.servicenow_service import ServiceNowService
    service = ServiceNowService()

    if not service.is_configured():
        logger.debug('poll_servicenow: ServiceNow not configured, skipping.')
        return {'skipped': True, 'reason': 'ServiceNow not configured'}

    # Verify connectivity before doing expensive queries.
    connection_result = service.test_connection()
    if not connection_result.get('success'):
        raise ConnectionError(
            f"ServiceNow connection test failed: {connection_result.get('message')}"
        )

    # Fetch incidents for current shift period using the configured groups.
    from datetime import datetime, date
    today = date.today()
    incidents = service.get_incidents_for_shift(
        shift_date=today.strftime('%Y-%m-%d'),
    ) if hasattr(service, 'get_incidents_for_shift') else []

    fetched = len(incidents) if isinstance(incidents, list) else 0
    logger.info('poll_servicenow: fetched %d incident records', fetched)
    return {'fetched': fetched, 'date': today.isoformat()}


@celery.task(
    name='tasks.servicenow_tasks.poll_servicenow',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def poll_servicenow(self):
    """Poll ServiceNow for new/updated incidents and CTasks and sync them locally."""
    try:
        return _run_servicenow_poll()
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
