"""T-029 — Unit tests for Permission Guard Decorator (COMP-010, REQ-010)."""
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask


@pytest.fixture
def flask_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["WTF_CSRF_ENABLED"] = False
    return app


def _make_user(role, authenticated=True):
    user = MagicMock()
    user.is_authenticated = authenticated
    user.role = role
    return user


class TestRequirePermission:
    def test_permissioned_user_can_call_wrapped_function(self, flask_app):
        from decorators.permission_guard import require_permission

        inner = MagicMock(return_value=("OK", 200))

        @require_permission("CORE_ACTION_EXECUTE")
        def view():
            return inner()

        with flask_app.test_request_context():
            with patch("decorators.permission_guard.current_user", _make_user("user")):
                status = view()

        assert inner.call_count == 1
        # return value is the wrapped function's return value
        assert status == ("OK", 200)

    def test_unpermissioned_user_gets_403_and_inner_not_called(self, flask_app):
        from decorators.permission_guard import require_permission

        inner = MagicMock()
        # Simulate a role that is NOT in _PERMISSION_ROLES for this permission
        @require_permission("CORE_ACTION_EXECUTE")
        def view():
            return inner()  # pragma: no cover

        with flask_app.test_request_context():
            # Override _PERMISSION_ROLES so "guest" is not allowed
            with patch("decorators.permission_guard._PERMISSION_ROLES", {"CORE_ACTION_EXECUTE": {"user"}}):
                with patch("decorators.permission_guard.current_user", _make_user("guest")):
                    response, status_code = view()

        assert status_code == 403
        response_json = response.get_json()
        assert response_json["error"] == "permission_denied"
        assert "required_permission" in response_json
        assert inner.call_count == 0

    def test_unauthenticated_user_gets_401_and_inner_not_called(self, flask_app):
        from decorators.permission_guard import require_permission

        inner = MagicMock()

        @require_permission("CORE_ACTION_EXECUTE")
        def view():
            return inner()  # pragma: no cover

        unauthenticated_user = _make_user("user", authenticated=False)

        with flask_app.test_request_context():
            with patch("decorators.permission_guard.current_user", unauthenticated_user):
                response, status_code = view()

        assert status_code == 401
        response_json = response.get_json()
        assert response_json["error"] == "authentication_required"
        assert "redirect" in response_json
        assert inner.call_count == 0

    def test_no_current_user_gets_401(self, flask_app):
        from decorators.permission_guard import require_permission

        inner = MagicMock()

        @require_permission("CORE_ACTION_EXECUTE")
        def view():
            return inner()  # pragma: no cover

        with flask_app.test_request_context():
            with patch("decorators.permission_guard.current_user", None):
                response, status_code = view()

        assert status_code == 401
        assert inner.call_count == 0
