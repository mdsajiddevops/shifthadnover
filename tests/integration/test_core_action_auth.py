"""
T-034 — Integration tests: session validation and permission guard (COMP-007, REQ-010).
"""
import os
import pytest
from unittest.mock import patch
from tests.integration.conftest import make_fake_user


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
class TestCoreActionAuth:
    def test_no_session_returns_401(self, app):
        """Unauthenticated request to POST /core-action must return 401."""
        with app.test_client() as client:
            response = client.post(
                "/core-action",
                json={"resource_id": "550e8400-e29b-41d4-a716-446655440000", "section_id": "s1", "payload": {}},
            )
        assert response.status_code == 401

    def test_authenticated_insufficient_role_returns_403(self, app):
        """User with a role excluded from CORE_ACTION_EXECUTE gets 403."""
        # Override the permission map so 'restricted_user' is not allowed
        fake_user = make_fake_user(role="restricted_user")
        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user), \
             patch("decorators.permission_guard._PERMISSION_ROLES", {"CORE_ACTION_EXECUTE": {"user"}}):
            with app.test_client() as client:
                response = client.post(
                    "/core-action",
                    json={"resource_id": "550e8400-e29b-41d4-a716-446655440000", "section_id": "s1", "payload": {}},
                )
        assert response.status_code == 403

    def test_execute_service_not_called_on_401(self, app):
        """Business logic must not execute on unauthenticated request."""
        with patch("routes.core_action.execute_core_action") as mock_exec:
            with app.test_client() as client:
                response = client.post(
                    "/core-action",
                    json={"resource_id": "550e8400-e29b-41d4-a716-446655440000", "section_id": "s1", "payload": {}},
                )
        assert response.status_code == 401
        mock_exec.assert_not_called()
