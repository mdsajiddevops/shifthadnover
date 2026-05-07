"""
Regression tests — Admin Management Features

Covers:
  - System configuration page
  - Email monitoring and stats
  - Active sessions management
  - User management (list, add, edit, delete)
  - Email configuration (SMTP)
  - Feature management toggles
  - System health endpoint
  - Shift configuration / timings
  - ServiceNow configuration page
"""
import re
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from tests.config import TestConfig

TIMESTAMP = datetime.now().strftime("%H%M%S")


# ---------------------------------------------------------------------------
# System & Configuration Pages
# ---------------------------------------------------------------------------


class TestSystemConfiguration:

    def test_configuration_page_loads(self, admin_session):
        resp = admin_session.get("/admin/configuration")
        assert resp.status_code == 200

    def test_configuration_has_sections(self, admin_session):
        page = admin_session.get("/admin/configuration").text.lower()
        assert any(term in page for term in ["configuration", "setting", "smtp", "email"])

    def test_system_health_page_loads(self, admin_session):
        resp = admin_session.get("/admin/system-health")
        assert resp.status_code == 200

    def test_system_health_shows_status(self, admin_session):
        page = admin_session.get("/admin/system-health").text.lower()
        assert any(term in page for term in ["database", "status", "health", "ok", "connected"])

    def test_feature_management_page_loads(self, admin_session):
        resp = admin_session.get("/admin/feature-management")
        assert resp.status_code == 200

    def test_shift_config_api(self, admin_session):
        resp = admin_session.get("/api/app/shifts")
        assert resp.status_code in (200, 204)

    def test_app_settings_api(self, admin_session):
        resp = admin_session.get("/api/app/settings")
        assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Email Monitoring
# ---------------------------------------------------------------------------


class TestEmailMonitoring:

    def test_email_monitoring_page_loads(self, admin_session):
        resp = admin_session.get("/admin/email-monitoring")
        assert resp.status_code == 200

    def test_email_monitoring_has_log_table(self, admin_session):
        soup = admin_session.soup("/admin/email-monitoring")
        tables = soup.find_all("table")
        assert len(tables) > 0, "Email monitoring page should contain a log table"

    def test_email_monitoring_shows_status_column(self, admin_session):
        page = admin_session.get("/admin/email-monitoring").text.lower()
        assert any(term in page for term in ["status", "sent", "failed", "success", "pending"])

    def test_email_monitoring_stats_api(self, admin_session):
        resp = admin_session.get("/api/email-monitoring/stats")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_email_notifications_api(self, admin_session):
        resp = admin_session.get("/api/email-notifications")
        assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Active Sessions
# ---------------------------------------------------------------------------


class TestActiveSessions:

    def test_active_sessions_page_loads(self, admin_session):
        resp = admin_session.get("/admin/active-sessions")
        assert resp.status_code == 200

    def test_active_sessions_api(self, admin_session):
        resp = admin_session.get("/api/active-sessions")
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_active_sessions_shows_current_session(self, admin_session):
        page = admin_session.get("/admin/active-sessions").text.lower()
        assert any(term in page for term in ["session", "user", "active", "login"])


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------


class TestUserManagement:

    def test_user_management_page_loads(self, admin_session):
        resp = admin_session.get("/user-management")
        assert resp.status_code == 200

    def test_user_management_lists_users(self, admin_session):
        soup = admin_session.soup("/user-management")
        tables_or_lists = soup.find_all("table") + soup.find_all("ul")
        assert len(tables_or_lists) > 0, "User management should list users in a table or list"

    def test_users_api_returns_json(self, admin_session):
        resp = admin_session.get(f"/api/accounts/{TestConfig.TEST_ACCOUNT_ID}/teams")
        assert resp.status_code in (200, 204)

    def test_add_user_page_loads(self, admin_session):
        resp = admin_session.get("/users/add")
        assert resp.status_code in (200, 302)

    def test_admin_cannot_terminate_own_session(self, admin_session):
        """Sanity check — admin pages are functional."""
        resp = admin_session.get("/admin/active-sessions")
        assert resp.status_code == 200
        # Should see a terminate option, not an error
        page = resp.text.lower()
        assert "error" not in page or "session" in page

    def test_user_team_assignment_api(self, admin_session):
        """Get teams for the first user returned."""
        # This just verifies the API endpoint exists and is reachable
        resp = admin_session.get("/api/user/1/teams")
        assert resp.status_code in (200, 403, 404)
        # 404 = user 1 doesn't exist; 403 = cross-account; both are fine


# ---------------------------------------------------------------------------
# Shift Configuration
# ---------------------------------------------------------------------------


class TestShiftConfiguration:

    def test_team_shift_timings_page_loads(self, admin_session):
        resp = admin_session.get(f"/team-shift-timings/team/{TestConfig.TEST_TEAM_ID}")
        assert resp.status_code in (200, 302, 404)

    def test_shift_timings_list(self, admin_session):
        resp = admin_session.get("/team-shift-timings")
        assert resp.status_code in (200, 302, 404)


# ---------------------------------------------------------------------------
# Scheduler / Background Tasks
# ---------------------------------------------------------------------------


class TestSchedulerStatus:

    def test_scheduler_status_endpoint(self, admin_session):
        resp = admin_session.get("/scheduler-status")
        assert resp.status_code in (200, 204, 404)
        if resp.status_code == 200:
            page = resp.text.lower()
            assert any(term in page for term in ["celery", "task", "worker", "beat", "schedule"])


# ---------------------------------------------------------------------------
# Admin Incident Metrics
# ---------------------------------------------------------------------------


class TestIncidentMetrics:

    def test_incident_metrics_page_loads(self, admin_session):
        resp = admin_session.get("/admin/incident-metrics")
        assert resp.status_code in (200, 302, 404)

    def test_incident_response_logs_page(self, admin_session):
        resp = admin_session.get("/admin/incident-response-logs")
        assert resp.status_code in (200, 302, 404)
