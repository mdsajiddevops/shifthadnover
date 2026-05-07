"""
Scheduler management routes (COMP-013).

Exposes the Celery-backed scheduler control API used by the operations UI.
All route paths, HTTP methods, and success response shapes are frozen — do
not change them without updating API consumers.

Endpoints:
  GET  /scheduler/status       → {status, workers_active, scheduled_jobs, broker_reachable}
  POST /scheduler/start        → {status, message}
  POST /scheduler/stop         → {status, message}
  POST /scheduler/force-check  → {status, task_id, message}

REQ-003, REQ-004, REQ-013, REQ-017.
"""
import logging

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from services.ctask_scheduler import (
    force_scheduler_check,
    get_scheduler_status,
    start_ctask_scheduler,
    stop_ctask_scheduler,
)
from utils.rbac_errors import resolve_rbac_error

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/scheduler')

_SCHEDULER_MIN_ROLE = 'team_admin'
_ROLE_RANK = {'user': 0, 'team_admin': 1, 'account_admin': 2, 'super_admin': 3}


def _has_role(user_role: str, required: str) -> bool:
    return _ROLE_RANK.get(user_role, -1) >= _ROLE_RANK.get(required, 99)


# ---------------------------------------------------------------------------
# Blueprint-level error handlers (safety net — primary path uses explicit returns)
# ---------------------------------------------------------------------------

@scheduler_bp.errorhandler(400)
def bad_request(e):
    return jsonify({'error': str(e)}), 400


@scheduler_bp.errorhandler(403)
def forbidden(e):
    return jsonify({'error': str(e)}), 403


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@scheduler_bp.route('/status', methods=['GET'])
@login_required
def status():
    """Return Celery worker availability as scheduler status (REQ-013: ≤5 s)."""
    result = get_scheduler_status()
    http_status = 503 if result.get('status') == 'degraded' or not result.get('broker_reachable', True) else 200
    return jsonify(result), http_status


@scheduler_bp.route('/start', methods=['POST'])
@login_required
def start():
    """Signal scheduler start (Celery Beat is persistent; this is a no-op by design)."""
    if not _has_role(current_user.role, _SCHEDULER_MIN_ROLE):
        msg = resolve_rbac_error(current_user.role, _SCHEDULER_MIN_ROLE, 'start_scheduler')
        return jsonify({'error': msg}), 403

    result = start_ctask_scheduler()
    return jsonify(result or {'status': 'ok', 'message': 'Scheduler start signal sent.'})


@scheduler_bp.route('/stop', methods=['POST'])
@login_required
def stop():
    """Signal scheduler stop (no-op; stop the celery-beat container to pause scheduling)."""
    if not _has_role(current_user.role, _SCHEDULER_MIN_ROLE):
        msg = resolve_rbac_error(current_user.role, _SCHEDULER_MIN_ROLE, 'stop_scheduler')
        return jsonify({'error': msg}), 403

    result = stop_ctask_scheduler()
    return jsonify(result or {'status': 'ok', 'message': 'Scheduler stop signal sent.'})


@scheduler_bp.route('/force-check', methods=['POST'])
@login_required
def force_check():
    """Dispatch an immediate CTask assignment task via Celery."""
    if not _has_role(current_user.role, _SCHEDULER_MIN_ROLE):
        msg = resolve_rbac_error(current_user.role, _SCHEDULER_MIN_ROLE, 'force_scheduler_check')
        return jsonify({'error': msg}), 403

    result = force_scheduler_check()
    if result.get('status') == 'error' or not result.get('broker_reachable', True):
        return jsonify({'status': 'error', 'message': result.get('broker_error', 'Broker unavailable')}), 503

    return jsonify({
        'status': 'ok',
        'task_id': result.get('task_id'),
        'message': result.get('message', 'CTask assignment task dispatched.'),
    })
