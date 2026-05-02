from functools import wraps
from flask import abort
from flask_login import current_user


def require_role(*roles):
    """Decorator that aborts with 403 if the logged-in user's role is not in *roles*.

    Usage:
        @bp.route('/admin/users')
        @login_required
        @require_role('super_admin', 'account_admin')
        def admin_users():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_any_admin(f):
    """Shorthand: allow super_admin, account_admin, or team_admin."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in (
            'super_admin', 'account_admin', 'team_admin'
        ):
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def require_super_admin(f):
    """Shorthand: allow super_admin only."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super_admin':
            abort(403)
        return f(*args, **kwargs)
    return wrapper
