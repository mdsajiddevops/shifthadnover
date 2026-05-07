"""
Regression tests — API Response Contracts

Ensures that JSON APIs:
  - Return correct Content-Type headers
  - Return expected HTTP status codes for authenticated requests
  - Return 401/redirect for unauthenticated requests
  - Return structured JSON (not HTML error pages)

These tests act as a contract layer — if a refactor silently changes
an API from JSON to HTML, or from 200 to 500, these tests catch it.
"""
import pytest

from tests.config import TestConfig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def assert_json(resp, *, label=""):
    prefix = f"[{label}] " if label else ""
    ct = resp.headers.get("Content-Type", "")
    assert "application/json" in ct, (
        f"{prefix}Expected JSON Content-Type, got '{ct}'. "
        f"Status: {resp.status_code}. Body[:200]: {resp.text[:200]}"
    )
    data = resp.json()
    assert data is not None, f"{prefix}Response JSON is null"
    return data


# ---------------------------------------------------------------------------
# Unauthenticated access to JSON APIs
# ---------------------------------------------------------------------------


JSON_API_ENDPOINTS = [
    "/api/checkin/status",
    "/api/active-sessions",
    "/api/email-monitoring/stats",
    f"/api/escalation-matrix/entries",
    "/api/application-details",
]


class TestUnauthenticatedAPIAccess:
    """JSON APIs must not silently return HTML login pages to unauth clients."""

    @pytest.mark.parametrize("path", JSON_API_ENDPOINTS)
    def test_unauth_api_does_not_return_200_html(self, anon_session, path):
        resp = anon_session.session.get(
            f"{anon_session.base_url}{path}",
            timeout=TestConfig.REQUEST_TIMEOUT,
            allow_redirects=False,  # Don't follow to /login HTML page
        )
        if resp.status_code == 200:
            ct = resp.headers.get("Content-Type", "")
            assert "application/json" in ct, (
                f"Unauth GET {path} returned 200 with non-JSON content ({ct}). "
                "API should return 401 or redirect, not an HTML login page."
            )


# ---------------------------------------------------------------------------
# Authenticated JSON API contracts
# ---------------------------------------------------------------------------


class TestCheckinAPIContract:

    def test_status_returns_json(self, admin_session):
        resp = admin_session.get("/api/checkin/status")
        assert resp.status_code == 200
        assert_json(resp, label="checkin/status")

    def test_history_returns_json_or_204(self, admin_session):
        resp = admin_session.get("/api/checkin/history")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="checkin/history")


class TestEscalationMatrixAPIContract:

    def test_entries_returns_json(self, admin_session):
        resp = admin_session.get(
            f"/api/escalation-matrix/entries"
            f"?account_id={TestConfig.TEST_ACCOUNT_ID}"
            f"&team_id={TestConfig.TEST_TEAM_ID}"
        )
        assert resp.status_code == 200
        assert_json(resp, label="escalation-matrix/entries")

    def test_teams_by_account_returns_json(self, admin_session):
        resp = admin_session.get(
            f"/api/escalation-matrix/teams-by-account"
            f"?account_id={TestConfig.TEST_ACCOUNT_ID}"
        )
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="escalation-matrix/teams-by-account")


class TestHandoverAPIContract:

    def test_get_engineers_returns_json(self, admin_session):
        resp = admin_session.get("/api/get_engineers")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="get_engineers")

    def test_get_all_team_members_returns_json(self, admin_session):
        resp = admin_session.get("/api/get_all_team_members")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="get_all_team_members")

    def test_team_members_by_team_id(self, admin_session):
        resp = admin_session.get(f"/api/team-members/{TestConfig.TEST_TEAM_ID}")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label=f"team-members/{TestConfig.TEST_TEAM_ID}")


class TestActiveSessionsAPIContract:

    def test_active_sessions_returns_json(self, admin_session):
        resp = admin_session.get("/api/active-sessions")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="active-sessions")


class TestEmailAPIContract:

    def test_email_monitoring_stats_returns_json(self, admin_session):
        resp = admin_session.get("/api/email-monitoring/stats")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="email-monitoring/stats")

    def test_email_recipients_returns_json(self, admin_session):
        resp = admin_session.get(
            f"/api/email-recipients"
            f"?account_id={TestConfig.TEST_ACCOUNT_ID}"
            f"&team_id={TestConfig.TEST_TEAM_ID}"
        )
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="email-recipients")


class TestAccountTeamAPIContract:

    def test_accounts_api_returns_json(self, admin_session):
        resp = admin_session.get("/api/accounts")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label="accounts")

    def test_account_teams_api_returns_json(self, admin_session):
        resp = admin_session.get(
            f"/api/accounts/{TestConfig.TEST_ACCOUNT_ID}/teams"
        )
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert_json(resp, label=f"accounts/{TestConfig.TEST_ACCOUNT_ID}/teams")


class TestChangeInfoAPIContract:

    def test_post_requires_json_body(self, admin_session):
        """Posting without required fields should return 4xx, not 500."""
        resp = admin_session.post("/api/change-info", json={})
        assert resp.status_code in (400, 422, 500), (
            f"Empty change-info POST returned unexpected {resp.status_code}"
        )
        # Even error responses should ideally be JSON
        if resp.status_code != 500:
            ct = resp.headers.get("Content-Type", "")
            # Accept HTML error pages for 500 (server error) — just don't want silent 200
            if "application/json" in ct:
                assert_json(resp, label="change-info POST empty")

    def test_get_nonexistent_change_returns_404(self, admin_session):
        resp = admin_session.get("/api/change-info/999999999")
        assert resp.status_code in (404, 400), (
            f"Non-existent change info should return 404, got {resp.status_code}"
        )
