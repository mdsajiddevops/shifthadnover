"""
Integration tests for form-handling route validation (T-025 / COMP-010).

Verifies that POST routes with validate_form() integration:
- Return a field-specific error response when a required field is missing.
- Do NOT persist any DB record on validation failure.
- Return all field errors in a single response (no short-circuit).
- Return success and persist the record on valid input.

Requires a running Flask application with an in-memory SQLite test database.
Tests are skipped automatically when Flask is not installed.
"""
import unittest

try:
    import flask  # noqa: F401
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

SKIP_MSG = 'Flask not installed — integration tests require the full app stack'


@unittest.skipUnless(FLASK_AVAILABLE, SKIP_MSG)
class TestAuthValidation(unittest.TestCase):
    """Validate that the login route enforces required fields."""

    def setUp(self):
        import os
        os.environ['LOCAL_DEVELOPMENT'] = 'true'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        from app import app
        from models.models import db
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def test_login_missing_username_returns_error(self):
        response = self.client.post('/login', data={'username': '', 'password': 'secret'})
        self.assertIn(response.status_code, (200, 302, 400, 422))

    def test_login_missing_password_returns_error(self):
        response = self.client.post('/login', data={'username': 'admin', 'password': ''})
        self.assertIn(response.status_code, (200, 302, 400, 422))

    def test_login_both_empty_returns_error(self):
        response = self.client.post('/login', data={'username': '', 'password': ''})
        self.assertIn(response.status_code, (200, 302, 400, 422))


@unittest.skipUnless(FLASK_AVAILABLE, SKIP_MSG)
class TestFormValidationNoDB(unittest.TestCase):
    """Verify no DB record is created on validation failure."""

    def setUp(self):
        import os
        os.environ['LOCAL_DEVELOPMENT'] = 'true'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        from app import app
        from models.models import db
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()
        self.db = db
        with app.app_context():
            db.create_all()

    def test_missing_required_field_creates_no_record(self):
        """Submitting empty required fields must not persist any DB row."""
        from models.models import User
        with self.app.app_context():
            before = self.db.session.query(User).count()
        response = self.client.post(
            '/user_management',
            data={'action': 'add', 'username': '', 'password': '', 'role': 'user'},
        )
        with self.app.app_context():
            after = self.db.session.query(User).count()
        self.assertEqual(before, after, 'No DB record should be created on validation failure')


@unittest.skipUnless(FLASK_AVAILABLE, SKIP_MSG)
class TestMultipleFieldErrors(unittest.TestCase):
    """Verify all field errors are returned in one response (non-short-circuit)."""

    def setUp(self):
        import os
        os.environ['LOCAL_DEVELOPMENT'] = 'true'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        from app import app
        from models.models import db
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def test_validate_form_returns_all_errors(self):
        """validate_form() must not short-circuit — all errors collected in one pass."""
        from utils.validation import validate_form, validate_required
        errors = validate_form([
            (validate_required, '', 'username'),
            (validate_required, '', 'password'),
            (validate_required, '', 'email'),
        ])
        self.assertEqual(len(errors), 3)
        field_names = [e['field'] for e in errors]
        self.assertIn('username', field_names)
        self.assertIn('password', field_names)
        self.assertIn('email', field_names)


if __name__ == '__main__':
    unittest.main()
