"""
Celery Beat periodic schedule.

All four background job types are declared here with their trigger intervals.
Celery Beat runs as a single dedicated process (celery-beat service), so each
job executes exactly once per interval regardless of HTTP worker count — native
deduplication with no application-level locking required (REQ-005).
"""
from datetime import timedelta

# Broker / backend are read from env vars in celery_app.py — not declared here.

beat_schedule = {
    # Email digest: notify teams about pending handovers / shift summary
    'email-digest': {
        'task': 'tasks.email_tasks.send_email_digest',
        'schedule': timedelta(hours=1),
    },
    # ServiceNow polling: sync incidents and CTasks from ServiceNow
    'servicenow-poll': {
        'task': 'tasks.servicenow_tasks.poll_servicenow',
        'schedule': timedelta(minutes=5),
    },
    # Task retry sweep: re-enqueue tasks in the failed_tasks DLQ that are
    # eligible for manual retry (status == 'pending_retry')
    'task-retry-sweep': {
        'task': 'tasks.retry_tasks.retry_failed_tasks',
        'schedule': timedelta(minutes=10),
    },
    # CTask auto-assignment: match unassigned ServiceNow CTasks to on-shift engineers
    'ctask-auto-assign': {
        'task': 'tasks.ctask_tasks.run_ctask_assignment',
        'schedule': timedelta(seconds=120),
    },
}

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True
