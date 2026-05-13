"""
CoreAction Blueprint — COMP-007 (CTCOAMSHM-115, REQ-007, REQ-008, REQ-010, REQ-011)

HTTP routes for the CoreAction feature:
  POST   /core-action                        — execute a core action
  POST   /core-action/<resource_id>/lock     — acquire section lock
  DELETE /core-action/<resource_id>/lock/<lock_id>  — release section lock
  GET    /core-action/stream                 — SSE stream for core_action_change events
"""
import json
import time
import logging
import uuid as _uuid_mod

from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_login import current_user, login_required  # login_required kept for SSE fallback

from models.models import db
from decorators.permission_guard import require_permission
from services.core_action_service import execute_core_action, ValidationError
from services.section_lock_coordinator import (
    acquire_lock, release_lock,
    LockConflictError, LockNotFoundError, LockNotOwnedError,
)
from services.degradation_logger import DegradationSignal

logger = logging.getLogger(__name__)

core_action_bp = Blueprint("core_action", __name__, url_prefix="/core-action")


def _is_valid_uuid(value: str) -> bool:
    try:
        _uuid_mod.UUID(str(value), version=4)
        return True
    except (ValueError, AttributeError):
        return False


@core_action_bp.route("", methods=["POST"])
@require_permission("CORE_ACTION_EXECUTE")
def execute():
    """Execute a core action end-to-end."""
    data = request.get_json(silent=True) or {}
    actor_user_id = str(current_user.id)

    try:
        result = execute_core_action(
            resource_id=data.get("resource_id"),
            section_id=data.get("section_id"),
            payload=data.get("payload"),
            actor_user_id=actor_user_id,
            db_session=db.session,
        )
    except ValidationError as exc:
        return jsonify({"error": "validation_failed", "fields": exc.errors}), 422
    except LockConflictError as exc:
        return jsonify({
            "error": "section_locked",
            "locked_by": exc.locked_by,
            "expires_at": exc.expires_at,
            "message": "The requested section is currently locked by another user.",
        }), 409
    except Exception:
        logger.exception("Unhandled error in core_action execute")
        return jsonify({"error": "server_error", "message": "An unexpected error occurred."}), 500

    if isinstance(result, DegradationSignal):
        return jsonify({"error": "service_degraded", "message": "Service temporarily unavailable."}), 503

    return jsonify(result), 200


@core_action_bp.route("/<resource_id>/lock", methods=["POST"])
@require_permission("CORE_ACTION_EXECUTE")
def acquire_section_lock(resource_id: str):
    """Acquire a section lock on resource_id."""
    if not _is_valid_uuid(resource_id):
        return jsonify({"error": "validation_failed", "fields": {"resource_id": "resource_id must be a valid UUID v4"}}), 422

    data = request.get_json(silent=True) or {}
    section_id = data.get("section_id", "default")
    actor_user_id = str(current_user.id)

    try:
        lock_info = acquire_lock(
            section_id=section_id,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
            db_session=db.session,
        )
        db.session.commit()
        return jsonify({"status": "acquired", **lock_info}), 200
    except LockConflictError as exc:
        return jsonify({
            "error": "section_locked",
            "locked_by": exc.locked_by,
            "expires_at": exc.expires_at,
            "message": "The requested section is currently locked by another user.",
        }), 409
    except Exception:
        logger.exception("Error acquiring lock")
        db.session.rollback()
        return jsonify({"error": "server_error", "message": "An unexpected error occurred."}), 500


@core_action_bp.route("/<resource_id>/lock/<lock_id>", methods=["DELETE"])
@require_permission("CORE_ACTION_EXECUTE")
def release_section_lock(resource_id: str, lock_id: str):
    """Release a section lock."""
    if not _is_valid_uuid(resource_id):
        return jsonify({"error": "validation_failed", "fields": {"resource_id": "resource_id must be a valid UUID v4"}}), 422

    actor_user_id = str(current_user.id)

    try:
        lock_info = release_lock(lock_id=lock_id, actor_user_id=actor_user_id, db_session=db.session)
        db.session.commit()
        return jsonify({"status": "released", "lock_id": lock_info["lock_id"], "section_id": lock_info["section_id"]}), 200
    except LockNotFoundError:
        return jsonify({"error": "not_found", "message": "Lock not found."}), 404
    except LockNotOwnedError:
        return jsonify({"error": "permission_denied", "message": "Lock is not owned by the requesting user."}), 403
    except Exception:
        logger.exception("Error releasing lock")
        db.session.rollback()
        return jsonify({"error": "server_error", "message": "An unexpected error occurred."}), 500


@core_action_bp.route("/stream", methods=["GET"])
@require_permission("CORE_ACTION_EXECUTE")
def sse_stream():
    """SSE stream for core_action_change events.

    Polls the HandoverChange table and delivers events to the connected client.
    Events are scoped to the authenticated user's own actions (IDOR mitigation).
    """
    from models.collaboration import HandoverChange

    actor_user_id = str(current_user.id)

    def generate():
        last_id = 0
        while True:
            try:
                changes = (
                    HandoverChange.query
                    .filter(
                        HandoverChange.change_type == "core_action_change",
                        HandoverChange.id > last_id,
                    )
                    .order_by(HandoverChange.id.asc())
                    .limit(50)
                    .all()
                )
                for change in changes:
                    last_id = change.id
                    try:
                        meta = json.loads(change.new_value) if change.new_value else {}
                    except (ValueError, TypeError):
                        meta = {}
                    # Scope events to this user's own actions
                    if meta.get("actor") != actor_user_id:
                        continue
                    payload = json.dumps({
                        "core_action_id": change.item_id,
                        "event_type": change.section_type,
                        "resource_id": meta.get("resource_id"),
                        "actor": meta.get("actor"),
                        "timestamp": change.created_at.isoformat() if change.created_at else None,
                    })
                    yield f"data: {payload}\n\n"
                yield "event: heartbeat\ndata: {}\n\n"
            except Exception:
                logger.exception("SSE stream error")
                break
            time.sleep(1)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
