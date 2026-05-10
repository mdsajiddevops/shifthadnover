"""
Unit tests for utils/validators.py (T-035 / COMP-015).

Verifies:
- Empty field → named error message.
- None value → named error message.
- Out-of-range / invalid value → descriptive error.
- Fully valid input → empty dict.
"""
import unittest
from utils.validators import (
    validate_handover_fields,
    validate_incident_fields,
    validate_keypoint_fields,
    validate_user_fields,
)


class TestHandoverFieldValidation(unittest.TestCase):
    def test_empty_shift_date_returns_error(self):
        errors = validate_handover_fields({'shift_date': '', 'shift_type': 'Evening', 'submitted_by': 'Alice'})
        self.assertIn('shift_date', errors)

    def test_none_shift_type_returns_error(self):
        errors = validate_handover_fields({'shift_date': '2026-01-01', 'shift_type': None, 'submitted_by': 'Alice'})
        self.assertIn('shift_type', errors)

    def test_invalid_shift_type_returns_named_error(self):
        errors = validate_handover_fields({'shift_date': '2026-01-01', 'shift_type': 'X', 'submitted_by': 'Alice'})
        self.assertIn('shift_type', errors)
        self.assertIn('X', errors['shift_type'])

    def test_valid_input_returns_empty_dict(self):
        errors = validate_handover_fields({'shift_date': '2026-01-01', 'shift_type': 'Evening', 'submitted_by': 'Alice'})
        self.assertEqual(errors, {})

    def test_all_valid_shift_types_pass(self):
        for shift in ('Morning', 'Evening', 'Late Evening', 'Night', 'General', 'OnShore', 'OffShore'):
            errors = validate_handover_fields({'shift_date': '2026-01-01', 'shift_type': shift, 'submitted_by': 'Alice'})
            self.assertNotIn('shift_type', errors, f"Expected '{shift}' to be valid")


class TestIncidentFieldValidation(unittest.TestCase):
    def test_empty_title_returns_error(self):
        errors = validate_incident_fields({'title': '', 'status': 'Open'})
        self.assertIn('title', errors)

    def test_none_status_returns_error(self):
        errors = validate_incident_fields({'title': 'INC-001', 'status': None})
        self.assertIn('status', errors)

    def test_invalid_status_returns_named_error(self):
        errors = validate_incident_fields({'title': 'INC-001', 'status': 'Maybe'})
        self.assertIn('status', errors)
        self.assertIn('Maybe', errors['status'])

    def test_valid_input_returns_empty_dict(self):
        errors = validate_incident_fields({'title': 'INC-001', 'status': 'Open'})
        self.assertEqual(errors, {})

    def test_title_too_long_returns_error(self):
        errors = validate_incident_fields({'title': 'x' * 300, 'status': 'Open'})
        self.assertIn('title', errors)


class TestKeyPointFieldValidation(unittest.TestCase):
    def test_empty_description_returns_error(self):
        errors = validate_keypoint_fields({'description': ''})
        self.assertIn('description', errors)

    def test_valid_input_returns_empty_dict(self):
        errors = validate_keypoint_fields({'description': 'Some key point', 'status': 'Open'})
        self.assertEqual(errors, {})

    def test_invalid_status_returns_named_error(self):
        errors = validate_keypoint_fields({'description': 'KP', 'status': 'Pending'})
        self.assertIn('status', errors)


class TestUserFieldValidation(unittest.TestCase):
    def test_empty_username_returns_error(self):
        errors = validate_user_fields({'username': '', 'email': 'a@b.com'})
        self.assertIn('username', errors)

    def test_invalid_email_returns_error(self):
        errors = validate_user_fields({'username': 'alice', 'email': 'not-an-email'})
        self.assertIn('email', errors)

    def test_invalid_role_returns_named_error(self):
        errors = validate_user_fields({'username': 'alice', 'email': 'a@b.com', 'role': 'god'})
        self.assertIn('role', errors)
        self.assertIn('god', errors['role'])

    def test_valid_input_returns_empty_dict(self):
        errors = validate_user_fields({'username': 'alice', 'email': 'alice@example.com', 'role': 'user'})
        self.assertEqual(errors, {})


if __name__ == '__main__':
    unittest.main()
