"""
Worker status instrumentation adapter (COMP-011).

Safely queries Celery worker status and returns a structured result.
Never raises — all exceptions are caught and converted to available=False.
"""
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

# Lazy module-level reference — resolved at first call so this module can be
# imported without a running broker (e.g. during unit tests).
_celery = None


def _get_celery():
    global _celery
    if _celery is None:
        from celery_app import celery as _c
        _celery = _c
    return _celery


class WorkerStatusResult(TypedDict):
    available: bool
    worker_count: int
    active_tasks: int
    error: str | None


def get_worker_status(timeout_seconds: float = 1.0) -> WorkerStatusResult:
    """Return Celery worker status without raising on any failure.

    On success: available=True with populated counts.
    On any exception: available=False, counts=0, error=short reason.
    The timeout ensures a broker outage adds at most timeout_seconds latency
    to the calling web request (REQ-012).
    """
    try:
        celery = _get_celery()
        inspect = celery.control.inspect(timeout=timeout_seconds)
        active = inspect.active()
        if active is None:
            raise RuntimeError("inspect.active() returned None — no workers reachable")
        worker_count = len(active)
        active_tasks = sum(len(tasks) for tasks in active.values())
        return WorkerStatusResult(
            available=True,
            worker_count=worker_count,
            active_tasks=active_tasks,
            error=None,
        )
    except Exception as e:
        logger.warning("WORKER_STATUS_CHECK_FAILED: %s", e)
        return WorkerStatusResult(
            available=False,
            worker_count=0,
            active_tasks=0,
            error=f"Worker status unavailable: {e}",
        )
