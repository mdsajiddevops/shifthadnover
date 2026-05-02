from celery import Celery
from celery.schedules import crontab


def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
        backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    )
    celery.conf.update(app.config)

    celery.conf.beat_schedule = {
        'ctask-auto-assign': {
            'task': 'tasks.run_ctask_assignment',
            'schedule': 120.0,  # every 2 minutes, matching old threading interval
        },
    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
