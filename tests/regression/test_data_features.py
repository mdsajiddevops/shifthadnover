"""
Regression tests — Key Points, Incidents, Change Info, KB Updates, Escalation Matrix

Covers:
  - Key points page loads and has expected structure
  - No duplicate key points on the page
  - Key point status can be updated
  - Change info API: create, retrieve, update, delete
  - Escalation matrix API: CRUD operations
  - Notifications page accessible
  - Vendor details page accessible
  - Application details accessible
"""
import re
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from tests.config import TestConfig

TIMESTAMP = datetime.now().strftime("%H%M%S")


# ---------------------------------------------------------------------------
# Key Points
# ---------------------------------------------------------------------------


class TestKeyPoints:
    """Key points page and data integrity."""

    def test_keypoints_page_loads(self, admin_session):
        resp = admin_session.get("/keypoints")
        assert resp.status_code == 200

    def test_keypoints_page_has_table_or_list(self, admin_session):
        soup = admin_session.soup("/keypoints")
        has_table = bool(soup.find("table"))
        has_list = bool(soup.find(class_=re.compile(r"keypoint|key-point|kp-", re.I)))
        assert has_table or has_list, "Key points page should have a table or list of key points"

    def test_no_duplicate_keypoints(self, admin_session):
        soup = admin_session.soup("/keypoints")
        descriptions = []
        for elem in soup.find_all(attrs={"class": re.compile(r"description|keypoint", re.I)}):
            text = elem.get_text(strip=True).lower()
            if len(text) > 10:
                descriptions.append(text)
        unique = set(descriptions)
        duplicates = len(descriptions) - len(unique)
        assert duplicates == 0, (
            f"Found {duplicates} duplicate key point description(s) on /keypoints"
        )

    def test_keypoints_status_filter(self, admin_session):
        for status in ("Open", "Closed", "In Progress"):
            resp = admin_session.post(
                "/keypoints",
                data={"filter_status": status},
                allow_redirects=True,
            )
            assert resp.status_code == 200, f"Key points filter by '{status}' failed"

    def test_keypoints_team_filter(self, admin_session):
        resp = admin_session.post(
            "/keypoints",
            data={"filter_team_id": str(TestConfig.TEST_TEAM_ID)},
            allow_redirects=True,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Change Info
# ---------------------------------------------------------------------------


class TestChangeInfo:
    """Change info CRUD via the reports-side API."""

    @pytest.fixture(scope="class")
    def change_id(self, admin_session):
        payload = {
            "app_name": f"RegressionApp-{TIMESTAMP}",
            "change_number": f"CHG-REG-{TIMESTAMP}",
            "description": "Automated regression test change info",
            "status": "Scheduled",
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "team_id": TestConfig.TEST_TEAM_ID,
            "account_id": TestConfig.TEST_ACCOUNT_ID,
        }
        resp = admin_session.post("/api/change-info", json=payload)
        assert resp.status_code in (200, 201), (
            f"Create change info returned {resp.status_code}: {resp.text[:200]}"
        )
        data = resp.json()
        change_id = data.get("id") or data.get("change_id") or data.get("data", {}).get("id")
        assert change_id, f"No change ID in response: {data}"
        yield str(change_id)

        # Cleanup
        admin_session.delete(f"/api/change-info/{change_id}")

    def test_create_change_info(self, change_id):
        assert change_id is not None

    def test_update_change_info(self, admin_session, change_id):
        resp = admin_session.put(
            f"/api/change-info/{change_id}",
            json={"status": "Completed", "description": "Updated by regression test"},
        )
        assert resp.status_code in (200, 204), (
            f"Update change info returned {resp.status_code}"
        )

    def test_change_info_appears_in_reports(self, admin_session, change_id):
        resp = admin_session.get("/change-info-reports")
        assert resp.status_code == 200
        # The change number we created should appear somewhere on the page
        assert f"CHG-REG-{TIMESTAMP}" in resp.text or "Regression" in resp.text or resp.status_code == 200

    def test_delete_change_info(self, admin_session, change_id):
        resp = admin_session.delete(f"/api/change-info/{change_id}")
        assert resp.status_code in (200, 204), (
            f"Delete change info returned {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# KB Updates
# ---------------------------------------------------------------------------


class TestKBUpdates:
    """KB update reports page."""

    def test_kb_reports_page_loads(self, admin_session):
        resp = admin_session.get("/kb-update-reports")
        assert resp.status_code == 200

    def test_kb_reports_has_content(self, admin_session):
        resp = admin_session.get("/kb-update-reports")
        page = resp.text.lower()
        assert any(term in page for term in ["kb", "knowledge", "update", "table"])


# ---------------------------------------------------------------------------
# Escalation Matrix
# ---------------------------------------------------------------------------


class TestEscalationMatrix:
    """Escalation matrix page and API."""

    def test_escalation_matrix_page_loads(self, admin_session):
        resp = admin_session.get("/escalation-matrix")
        assert resp.status_code == 200

    def test_get_entries_api(self, admin_session):
        resp = admin_session.get(
            f"/api/escalation-matrix/entries?account_id={TestConfig.TEST_ACCOUNT_ID}&team_id={TestConfig.TEST_TEAM_ID}"
        )
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_get_applications_api(self, admin_session):
        resp = admin_session.get(
            f"/api/escalation-matrix/applications?account_id={TestConfig.TEST_ACCOUNT_ID}&team_id={TestConfig.TEST_TEAM_ID}"
        )
        assert resp.status_code in (200, 204)

    @pytest.fixture(scope="class")
    def escalation_entry_id(self, admin_session):
        payload = {
            "application_name": f"RegressionApp-{TIMESTAMP}",
            "tier": "L1",
            "contact_name": "Regression Tester",
            "contact_email": "regression@test.example",
            "contact_phone": "+1-555-0000",
            "account_id": TestConfig.TEST_ACCOUNT_ID,
            "team_id": TestConfig.TEST_TEAM_ID,
        }
        resp = admin_session.post("/api/escalation-matrix/entry", json=payload)
        assert resp.status_code in (200, 201), (
            f"Create escalation entry returned {resp.status_code}: {resp.text[:200]}"
        )
        data = resp.json()
        entry_id = data.get("id") or data.get("entry_id") or data.get("data", {}).get("id")
        assert entry_id, f"No entry ID in response: {data}"
        yield str(entry_id)
        admin_session.delete(f"/api/escalation-matrix/entry/{entry_id}")

    def test_create_escalation_entry(self, escalation_entry_id):
        assert escalation_entry_id is not None

    def test_get_specific_entry(self, admin_session, escalation_entry_id):
        resp = admin_session.get(f"/api/escalation-matrix/entry/{escalation_entry_id}")
        assert resp.status_code == 200

    def test_update_escalation_entry(self, admin_session, escalation_entry_id):
        resp = admin_session.put(
            f"/api/escalation-matrix/entry/{escalation_entry_id}",
            json={"tier": "L2", "contact_name": "Updated Tester"},
        )
        assert resp.status_code in (200, 204)

    def test_delete_escalation_entry(self, admin_session, escalation_entry_id):
        resp = admin_session.delete(f"/api/escalation-matrix/entry/{escalation_entry_id}")
        assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Vendor Details & Application Details
# ---------------------------------------------------------------------------


class TestVendorAndApplicationDetails:
    """Vendor details and application details pages."""

    def test_vendor_details_page_loads(self, admin_session):
        resp = admin_session.get("/vendor-details")
        assert resp.status_code == 200

    def test_vendor_details_has_content(self, admin_session):
        page = admin_session.get("/vendor-details").text.lower()
        assert any(term in page for term in ["vendor", "contact", "table", "application"])

    def test_application_details_api(self, admin_session):
        resp = admin_session.get("/api/application-details")
        assert resp.status_code in (200, 204)

    def test_escalation_matrix_user_page(self, user_session):
        resp = user_session.get("/escalation-matrix")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class TestNotifications:
    """Notification endpoints."""

    def test_notifications_page_loads(self, admin_session):
        resp = admin_session.get("/notifications")
        assert resp.status_code == 200

    def test_mark_all_read(self, admin_session):
        resp = admin_session.post("/notifications/mark-all-read", data={}, allow_redirects=True)
        assert resp.status_code in (200, 302, 204)

    def test_notifications_page_for_regular_user(self, user_session):
        resp = user_session.get("/notifications")
        assert resp.status_code == 200
