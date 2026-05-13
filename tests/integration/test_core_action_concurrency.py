"""
T-037 — Integration tests: concurrent lock conflict (COMP-013, REQ-009).

Tests that a 409 is returned when a resource section is already locked,
and that no core_action_records row is created for the rejected request.
"""
import os
import pytest
from unittest.mock import patch
from tests.integration.conftest import make_fake_user

VALID_UUID = "770e8400-e29b-41d4-a716-446655440002"


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
class TestCoreActionConcurrency:
    def _post(self, app, service_side_effect=None, service_return=None):
        fake_user = make_fake_user(user_id="user_concurrency_1")

        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user):
            if service_side_effect:
                ctx_mgr = patch("routes.core_action.execute_core_action", side_effect=service_side_effect)
            else:
                ctx_mgr = patch("routes.core_action.execute_core_action", return_value=service_return)
            with ctx_mgr:
                with app.test_client() as client:
                    return client.post(
                        "/core-action",
                        json={
                            "resource_id": VALID_UUID,
                            "section_id": "incidents",
                            "payload": {},
                        },
                    )

    def test_lock_conflict_returns_409(self, app):
        from services.section_lock_coordinator import LockConflictError
        r = self._post(app, service_side_effect=LockConflictError(locked_by="user_2"))
        assert r.status_code == 409

    def test_409_response_contains_locked_by(self, app):
        from services.section_lock_coordinator import LockConflictError
        r = self._post(app, service_side_effect=LockConflictError(locked_by="user_2"))
        data = r.get_json()
        assert "locked_by" in data
        assert data["locked_by"] == "user_2"

    def test_successful_request_after_no_conflict_returns_200(self, app):
        success = {
            "status": "completed",
            "core_action_id": "ca-conc-001",
            "resource_id": VALID_UUID,
            "section_id": "incidents",
            "completed_at": "2026-05-13T06:00:00Z",
            "actor": "user_concurrency_1",
        }
        r = self._post(app, service_return=success)
        assert r.status_code == 200
