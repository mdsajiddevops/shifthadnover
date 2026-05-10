"""
Worker status instrumentation adapter (COMP-011).

Safely queries Celery worker status and returns a structured result.
Never raises — all exceptions are caught and converted to available=False.
"""
import logging
import time
from typing import TypedDict

logger = logging.getLogger(__name__)

_celery = None
_cache_result: "WorkerStatusResult | None" = None
_cache_ts: float = 0.0
_CACHE_TTL = 30.0  # seconds — avoids 1s broker timeout on every page load


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

    Caches the result for _CACHE_TTL seconds so broker timeouts (when workers
    are unreachable) only block once per TTL window rather than on every request.
    """
    global _cache_result, _cache_ts
    if _cache_result is not None and (time.monotonic() - _cache_ts) < _CACHE_TTL:
        return _cache_result
    try:
        celery = _get_celery()
        inspect = celery.control.inspect(timeout=timeout_seconds)
        active = inspect.active()
        if active is None:
            raise RuntimeError("inspect.active() returned None — no workers reachable")
        worker_count = len(active)
        active_tasks = sum(len(tasks) for tasks in active.values())
        result = WorkerStatusResult(
            available=True,
            worker_count=worker_count,
            active_tasks=active_tasks,
            error=None,
        )
    except Exception as e:
        logger.warning("WORKER_STATUS_CHECK_FAILED: %s", e)
        result = WorkerStatusResult(
            available=False,
            worker_count=0,
            active_tasks=0,
            error=f"Worker status unavailable: {e}",
        )
    _cache_result = result
    _cache_ts = time.monotonic()
    return result
