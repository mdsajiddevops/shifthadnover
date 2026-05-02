"""
Celery application factory (COMP-005).

Broker URL and result backend are read exclusively from environment variables
(REQ-003, ADR-002).  The Flask app context is applied lazily so this module
can be imported by the Celery worker without importing the full Flask stack
at module load time.

Worker startup:
    celery -A celery_app worker --loglevel=info

Beat startup:
    celery -A celery_app beat --loglevel=info
"""
import os
from celery import Celery

BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

if not os.environ.get('CELERY_BROKER_URL'):
    import logging
    logging.getLogger(__name__).warning(
        'CELERY_BROKER_URL is not set; defaulting to redis://redis:6379/0. '
        'Set the variable explicitly in production.'
    )

celery = Celery(
    'shifthandover',
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        'tasks.email_tasks',
        'tasks.servicenow_tasks',
        'tasks.retry_tasks',
        'tasks.ctask_tasks',
    ],
)

# Load beat schedule + serialisation settings from celeryconfig.py
celery.config_from_object('celeryconfig')


class ContextTask(celery.Task):
    """Task base class that wraps each execution in a Flask app context."""
    abstract = True
    _flask_app = None

    @property
    def flask_app(self):
        if self._flask_app is None:
            try:
                from app import app as _app
                self._flask_app = _app
            except ImportError:
                return None
        return self._flask_app

    def __call__(self, *args, **kwargs):
        app = self.flask_app
        if app is not None:
            # Production: run inside Flask app context.
            # self.run is a bound method — task instance is prepended automatically.
            with app.app_context():
                return self.run(*args, **kwargs)
        # Flask unavailable (e.g. unit test runner): call the raw function so
        # tests can supply a mock task-self as args[0] without a double-self TypeError.
        fn = getattr(self.run, '__func__', self.run)
        return fn(*args, **kwargs)


celery.Task = ContextTask


# ---------------------------------------------------------------------------
# Backward-compatibility shim: keep make_celery() so any code that called
# make_celery(app) continues to work during the transition period.
# ---------------------------------------------------------------------------
def make_celery(app):  # noqa: ARG001  (app argument accepted but unused)
    """Deprecated factory shim — returns the module-level celery instance."""
    import logging
    logging.getLogger(__name__).warning(
        'make_celery() is deprecated; import celery_app.celery directly.'
    )
    return celery
