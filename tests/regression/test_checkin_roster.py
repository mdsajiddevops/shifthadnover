"""
Regression tests — Check-in / Check-out & Roster

Covers:
  - Check-in status API returns valid JSON
  - Check-in POST (mark self as on duty)
  - Check-out POST (mark self as off duty)
  - Check-in history endpoint
  - Team status endpoint
  - Roster page loads and shows shift/engineer data
  - Shift schedule page loads
  - Shift swap/leave pages load (if feature enabled)
"""
import pytest

from tests.config import TestConfig


class TestCheckin:
    """Check-in / check-out flow via the JSON API."""

    def test_checkin_status_returns_json(self, admin_session):
        resp = admin_session.get("/api/checkin/status")
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type", "").startswith("application/json"), (
            "Check-in status endpoint should return JSON"
        )

    def test_checkin_status_has_expected_shape(self, admin_session):
        data = admin_session.get("/api/checkin/status").json()
        # Expect a dict or list — not an error object
        assert isinstance(data, (dict, list)), f"Unexpected shape: {type(data)}"

    def test_checkin_post(self, admin_session):
        """POST to check in — idempotent so safe to run repeatedly."""
        resp = admin_session.post(
            "/api/checkin",
            json={"action": "checkin", "team_id": TestConfig.TEST_TEAM_ID},
        )
        assert resp.status_code in (200, 201, 409), (
            f"Check-in returned unexpected status {resp.status_code}: {resp.text[:200]}"
        )
        # 409 = already checked in (acceptable, not a regression failure)

    def test_checkout_post(self, admin_session):
        resp = admin_session.post(
            "/api/checkin",
            json={"action": "checkout", "team_id": TestConfig.TEST_TEAM_ID},
        )
        assert resp.status_code in (200, 201, 404, 409), (
            f"Check-out returned unexpected status {resp.status_code}: {resp.text[:200]}"
        )

    def test_checkin_history_endpoint(self, admin_session):
        resp = admin_session.get("/api/checkin/history")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_team_status_endpoint(self, admin_session):
        resp = admin_session.get(f"/api/team-status/{TestConfig.TEST_TEAM_ID}")
        assert resp.status_code in (200, 404), (
            f"Team status endpoint returned {resp.status_code}"
        )
        if resp.status_code == 200:
            assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_regular_user_can_checkin(self, user_session):
        resp = user_session.post(
            "/api/checkin",
            json={"action": "checkin", "team_id": TestConfig.TEST_TEAM_ID},
        )
        assert resp.status_code in (200, 201, 409), (
            f"Regular user check-in returned {resp.status_code}"
        )


class TestRosterPages:
    """Roster display and management pages."""

    def test_roster_page_loads(self, admin_session):
        resp = admin_session.get("/roster")
        assert resp.status_code == 200

    def test_roster_has_shift_content(self, admin_session):
        page = admin_session.get("/roster").text.lower()
        assert any(term in page for term in ["shift", "engineer", "roster", "schedule"])

    def test_teams_roster_page_loads(self, admin_session):
        resp = admin_session.get("/teams-roster")
        assert resp.status_code == 200

    def test_shift_schedule_page_loads(self, admin_session):
        resp = admin_session.get("/shift-schedule")
        assert resp.status_code in (200, 302, 404)
        # 404 acceptable if feature not configured; 302 = redirect to setup

    def test_manual_roster_page_loads(self, admin_session):
        resp = admin_session.get("/admin/manual-roster")
        assert resp.status_code == 200

    def test_available_engineers_api(self, admin_session):
        resp = admin_session.get(
            f"/api/available-engineers?team_id={TestConfig.TEST_TEAM_ID}"
        )
        assert resp.status_code in (200, 204)

    def test_roster_page_for_regular_user(self, user_session):
        resp = user_session.get("/roster")
        assert resp.status_code == 200


class TestShiftSwapLeave:
    """Shift swap and leave request pages (optional feature)."""

    def test_swap_request_page_loads(self, user_session):
        resp = user_session.get("/swap/request")
        # This feature may not be enabled; 302/404 is acceptable
        assert resp.status_code in (200, 302, 404)

    def test_shift_allowance_page(self, admin_session):
        resp = admin_session.get("/shift-allowance")
        assert resp.status_code in (200, 302, 404)

    def test_simple_swap_request(self, user_session):
        resp = user_session.get("/simple-swap-request")
        assert resp.status_code in (200, 302, 404)


class TestRosterUpload:
    """Roster upload page — admin only."""

    def test_roster_upload_page_accessible_to_admin(self, admin_session):
        resp = admin_session.get("/roster-upload")
        assert resp.status_code in (200, 302)

    def test_roster_upload_blocked_for_regular_user(self, user_session):
        resp = user_session.session.get(
            f"{user_session.base_url}/roster-upload",
            allow_redirects=True,
            timeout=TestConfig.REQUEST_TIMEOUT,
        )
        denied = resp.status_code in (403, 404) or "/login" in resp.url
        redirected = resp.url != f"{user_session.base_url}/roster-upload" and resp.status_code == 200
        assert denied or redirected, (
            "Regular user should not have unrestricted access to /roster-upload"
        )
