"""
Dead-letter queue handler (COMP-011).

on_task_failure() is registered as Celery's on_failure callback.  It writes
a full-context FailedTask record to the database and dispatches an operations
alert.  The two operations are independent: a DB-write failure must not
suppress the alert, and an alert failure must not suppress the DB write.

REQ-006: tasks exhausting all retries are moved here and trigger an ops alert.
"""
import json
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

# Module-level imports so these names can be patched by tests.
# Guarded with try/except so the module is importable in test environments
# where the application DB hasn't been initialised yet.
try:
    from models.failed_task import FailedTask
    from models.models import db
except Exception:
    FailedTask = None  # type: ignore[assignment]
    db = None  # type: ignore[assignment]


def _write_db_record(
    task_id: str,
    task_name: str,
    args,
    kwargs,
    exc: Exception,
    tb_str: str,
    retry_count: int,
    max_retries: int,
) -> None:
    """Persist a FailedTask row.  Raises on DB error (caller handles)."""
    record = FailedTask(
        celery_task_id=task_id,
        task_name=task_name,
        task_args=json.dumps(list(args or [])),
        task_kwargs=json.dumps(dict(kwargs or {})),
        error_message=str(exc)[:1000],
        error_trace=tb_str,
        status='failed',
        retry_count=retry_count,
        max_retries=max_retries,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        alert_dispatched=False,
    )
    db.session.add(record)
    db.session.commit()
    logger.info('DLQ: FailedTask record written (id=%s, task=%s)', record.id, task_name)


def _dispatch_alert(task_id: str, task_name: str, error_message: str) -> None:
    """Send an operations alert.  Does NOT include full trace or raw args.

    Tries the email service first; falls back to a structured log entry so
    an alerting pipeline can pick it up from stdout.
    """
    subject = f'[ShiftOps] Celery task exhausted retries: {task_name}'
    body = (
        f'Task "{task_name}" (ID: {task_id}) has exhausted all retries '
        f'and been moved to the dead-letter queue.\n\n'
        f'Error: {error_message}\n\n'
        'Check the failed_tasks table for full details.'
    )
    try:
        from services.email_service import send_ops_alert
        send_ops_alert(subject=subject, body=body)
        logger.info('DLQ: ops alert dispatched via email for task %s', task_id)
        return
    except ImportError:
        pass  # Function not yet wired up — fall through to log alert.
    except Exception as alert_exc:
        logger.error(
            'DLQ: email alert failed for task %s: %s — falling back to log alert',
            task_id,
            alert_exc,
        )

    # Fallback: emit a structured CRITICAL log entry that monitoring can capture.
    logger.critical(
        'OPS_ALERT task_id=%s task_name=%s error=%s',
        task_id,
        task_name,
        error_message,
    )


def on_task_failure(
    task_id: str,
    task_name: str,
    args,
    kwargs,
    exc: Exception,
    retry_count: int,
    max_retries: int,
    einfo=None,
) -> None:
    """
    Callback invoked when a task exhausts all retries.

    Guarantees: DB write failure does not suppress alert; alert failure does
    not suppress DB write.  Both are attempted unconditionally.
    """
    tb_str = ''
    if einfo is not None:
        try:
            tb_str = str(einfo.traceback)
        except Exception:
            tb_str = traceback.format_exc()
    else:
        tb_str = ''.join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )

    db_ok = False
    try:
        _write_db_record(
            task_id=task_id,
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            exc=exc,
            tb_str=tb_str,
            retry_count=retry_count,
            max_retries=max_retries,
        )
        db_ok = True
    except Exception as db_exc:
        logger.error('DLQ: DB write failed for task %s: %s', task_id, db_exc)

    try:
        _dispatch_alert(task_id, task_name, str(exc)[:500])
    except Exception as alert_exc:
        logger.error('DLQ: alert dispatch raised for task %s: %s', task_id, alert_exc)

    if not db_ok:
        logger.critical(
            'DLQ: BOTH DB write AND alert dispatch failed for task %s. '
            'Manual intervention required. Error: %s',
            task_id,
            exc,
        )
