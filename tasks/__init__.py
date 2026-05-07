"""
Tasks package — Celery task modules for ShiftHandover (COMP-007–011).

Importing this package makes all tasks available for autodiscovery.
The Celery app instance lives in celery_app.py; tasks import it from there.

To run workers:
    celery -A celery_app worker --loglevel=info
    celery -A celery_app beat  --loglevel=info
"""
from celery_app import celery  # noqa: F401 — re-export so 'celery -A tasks' resolves the app
