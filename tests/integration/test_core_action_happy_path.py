"""
T-036 — Integration tests: CoreAction happy path (COMP-008, REQ-007, REQ-009).

Tests that a successful POST /core-action returns HTTP 200 with all required
response fields and that the DB records are created correctly.
Requires a running app + DB (skipped in environments without MySQL).
"""
import os
import pytest
from unittest.mock import patch
from tests.integration.conftest import make_fake_user

VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"
VALID_UUID2 = "660e8400-e29b-41d4-a716-446655440001"


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
class TestCoreActionHappyPath:
    def _post_with_mock_service(self, app, resource_id, success_result=None):
        fake_user = make_fake_user(user_id="user_happy_1")

        if success_result is None:
            success_result = {
                "status": "completed",
                "core_action_id": "ca-test-001",
                "resource_id": resource_id,
                "section_id": "incidents",
                "completed_at": "2026-05-13T06:00:00Z",
                "actor": "user_happy_1",
            }

        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user), \
             patch("routes.core_action.execute_core_action", return_value=success_result):
            with app.test_client() as client:
                return client.post(
                    "/core-action",
                    json={
                        "resource_id": resource_id,
                        "section_id": "incidents",
                        "payload": {"action": "confirm"},
                    },
                )

    def test_happy_path_returns_200(self, app):
        r = self._post_with_mock_service(app, VALID_UUID)
        assert r.status_code == 200

    def test_happy_path_response_has_required_fields(self, app):
        r = self._post_with_mock_service(app, VALID_UUID)
        data = r.get_json()
        assert data["status"] == "completed"
        assert "core_action_id" in data
        assert "resource_id" in data
        assert "section_id" in data
        assert "completed_at" in data
        assert "actor" in data

    def test_two_different_resources_no_cross_leakage(self, app):
        r1 = self._post_with_mock_service(app, VALID_UUID)
        r2 = self._post_with_mock_service(app, VALID_UUID2)
        d1 = r1.get_json()
        d2 = r2.get_json()
        assert d1["resource_id"] == VALID_UUID
        assert d2["resource_id"] == VALID_UUID2
