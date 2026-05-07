"""
Unit tests for utils/validation.py (T-021 / COMP-010).

Verifies all boundary conditions for the pure validation functions,
including multi-error non-short-circuit behaviour of validate_form
and the correct shape of format_error_response.
"""
import unittest

from utils.validation import (
    ValidationError,
    format_error_response,
    validate_form,
    validate_max_length,
    validate_not_null,
    validate_range,
    validate_required,
)


class TestValidateRequired(unittest.TestCase):
    def test_none_returns_error(self):
        err = validate_required(None, 'name')
        self.assertIsNotNone(err)
        self.assertEqual(err['field'], 'name')

    def test_empty_string_returns_error(self):
        err = validate_required('', 'name')
        self.assertIsNotNone(err)

    def test_whitespace_only_returns_error(self):
        err = validate_required('   ', 'name')
        self.assertIsNotNone(err)

    def test_valid_string_returns_none(self):
        self.assertIsNone(validate_required('hello', 'name'))

    def test_zero_is_valid(self):
        self.assertIsNone(validate_required(0, 'count'))

    def test_error_includes_field_name(self):
        err = validate_required(None, 'email')
        self.assertIn('email', err['message'])


class TestValidateNotNull(unittest.TestCase):
    def test_none_returns_error(self):
        err = validate_not_null(None, 'field')
        self.assertIsNotNone(err)
        self.assertEqual(err['field'], 'field')

    def test_empty_string_returns_none(self):
        self.assertIsNone(validate_not_null('', 'field'))

    def test_zero_returns_none(self):
        self.assertIsNone(validate_not_null(0, 'field'))

    def test_false_returns_none(self):
        self.assertIsNone(validate_not_null(False, 'field'))

    def test_valid_value_returns_none(self):
        self.assertIsNone(validate_not_null('hello', 'field'))


class TestValidateRange(unittest.TestCase):
    def test_value_at_min_boundary_passes(self):
        self.assertIsNone(validate_range(0, 'age', 0, 120))

    def test_value_at_max_boundary_passes(self):
        self.assertIsNone(validate_range(120, 'age', 0, 120))

    def test_value_strictly_inside_passes(self):
        self.assertIsNone(validate_range(60, 'age', 0, 120))

    def test_value_below_min_returns_error(self):
        err = validate_range(-1, 'age', 0, 120)
        self.assertIsNotNone(err)
        self.assertEqual(err['field'], 'age')

    def test_value_above_max_returns_error(self):
        err = validate_range(121, 'age', 0, 120)
        self.assertIsNotNone(err)

    def test_non_numeric_returns_error(self):
        err = validate_range('abc', 'count', 1, 10)
        self.assertIsNotNone(err)

    def test_error_message_contains_bounds_and_value(self):
        err = validate_range(200, 'age', 0, 120)
        self.assertIn('0', err['message'])
        self.assertIn('120', err['message'])

    def test_float_value_passes(self):
        self.assertIsNone(validate_range(1.5, 'ratio', 0.0, 2.0))


class TestValidateMaxLength(unittest.TestCase):
    def test_exactly_max_length_passes(self):
        self.assertIsNone(validate_max_length('a' * 10, 'title', 10))

    def test_one_over_max_length_returns_error(self):
        err = validate_max_length('a' * 11, 'title', 10)
        self.assertIsNotNone(err)
        self.assertEqual(err['field'], 'title')

    def test_empty_string_passes(self):
        self.assertIsNone(validate_max_length('', 'title', 10))

    def test_none_passes(self):
        self.assertIsNone(validate_max_length(None, 'title', 10))

    def test_error_message_contains_max_length(self):
        err = validate_max_length('a' * 300, 'title', 255)
        self.assertIn('255', err['message'])


class TestValidateForm(unittest.TestCase):
    """validate_form must not short-circuit — all rules run regardless of failures."""

    def test_all_valid_returns_empty_list(self):
        errors = validate_form([
            (validate_required, 'hello', 'name'),
            (validate_required, 'world', 'title'),
        ])
        self.assertEqual(errors, [])

    def test_single_failure_returns_one_error(self):
        errors = validate_form([
            (validate_required, '', 'name'),
        ])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['field'], 'name')

    def test_multiple_failures_all_collected(self):
        errors = validate_form([
            (validate_required, '', 'name'),
            (validate_required, None, 'email'),
            (validate_required, '  ', 'title'),
        ])
        self.assertEqual(len(errors), 3)
        fields = [e['field'] for e in errors]
        self.assertIn('name', fields)
        self.assertIn('email', fields)
        self.assertIn('title', fields)

    def test_mixed_valid_and_invalid(self):
        errors = validate_form([
            (validate_required, 'valid', 'name'),
            (validate_required, '', 'email'),
        ])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['field'], 'email')

    def test_empty_rules_returns_empty_list(self):
        self.assertEqual(validate_form([]), [])

    def test_second_rule_evaluated_after_first_fails(self):
        """Confirm no short-circuit: second rule must run even when first fails."""
        calls = []

        def tracking_validator(value, field_name):
            calls.append(field_name)
            if not value:
                return ValidationError(field=field_name, message=f'{field_name} required')
            return None

        validate_form([
            (tracking_validator, '', 'first'),
            (tracking_validator, '', 'second'),
        ])
        self.assertIn('first', calls)
        self.assertIn('second', calls)


class TestFormatErrorResponse(unittest.TestCase):
    def test_empty_list_returns_empty_errors(self):
        result = format_error_response([])
        self.assertEqual(result, {'errors': []})

    def test_single_error_correct_structure(self):
        errors = [ValidationError(field='name', message='Name is required.')]
        result = format_error_response(errors)
        self.assertIn('errors', result)
        self.assertEqual(len(result['errors']), 1)
        self.assertEqual(result['errors'][0]['field'], 'name')
        self.assertEqual(result['errors'][0]['message'], 'Name is required.')

    def test_multiple_errors_all_present(self):
        errors = [
            ValidationError(field='name', message='required'),
            ValidationError(field='email', message='required'),
        ]
        result = format_error_response(errors)
        self.assertEqual(len(result['errors']), 2)

    def test_no_extra_top_level_keys(self):
        result = format_error_response([])
        self.assertEqual(set(result.keys()), {'errors'})


if __name__ == '__main__':
    unittest.main()
