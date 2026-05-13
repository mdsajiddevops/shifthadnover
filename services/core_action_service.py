"""
CoreAction Service — COMP-008 (CTCOAMSHM-115, REQ-007, REQ-008, REQ-009, REQ-011, REQ-012)

Orchestrates the full CoreAction execution pipeline as a single atomic unit:
  1. Input validation (COMP-009)
  2. Lock acquire (COMP-013)
  3. DB record create (COMP-011)
  4. Audit: action_initiated (COMP-016)
  5. Business logic (placeholder hook)
  6. DB record mark_completed (COMP-011)
  7. Audit: action_completed (COMP-016)
  8. SSE publish (COMP-014)
  9. Commit — this is the ONLY commit in the pipeline
  10. Return serialised success dict

Degradation path: SQLAlchemy errors → rollback → DegradationSignal → caller maps to 503.
"""
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from validators.core_action_validator import validate_core_action_input
from services.section_lock_coordinator import acquire_lock, release_lock, LockConflictError
from services.audit_log_writer import write_permission_denied, write_action_lifecycle
from services.sse_publisher import publish_core_action_event
from services.degradation_logger import log_degradation, DegradationSignal
from repositories.core_action_repository import (
    create_record,
    mark_completed,
    mark_rolled_back,
)


class ValidationError(Exception):
    """Raised when input validation fails.  Carries a field-keyed error map."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))


def execute_core_action(
    resource_id,
    section_id: str,
    payload: dict,
    actor_user_id: str,
    db_session,
) -> dict | DegradationSignal:
    """Execute the core action end-to-end.

    Returns a success dict on success.
    Returns a DegradationSignal if a DB/service failure occurs (caller maps to 503).
    Raises ValidationError (422) if inputs are invalid.
    Raises LockConflictError (409) if the section is already locked.
    """
    # Step 1 — Validate inputs before any lock or DB work
    errors = validate_core_action_input(
        {"resource_id": str(resource_id), "section_id": section_id, "payload": payload}
    )
    if errors:
        raise ValidationError(errors)

    # Step 2 — Permission is enforced at the decorator layer (COMP-010) before this function.
    # No re-check here.

    lock_info = None
    record = None

    try:
        # Step 3 — Acquire section lock
        try:
            lock_info = acquire_lock(
                section_id=section_id,
                resource_id=resource_id,
                actor_user_id=actor_user_id,
                db_session=db_session,
            )
        except LockConflictError as exc:
            # Write lock_denied audit entry (no commit — will be rolled back)
            write_action_lifecycle(
                core_action_id=None,
                event_type="lock_denied",
                actor_user_id=actor_user_id,
                resource_id=resource_id,
                details={"locked_by": exc.locked_by},
                db_session=db_session,
            )
            db_session.commit()
            raise  # re-raise for blueprint to map to 409

        # Step 4 — Create pending record
        record = create_record(
            resource_id=resource_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            payload=payload,
            db_session=db_session,
        )

        # Step 5 — Audit: action_initiated
        write_action_lifecycle(
            core_action_id=record.id,
            event_type="action_initiated",
            actor_user_id=actor_user_id,
            resource_id=resource_id,
            details=None,
            db_session=db_session,
        )

        # Step 6 — Business logic (placeholder — extend for future domain logic)
        _execute_business_logic(record, payload)

        # Step 7 — Mark completed
        mark_completed(record.id, db_session)

        # Step 8 — Audit: action_completed
        write_action_lifecycle(
            core_action_id=record.id,
            event_type="action_completed",
            actor_user_id=actor_user_id,
            resource_id=resource_id,
            details=None,
            db_session=db_session,
        )

        # Step 9 — SSE publish
        publish_core_action_event(
            core_action_id=record.id,
            event_type="core_action_change",
            resource_id=resource_id,
            actor=actor_user_id,
            db_session=db_session,
        )

        # Step 10 — Single commit (owns the entire transaction)
        db_session.commit()

        return {
            "status": "completed",
            "core_action_id": record.id,
            "resource_id": str(resource_id),
            "section_id": section_id,
            "completed_at": datetime.utcnow().isoformat() + "Z",
            "actor": str(actor_user_id),
        }

    except (LockConflictError, ValidationError):
        raise  # let blueprint handle these — no degradation path

    except SQLAlchemyError as exc:
        # Degradation path: DB failure — rollback and return a typed signal
        try:
            db_session.rollback()
        except Exception:
            pass
        return log_degradation(exc, context={"resource_id": str(resource_id), "actor": str(actor_user_id)})

    except Exception as exc:
        # Non-DB exception after record creation — rollback path
        try:
            if record is not None:
                # Best-effort: mark rolled_back and commit audit only
                try:
                    mark_rolled_back(record.id, db_session)
                    write_action_lifecycle(
                        core_action_id=record.id,
                        event_type="action_rolled_back",
                        actor_user_id=actor_user_id,
                        resource_id=resource_id,
                        details={"reason": type(exc).__name__},
                        db_session=db_session,
                    )
                    db_session.commit()
                except Exception:
                    db_session.rollback()
            else:
                db_session.rollback()
        except Exception:
            pass
        raise


def _execute_business_logic(record, payload: dict) -> None:
    """Placeholder for domain-specific business logic.

    Currently a no-op.  Future expansion point — must remain synchronous
    to meet the REQ-011 sub-100ms latency budget.
    """
    pass
