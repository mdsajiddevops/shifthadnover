"""
T-035 — Integration tests: input validation error responses (COMP-009, REQ-008).

Tests that POST /core-action returns 422 with field-keyed errors for every
class of validation failure.
"""
import os
import pytest
from unittest.mock import patch
from tests.integration.conftest import make_fake_user

VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


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
class TestCoreActionValidation:
    """These tests patch out flask_login so we can reach the validation layer."""

    def _post(self, app, payload_body):
        fake_user = make_fake_user()

        with patch("flask_login.utils._get_user", return_value=fake_user), \
             patch("decorators.permission_guard.current_user", fake_user):
            with app.test_client() as client:
                return client.post("/core-action", json=payload_body)

    def test_missing_resource_id_returns_422(self, app):
        r = self._post(app, {"section_id": "s1", "payload": {}})
        assert r.status_code == 422
        data = r.get_json()
        assert "resource_id" in data.get("fields", {})

    def test_invalid_uuid_resource_id_returns_422(self, app):
        r = self._post(app, {"resource_id": "not-a-uuid", "section_id": "s1", "payload": {}})
        assert r.status_code == 422
        data = r.get_json()
        assert "resource_id" in data.get("fields", {})

    def test_missing_section_id_returns_422(self, app):
        r = self._post(app, {"resource_id": VALID_UUID, "payload": {}})
        assert r.status_code == 422
        data = r.get_json()
        assert "section_id" in data.get("fields", {})

    def test_section_id_too_long_returns_422(self, app):
        r = self._post(app, {"resource_id": VALID_UUID, "section_id": "x" * 129, "payload": {}})
        assert r.status_code == 422
        data = r.get_json()
        assert "section_id" in data.get("fields", {})

    def test_missing_payload_returns_422(self, app):
        r = self._post(app, {"resource_id": VALID_UUID, "section_id": "s1"})
        assert r.status_code == 422
        data = r.get_json()
        assert "payload" in data.get("fields", {})

    def test_payload_not_object_returns_422(self, app):
        r = self._post(app, {"resource_id": VALID_UUID, "section_id": "s1", "payload": "bad"})
        assert r.status_code == 422
        data = r.get_json()
        assert "payload" in data.get("fields", {})

    def test_multiple_invalid_fields_all_in_errors(self, app):
        r = self._post(app, {"resource_id": "bad", "section_id": "", "payload": 42})
        assert r.status_code == 422
        errors = r.get_json().get("fields", {})
        assert "resource_id" in errors
        assert "section_id" in errors
        assert "payload" in errors
