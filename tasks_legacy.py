"""
Celery task definitions for ShiftHandover background jobs.
Workers are started via: celery -A tasks worker --loglevel=info
Beat scheduler:          celery -A tasks beat --loglevel=info
"""
from app import app
from celery_app import make_celery

celery = make_celery(app)


@celery.task(name='tasks.run_ctask_assignment', bind=True, max_retries=3)
def run_ctask_assignment(self):
    """Process unassigned CTasks from ServiceNow every 2 minutes."""
    try:
        from models.app_config import AppConfig
        if not AppConfig.is_enabled('feature_ctask_assignment'):
            return {'skipped': True, 'reason': 'feature_ctask_assignment disabled'}

        from services.ctask_assignment_service import CTaskAssignmentService
        service = CTaskAssignmentService()
        result = service.process_unassigned_ctasks()
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
