"""
RBAC error message resolver (COMP-016).

resolve_rbac_error(user_role, required_role, action) returns a specific,
role-identifying message for every supported combination so callers never
emit generic 403 responses (REQ-017).
"""

# Canonical role display names used in error messages.
_ROLE_LABELS = {
    'super_admin': 'Super Admin',
    'account_admin': 'Account Admin',
    'team_admin': 'Team Admin',
    'user': 'User',
    None: 'Unauthenticated',
}

# Actions that require a specific minimum role.
_ACTION_REQUIREMENTS = {
    # Team management
    'manage_team': 'team_admin',
    'create_team': 'account_admin',
    'delete_team': 'account_admin',
    # User management
    'manage_users': 'account_admin',
    'create_user': 'account_admin',
    'delete_user': 'account_admin',
    'reset_password': 'account_admin',
    # Handover approval
    'approve_handover': 'team_admin',
    'reject_handover': 'team_admin',
    # Admin panel
    'access_admin_panel': 'account_admin',
    'view_audit_logs': 'account_admin',
    # Scheduler management
    'start_scheduler': 'team_admin',
    'stop_scheduler': 'team_admin',
    'force_scheduler_check': 'team_admin',
    # System configuration
    'manage_system_config': 'super_admin',
    'rotate_secrets': 'super_admin',
}

# Role hierarchy: higher index = more privilege.
_ROLE_ORDER = ['user', 'team_admin', 'account_admin', 'super_admin']


def resolve_rbac_error(user_role: str | None, required_role: str, action: str) -> str:
    """Return a specific, role-identifying error message.

    Args:
        user_role:     The role the authenticated user actually holds (or None).
        required_role: The minimum role needed for the action.
        action:        Human-readable action label (e.g. 'approve_handover').

    Returns:
        A non-generic string describing the specific missing privilege.
    """
    user_label = _ROLE_LABELS.get(user_role, f"role '{user_role}'")
    required_label = _ROLE_LABELS.get(required_role, f"role '{required_role}'")

    if user_role is None:
        return (
            f"You must be logged in to perform '{action}'. "
            f"This action requires the {required_label} role."
        )

    return (
        f"Access denied: '{action}' requires the {required_label} role, "
        f"but your account has the {user_label} role. "
        f"Contact your Account Admin to request elevated access."
    )


def check_role(user_role: str | None, action: str) -> str | None:
    """Return an error message if user_role cannot perform action, else None.

    Looks up the required role from the built-in _ACTION_REQUIREMENTS table.
    Returns None if the action is permitted or unknown (fail-open for unknown
    actions — route-level guards are responsible for explicit checks).
    """
    required = _ACTION_REQUIREMENTS.get(action)
    if required is None:
        return None  # Unknown action — let caller decide.

    if user_role is None:
        return resolve_rbac_error(None, required, action)

    try:
        user_idx = _ROLE_ORDER.index(user_role)
        required_idx = _ROLE_ORDER.index(required)
    except ValueError:
        # Unrecognised role string — treat as least-privilege.
        return resolve_rbac_error(user_role, required, action)

    if user_idx < required_idx:
        return resolve_rbac_error(user_role, required, action)

    return None  # Permitted.
