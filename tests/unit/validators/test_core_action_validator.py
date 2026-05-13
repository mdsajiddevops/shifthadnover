"""T-028 — Unit tests for CoreAction Input Validator (COMP-009, REQ-008)."""
import pytest
from validators.core_action_validator import validate_core_action_input

VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


class TestResourceId:
    def test_missing_returns_error(self):
        errors = validate_core_action_input({"section_id": "s1", "payload": {}})
        assert errors["resource_id"] == "resource_id is required"

    def test_none_returns_error(self):
        errors = validate_core_action_input({"resource_id": None, "section_id": "s1", "payload": {}})
        assert errors["resource_id"] == "resource_id is required"

    def test_invalid_uuid_returns_error(self):
        errors = validate_core_action_input({"resource_id": "not-a-uuid", "section_id": "s1", "payload": {}})
        assert errors["resource_id"] == "resource_id must be a valid UUID v4"

    def test_valid_uuid_passes(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1", "payload": {}})
        assert "resource_id" not in errors


class TestSectionId:
    def test_missing_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "payload": {}})
        assert errors["section_id"] == "section_id is required"

    def test_empty_string_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "", "payload": {}})
        assert errors["section_id"] == "section_id is required"

    def test_too_long_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "x" * 129, "payload": {}})
        assert errors["section_id"] == "section_id must not exceed 128 characters"

    def test_exactly_128_chars_passes(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "x" * 128, "payload": {}})
        assert "section_id" not in errors

    def test_valid_short_string_passes(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "incidents", "payload": {}})
        assert "section_id" not in errors


class TestPayload:
    def test_missing_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1"})
        assert errors["payload"] == "payload is required"

    def test_none_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1", "payload": None})
        assert errors["payload"] == "payload is required"

    def test_string_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1", "payload": "bad"})
        assert errors["payload"] == "payload must be a JSON object"

    def test_list_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1", "payload": []})
        assert errors["payload"] == "payload must be a JSON object"

    def test_int_returns_error(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1", "payload": 42})
        assert errors["payload"] == "payload must be a JSON object"

    def test_empty_dict_passes(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1", "payload": {}})
        assert "payload" not in errors

    def test_populated_dict_passes(self):
        errors = validate_core_action_input({"resource_id": VALID_UUID, "section_id": "s1", "payload": {"k": "v"}})
        assert "payload" not in errors


class TestAllFieldsValid:
    def test_all_valid_returns_empty_dict(self):
        result = validate_core_action_input({
            "resource_id": VALID_UUID,
            "section_id": "valid-section",
            "payload": {"action": "confirm"},
        })
        assert result == {}
        assert isinstance(result, dict)

    def test_all_invalid_returns_all_errors(self):
        result = validate_core_action_input({
            "resource_id": "bad",
            "section_id": "",
            "payload": "wrong",
        })
        assert "resource_id" in result
        assert "section_id" in result
        assert "payload" in result
        assert len(result) == 3
