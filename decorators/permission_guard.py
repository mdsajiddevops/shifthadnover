"""
Permission guard decorator for CoreAction endpoints.

Usage:
    @require_permission("CORE_ACTION_EXECUTE")
    def my_route():
        ...
"""
import functools
from flask import jsonify, request
from flask_login import current_user

_PERMISSION_ROLES: dict[str, set[str]] = {
    "CORE_ACTION_EXECUTE": {"user", "team_admin", "account_admin", "super_admin"},
}


def require_permission(permission: str):
    """Return a decorator that enforces *permission* before the wrapped route runs.

    Returns 401 JSON if no authenticated session exists.
    Returns 403 JSON if the session exists but the user's role does not grant *permission*.
    Writes a permission_denied audit entry on every 403 (REQ-010).
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                return jsonify({
                    "error": "authentication_required",
                    "redirect": "/login",
                }), 401

            allowed_roles = _PERMISSION_ROLES.get(permission, set())
            if not allowed_roles or current_user.role not in allowed_roles:
                _write_denial_audit(permission)
                return jsonify({
                    "error": "permission_denied",
                    "message": "You do not have permission to perform this action.",
                    "required_permission": permission,
                }), 403

            return f(*args, **kwargs)
        return wrapper
    return decorator


def _write_denial_audit(permission: str) -> None:
    """Best-effort permission-denied audit write (REQ-010). Never raises."""
    try:
        from models.models import db
        from services.audit_log_writer import write_permission_denied
        data = request.get_json(silent=True) or {}
        write_permission_denied(
            actor_user_id=str(current_user.id),
            resource_id=data.get("resource_id"),
            denied_operation=permission,
            details={"role": getattr(current_user, "role", None)},
            db_session=db.session,
        )
        db.session.commit()
    except Exception:
        pass  # audit failure must not block the denial response
