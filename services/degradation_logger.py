"""
Degradation Logger — COMP-015

Captures dependency failures, emits a structured ERROR-level log entry, and
returns a typed DegradationSignal so callers can branch without catching raw exceptions.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Known exception categories — mapped from exception type name to a stable string key.
_CATEGORY_MAP: dict[str, str] = {
    "TimeoutError": "db_timeout",
    "OperationalError": "db_timeout",
    "InterfaceError": "db_timeout",
    "DisconnectionError": "db_timeout",
    "Timeout": "service_unavailable",
    "ConnectionError": "service_unavailable",
    "ConnectTimeout": "service_unavailable",
    "ReadTimeout": "service_unavailable",
}


@dataclass
class DegradationSignal:
    """Typed return value from log_degradation."""
    degraded: bool
    category: str
    detail: str
    original_exception_type: str


def log_degradation(exc: Exception, context: dict) -> DegradationSignal:
    """Log *exc* as a structured ERROR entry and return a DegradationSignal.

    Never raises. Any failure inside this function is silently swallowed so the
    logger itself cannot become a secondary failure point.

    Args:
        exc: The exception that triggered degradation.
        context: Caller-supplied dict included in the log payload (must be JSON-serialisable).

    Returns:
        DegradationSignal with degraded=True on all failure paths.
    """
    exc_type = type(exc).__name__
    category = _CATEGORY_MAP.get(exc_type, "unknown_error")
    detail = str(exc) if str(exc) else exc_type

    try:
        logger.error(
            "Degradation detected",
            extra={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "exception_type": exc_type,
                "message": detail,
                "category": category,
                "context": context,
            },
        )
    except Exception:  # pragma: no cover
        pass  # Logger must never raise

    return DegradationSignal(
        degraded=True,
        category=category,
        detail=detail,
        original_exception_type=exc_type,
    )


def no_degradation() -> DegradationSignal:
    """Return a non-degraded signal (happy path)."""
    return DegradationSignal(
        degraded=False,
        category="",
        detail="",
        original_exception_type="",
    )
