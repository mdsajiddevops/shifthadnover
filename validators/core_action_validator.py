"""
CoreAction Input Validator — COMP-009 (CTCOAMSHM-115, REQ-008)

Stateless per-field validation for POST /core-action payloads.
No Flask or SQLAlchemy imports — independently unit-testable.
"""
import uuid


def validate_core_action_input(data: dict) -> dict:
    """Validate *data* and return a field-keyed error map.

    Returns an empty dict on success.  On failure returns
    ``{field_name: human_readable_message}`` for every failing field.
    All fields are checked before returning (no early exit).
    """
    errors: dict[str, str] = {}

    # --- resource_id ---
    resource_id = data.get("resource_id")
    if resource_id is None:
        errors["resource_id"] = "resource_id is required"
    else:
        try:
            uuid.UUID(str(resource_id), version=4)
        except (ValueError, AttributeError):
            errors["resource_id"] = "resource_id must be a valid UUID v4"

    # --- section_id ---
    section_id = data.get("section_id")
    if section_id is None or section_id == "":
        errors["section_id"] = "section_id is required"
    elif not isinstance(section_id, str):
        errors["section_id"] = "section_id must be a string"
    elif len(section_id) > 128:
        errors["section_id"] = "section_id must not exceed 128 characters"

    # --- payload ---
    payload = data.get("payload")
    if payload is None:
        errors["payload"] = "payload is required"
    elif not isinstance(payload, dict):
        errors["payload"] = "payload must be a JSON object"

    return errors
