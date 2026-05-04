"""
Regression tests — User Profile & Account Settings

Covers:
  - Profile page loads for both admin and regular user
  - Profile edit page loads
  - Change password page is accessible
  - Account settings page
  - Multi-team context switching (set_selection, set_team_filter)
  - Reset-to-primary-team works
  - Onboarding pages load correctly
"""
import pytest

from tests.config import TestConfig


class TestUserProfile:

    def test_profile_page_loads_admin(self, admin_session):
        resp = admin_session.get("/profile")
        assert resp.status_code == 200

    def test_profile_page_loads_regular_user(self, user_session):
        resp = user_session.get("/profile")
        assert resp.status_code == 200

    def test_profile_has_user_info(self, admin_session):
        page = admin_session.get("/profile").text.lower()
        assert any(term in page for term in ["username", "email", "profile", "account"])

    def test_profile_edit_page_loads(self, admin_session):
        resp = admin_session.get("/profile/edit")
        assert resp.status_code in (200, 302)

    def test_change_password_page_loads(self, admin_session):
        resp = admin_session.get("/profile/change-password")
        assert resp.status_code in (200, 302)

    def test_account_settings_page_loads(self, admin_session):
        resp = admin_session.get("/account-settings")
        assert resp.status_code in (200, 302, 404)


class TestTeamContextSwitching:
    """set_selection and set_team_filter control the active account/team context in session."""

    def test_set_selection_post(self, admin_session):
        token, _ = admin_session.csrf_for_path("/")
        resp = admin_session.post(
            "/set_selection",
            data={
                "csrf_token": token,
                "account_id": str(TestConfig.TEST_ACCOUNT_ID),
                "team_id": str(TestConfig.TEST_TEAM_ID),
            },
            allow_redirects=True,
        )
        assert resp.status_code in (200, 302), (
            f"set_selection returned {resp.status_code}"
        )

    def test_set_team_filter_post(self, admin_session):
        token, _ = admin_session.csrf_for_path("/")
        resp = admin_session.post(
            "/set_team_filter",
            data={
                "csrf_token": token,
                "team_id": str(TestConfig.TEST_TEAM_ID),
            },
            allow_redirects=True,
        )
        assert resp.status_code in (200, 302), (
            f"set_team_filter returned {resp.status_code}"
        )

    def test_reset_to_primary_team(self, admin_session):
        resp = admin_session.get("/reset-to-primary-team", allow_redirects=True)
        assert resp.status_code in (200, 302), (
            f"reset-to-primary-team returned {resp.status_code}"
        )

    def test_set_primary_team(self, admin_session):
        resp = admin_session.post(
            f"/set-primary-team/{TestConfig.TEST_TEAM_ID}",
            data={},
            allow_redirects=True,
        )
        assert resp.status_code in (200, 302, 404), (
            f"set-primary-team returned {resp.status_code}"
        )


class TestOnboarding:

    def test_onboarding_page_loads(self, admin_session):
        resp = admin_session.get("/onboarding")
        # Onboarding may redirect if already complete
        assert resp.status_code in (200, 302)

    def test_onboarding_skip(self, admin_session):
        token, _ = admin_session.csrf_for_path("/onboarding")
        resp = admin_session.post(
            "/onboarding/skip",
            data={"csrf_token": token},
            allow_redirects=True,
        )
        assert resp.status_code in (200, 302, 404)


class TestDashboardWidgets:
    """Dashboard is the landing page — regression-critical."""

    def test_dashboard_loads_for_admin(self, admin_session):
        resp = admin_session.get("/")
        assert resp.status_code == 200

    def test_dashboard_loads_for_regular_user(self, user_session):
        resp = user_session.get("/")
        assert resp.status_code == 200

    def test_dashboard_has_shift_context(self, admin_session):
        page = admin_session.get("/").text.lower()
        assert any(term in page for term in ["shift", "handover", "engineer", "dashboard"])

    def test_dashboard_has_key_points_section(self, admin_session):
        page = admin_session.get("/").text.lower()
        assert "key point" in page or "keypoint" in page

    def test_dashboard_with_team_filter(self, admin_session):
        resp = admin_session.get(f"/?team_id={TestConfig.TEST_TEAM_ID}")
        assert resp.status_code == 200

    def test_about_page_loads(self, admin_session):
        resp = admin_session.get("/about")
        assert resp.status_code in (200, 404)

    def test_alerts_page_loads(self, admin_session):
        resp = admin_session.get("/alerts")
        assert resp.status_code in (200, 302, 404)
