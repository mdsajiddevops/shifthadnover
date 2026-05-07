"""
Field-level form validation utilities (COMP-015).

Each validate_*_fields(data) function accepts a dict of submitted form values
and returns a dict mapping field names to actionable error messages.  An empty
dict means all fields are valid (REQ-016).
"""


def _require(errors: dict, data: dict, field: str, label: str) -> bool:
    """Add an error if field is missing, None, or blank.  Returns True if ok."""
    val = data.get(field)
    if val is None:
        errors[field] = f"{label} is required."
        return False
    if isinstance(val, str) and not val.strip():
        errors[field] = f"{label} cannot be empty."
        return False
    return True


def _max_length(errors: dict, data: dict, field: str, label: str, max_len: int) -> None:
    val = data.get(field)
    if val and len(str(val)) > max_len:
        errors[field] = f"{label} must be at most {max_len} characters."


def _in_range(errors: dict, data: dict, field: str, label: str, lo, hi) -> None:
    val = data.get(field)
    if val is None:
        return
    try:
        num = float(val)
    except (TypeError, ValueError):
        errors[field] = f"{label} must be a number."
        return
    if not (lo <= num <= hi):
        errors[field] = f"{label} must be between {lo} and {hi}."


def validate_handover_fields(data: dict) -> dict:
    """Validate handover submission fields.

    Returns a field-name-keyed dict of error messages; empty on success.
    """
    errors: dict = {}
    _require(errors, data, 'shift_date', 'Shift date')
    _require(errors, data, 'shift_type', 'Shift type')
    _require(errors, data, 'submitted_by', 'Submitter name')

    shift_type = data.get('shift_type', '')
    valid_shifts = {'D', 'E', 'LE', 'N', 'G', 'OS', 'OF'}
    if shift_type and shift_type not in valid_shifts:
        errors['shift_type'] = (
            f"Shift type '{shift_type}' is not valid. "
            f"Must be one of: {', '.join(sorted(valid_shifts))}."
        )

    _max_length(errors, data, 'summary', 'Summary', 2000)
    return errors


def validate_incident_fields(data: dict) -> dict:
    """Validate incident creation / update fields."""
    errors: dict = {}
    _require(errors, data, 'title', 'Incident title')
    _require(errors, data, 'status', 'Status')

    valid_statuses = {'Open', 'In Progress', 'Resolved', 'Closed'}
    status = data.get('status', '')
    if status and status not in valid_statuses:
        errors['status'] = (
            f"Status '{status}' is not recognised. "
            f"Must be one of: {', '.join(sorted(valid_statuses))}."
        )

    _max_length(errors, data, 'title', 'Incident title', 255)
    _max_length(errors, data, 'description', 'Description', 5000)
    return errors


def validate_keypoint_fields(data: dict) -> dict:
    """Validate key-point creation / update fields."""
    errors: dict = {}
    _require(errors, data, 'description', 'Description')

    valid_statuses = {'Open', 'In Progress', 'Resolved', 'Closed'}
    status = data.get('status', '')
    if status and status not in valid_statuses:
        errors['status'] = (
            f"Status '{status}' is not recognised. "
            f"Must be one of: {', '.join(sorted(valid_statuses))}."
        )

    _max_length(errors, data, 'description', 'Description', 1000)
    _max_length(errors, data, 'jira_id', 'Jira ID', 50)
    return errors


def validate_user_fields(data: dict) -> dict:
    """Validate user creation / update fields."""
    errors: dict = {}
    _require(errors, data, 'username', 'Username')
    _require(errors, data, 'email', 'Email')

    email = data.get('email', '')
    if email and '@' not in str(email):
        errors['email'] = "Email must be a valid email address."

    valid_roles = {'super_admin', 'account_admin', 'team_admin', 'user'}
    role = data.get('role', '')
    if role and role not in valid_roles:
        errors['role'] = (
            f"Role '{role}' is not valid. "
            f"Must be one of: {', '.join(sorted(valid_roles))}."
        )

    _max_length(errors, data, 'username', 'Username', 80)
    _max_length(errors, data, 'email', 'Email', 120)
    return errors
