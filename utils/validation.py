"""
Input validation utility (COMP-010).

Pure functions — no Flask context, no side effects, no external dependencies.
Route handlers call validate_form() before any db.session operation so that
no partial records are persisted on invalid input (REQ-008).
"""
from typing import Any, Callable, TypedDict


class ValidationError(TypedDict):
    field: str
    message: str


def validate_required(value: Any, field_name: str) -> ValidationError | None:
    """Error if value is None, empty string, or whitespace-only."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ValidationError(field=field_name, message=f"'{field_name}' is required.")
    return None


def validate_not_null(value: Any, field_name: str) -> ValidationError | None:
    """Error only if value is None (empty string and 0 are permitted)."""
    if value is None:
        return ValidationError(field=field_name, message=f"'{field_name}' must not be null.")
    return None


def validate_range(
    value: int | float,
    field_name: str,
    min_val: int | float,
    max_val: int | float,
) -> ValidationError | None:
    """Error if numeric value is outside [min_val, max_val] (inclusive)."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return ValidationError(
            field=field_name,
            message=f"'{field_name}' must be a number between {min_val} and {max_val}.",
        )
    if num < min_val or num > max_val:
        return ValidationError(
            field=field_name,
            message=(
                f"'{field_name}' must be between {min_val} and {max_val}. "
                f"Received: {value}."
            ),
        )
    return None


def validate_max_length(value: Any, field_name: str, max_length: int) -> ValidationError | None:
    """Error if len(str(value)) > max_length."""
    if value is None:
        return None
    if len(str(value)) > max_length:
        return ValidationError(
            field=field_name,
            message=f"'{field_name}' must not exceed {max_length} characters.",
        )
    return None


def validate_form(rules: list[tuple[Callable, ...]]) -> list[ValidationError]:
    """Run all validator rules and collect every error (no short-circuit).

    Each element of rules is a tuple: (validator_fn, *args).
    The validator is called as validator_fn(*args).
    Returns a list of all ValidationErrors (empty list = all valid).
    """
    errors: list[ValidationError] = []
    for rule in rules:
        fn, *args = rule
        result = fn(*args)
        if result is not None:
            errors.append(result)
    return errors


def format_error_response(errors: list[ValidationError]) -> dict:
    """Wrap errors list in the standard response envelope."""
    return {"errors": errors}
