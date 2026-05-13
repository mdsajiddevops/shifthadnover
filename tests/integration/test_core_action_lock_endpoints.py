"""
T-039 — Integration tests: lock acquire/release endpoints (COMP-013, REQ-009).

Tests the standalone POST /core-action/<resource_id>/lock and
DELETE /core-action/<resource_id>/lock/<lock_id> endpoints.
"""
import os
import pytest
from unittest.mock import patch
from tests.integration.conftest import make_fake_user

VALID_UUID = "aa0e8400-e29b-41d4-a716-446655440010"
LOCK_ID = "bb0e8400-e29b-41d4-a716-446655440011"


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
class TestLockAcquireEndpoint:
    def _post_lock(self, app, resource_id=VALID_UUID, lock_return=None, side_effect=None):
        fake_user = make_fake_user(user_id="user_lock_1")
        if lock_return is None:
            lock_return = {"lock_id": LOCK_ID, "section_id": "incidents", "expires_at": "2026-05-13T07:00:00Z"}

        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user):
            if side_effect:
                ctx = patch("routes.core_action.acquire_lock", side_effect=side_effect)
            else:
                ctx = patch("routes.core_action.acquire_lock", return_value=lock_return)
            with ctx:
                with app.test_client() as client:
                    return client.post(
                        f"/core-action/{resource_id}/lock",
                        json={"section_id": "incidents"},
                    )

    def test_invalid_uuid_resource_id_returns_422(self, app):
        fake_user = make_fake_user(user_id="user_lock_1")
        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user):
            with app.test_client() as client:
                r = client.post("/core-action/not-a-uuid/lock", json={"section_id": "s1"})
        assert r.status_code == 422
        assert "resource_id" in r.get_json().get("fields", {})

    def test_lock_conflict_returns_409(self, app):
        from services.section_lock_coordinator import LockConflictError
        r = self._post_lock(app, side_effect=LockConflictError(locked_by="other_user", expires_at="2026-05-13T07:00:00Z"))
        assert r.status_code == 409
        data = r.get_json()
        assert data["error"] == "section_locked"
        assert "locked_by" in data

    def test_unauthenticated_returns_401(self, app):
        with app.test_client() as client:
            r = client.post(f"/core-action/{VALID_UUID}/lock", json={"section_id": "s1"})
        assert r.status_code == 401


@pytest.mark.integration
class TestLockReleaseEndpoint:
    def _delete_lock(self, app, resource_id=VALID_UUID, lock_id=LOCK_ID, release_return=None, side_effect=None):
        fake_user = make_fake_user(user_id="user_lock_1")
        if release_return is None:
            release_return = {"lock_id": lock_id, "section_id": "incidents"}

        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user):
            if side_effect:
                ctx = patch("routes.core_action.release_lock", side_effect=side_effect)
            else:
                ctx = patch("routes.core_action.release_lock", return_value=release_return)
            with ctx:
                with app.test_client() as client:
                    return client.delete(f"/core-action/{resource_id}/lock/{lock_id}")

    def test_successful_release_returns_200_with_lock_info(self, app):
        r = self._delete_lock(app)
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "released"
        assert "lock_id" in data
        assert "section_id" in data

    def test_not_found_returns_404(self, app):
        from services.section_lock_coordinator import LockNotFoundError
        r = self._delete_lock(app, side_effect=LockNotFoundError("Lock not found"))
        assert r.status_code == 404

    def test_not_owned_returns_403(self, app):
        from services.section_lock_coordinator import LockNotOwnedError
        r = self._delete_lock(app, side_effect=LockNotOwnedError(owned_by="other_user"))
        assert r.status_code == 403
        data = r.get_json()
        assert data["error"] == "permission_denied"

    def test_invalid_resource_id_returns_422(self, app):
        fake_user = make_fake_user(user_id="user_lock_1")
        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user):
            with app.test_client() as client:
                r = client.delete(f"/core-action/bad-id/lock/{LOCK_ID}")
        assert r.status_code == 422

    def test_unauthenticated_returns_401(self, app):
        with app.test_client() as client:
            r = client.delete(f"/core-action/{VALID_UUID}/lock/{LOCK_ID}")
        assert r.status_code == 401
