"""
Regression tests — Authentication & Role-Based Access Control

Covers:
  - Unauthenticated requests are redirected to /login
  - Login with invalid credentials is rejected
  - Login / logout round-trip works
  - Forgot-password page is reachable
  - Regular users cannot access super-admin-only pages (403 or redirect)
  - CSRF token is required on login POST
"""
import pytest
import requests

from tests.config import TestConfig
from tests.regression.conftest import AppSession


# ---------------------------------------------------------------------------
# Pages that must require authentication
# ---------------------------------------------------------------------------
PROTECTED_PAGES = [
    "/",
    "/handover",
    "/reports",
    "/keypoints",
    "/roster",
    "/escalation-matrix",
    "/vendor-details",
    "/profile",
    "/notifications",
]

# Pages only super_admin / account_admin should reach
ADMIN_ONLY_PAGES = [
    "/admin/configuration",
    "/admin/email-monitoring",
    "/admin/active-sessions",
    "/user-management",
    "/admin/system-health",
    "/admin/feature-management",
    "/admin/manual-roster",
]


class TestUnauthenticatedAccess:
    """Protected pages must redirect an anonymous visitor to /login."""

    @pytest.mark.parametrize("path", PROTECTED_PAGES)
    def test_redirect_to_login(self, anon_session, path):
        resp = anon_session.session.get(
            f"{anon_session.base_url}{path}",
            timeout=TestConfig.REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        # Either the final URL contains /login, or a 401/403 is returned
        redirected_to_login = "/login" in resp.url
        access_denied = resp.status_code in (401, 403)
        assert redirected_to_login or access_denied, (
            f"Expected redirect to /login or 401/403 for {path}, "
            f"got status={resp.status_code} url={resp.url}"
        )

    def test_login_page_is_public(self, anon_session):
        resp = anon_session.get("/login")
        assert resp.status_code == 200
        assert "login" in resp.text.lower()

    def test_forgot_password_page_is_public(self, anon_session):
        resp = anon_session.get("/forgot-password")
        assert resp.status_code == 200


class TestLoginLogout:
    """Login / logout flows."""

    def test_login_valid_credentials(self):
        creds = TestConfig.TEST_USERS["super_admin"]
        s = AppSession()
        success = s.login(creds["username"], creds["password"])
        assert success, "Login with valid super_admin credentials should succeed"
        # Confirm we can now load a protected page
        resp = s.get("/")
        assert resp.status_code == 200
        s.logout()

    def test_login_invalid_password_rejected(self):
        creds = TestConfig.TEST_USERS["super_admin"]
        s = AppSession()

        resp = s.session.get(
            f"{s.base_url}/login", timeout=TestConfig.REQUEST_TIMEOUT
        )
        token = s.csrf_token_from_html(resp.text)
        resp = s.session.post(
            f"{s.base_url}/login",
            data={
                "username": creds["username"],
                "password": "WRONG_PASSWORD_REGRESSION_TEST",
                "csrf_token": token,
            },
            allow_redirects=True,
            timeout=TestConfig.REQUEST_TIMEOUT,
        )
        still_on_login = "/login" in resp.url or "invalid" in resp.text.lower() or "incorrect" in resp.text.lower()
        assert still_on_login, "Login with wrong password should not succeed"

    def test_login_unknown_user_rejected(self):
        s = AppSession()
        resp = s.session.get(f"{s.base_url}/login", timeout=TestConfig.REQUEST_TIMEOUT)
        token = s.csrf_token_from_html(resp.text)
        resp = s.session.post(
            f"{s.base_url}/login",
            data={
                "username": "nonexistent_user_xyz_regression",
                "password": "password123",
                "csrf_token": token,
            },
            allow_redirects=True,
            timeout=TestConfig.REQUEST_TIMEOUT,
        )
        still_on_login = "/login" in resp.url
        assert still_on_login, "Login with unknown username should stay on /login"

    def test_logout_destroys_session(self):
        creds = TestConfig.TEST_USERS["super_admin"]
        s = AppSession()
        s.login(creds["username"], creds["password"])
        assert s.get("/").status_code == 200

        s.logout()

        # After logout the session cookie should be invalid
        resp = s.session.get(
            f"{s.base_url}/",
            allow_redirects=True,
            timeout=TestConfig.REQUEST_TIMEOUT,
        )
        assert "/login" in resp.url or resp.status_code in (401, 403), (
            "After logout, protected pages should redirect to /login"
        )

    def test_csrf_required_on_login_post(self):
        s = AppSession()
        creds = TestConfig.TEST_USERS["super_admin"]
        # POST without csrf_token
        resp = s.session.post(
            f"{s.base_url}/login",
            data={"username": creds["username"], "password": creds["password"]},
            allow_redirects=False,
            timeout=TestConfig.REQUEST_TIMEOUT,
        )
        # Flask-WTF returns 400 Bad Request when CSRF is missing/invalid
        assert resp.status_code in (400, 302, 200), (
            "Request without CSRF token should be rejected (400) or stay on login"
        )
        # Specifically, we must NOT be redirected away from login successfully
        if resp.status_code == 302:
            assert "/login" in resp.headers.get("Location", ""), (
                "CSRF-less login should not redirect to protected pages"
            )


class TestRoleBasedAccess:
    """Regular users must not be able to reach admin-only pages."""

    @pytest.mark.parametrize("path", ADMIN_ONLY_PAGES)
    def test_regular_user_denied_admin_page(self, user_session, path):
        resp = user_session.session.get(
            f"{user_session.base_url}{path}",
            timeout=TestConfig.REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        denied = resp.status_code in (403, 404) or "/login" in resp.url or "unauthorized" in resp.text.lower() or "permission" in resp.text.lower() or "access" in resp.text.lower()
        # Also acceptable: redirect to dashboard/home with a flash message
        redirected_away = resp.url != f"{user_session.base_url}{path}" and resp.status_code == 200
        assert denied or redirected_away, (
            f"Regular user should not have full access to {path}. "
            f"Got status={resp.status_code} url={resp.url}"
        )

    @pytest.mark.parametrize("path", ADMIN_ONLY_PAGES)
    def test_admin_can_reach_admin_page(self, admin_session, path):
        resp = admin_session.get(path)
        assert resp.status_code == 200, (
            f"Admin should be able to access {path}, got {resp.status_code}"
        )
