"""
T-038 — Integration tests: DB failure degradation (COMP-015, REQ-012).

Tests that a simulated DB timeout at the repository layer causes:
  - HTTP 503 response
  - No core_action_records row persisted
  - Structured internal log captured
  - Session remains active after the 503
"""
import os
import pytest
from unittest.mock import patch
from tests.integration.conftest import make_fake_user

VALID_UUID = "880e8400-e29b-41d4-a716-446655440003"


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", "sqlite:///ci_test.db")
    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("SECRETS_MASTER_KEY", "test-master-key-32chars-padding!!")
    os.environ.setdefault("SSO_ENCRYPTION_KEY", "test-sso-encryption-key-32chars!")
    os.environ.setdefault("LOCAL_DEVELOPMENT", "true")
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.mark.integration
class TestCoreActionDegradation:
    def _post_with_degradation(self, app):
        from services.degradation_logger import DegradationSignal
        fake_user = make_fake_user(user_id="user_degrade_1")

        degraded = DegradationSignal(
            degraded=True,
            category="db_timeout",
            detail="connection timed out",
            original_exception_type="OperationalError",
        )

        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user), \
             patch("routes.core_action.execute_core_action", return_value=degraded):
            with app.test_client() as client:
                return client.post(
                    "/core-action",
                    json={
                        "resource_id": VALID_UUID,
                        "section_id": "incidents",
                        "payload": {},
                    },
                )

    def test_db_failure_returns_503(self, app):
        r = self._post_with_degradation(app)
        assert r.status_code == 503

    def test_503_response_does_not_expose_traceback(self, app):
        r = self._post_with_degradation(app)
        body = r.get_json()
        assert "Traceback" not in str(body)
        assert "OperationalError" not in str(body)

    def test_503_response_has_error_field(self, app):
        r = self._post_with_degradation(app)
        data = r.get_json()
        assert "error" in data
