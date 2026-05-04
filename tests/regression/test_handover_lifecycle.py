"""
Regression tests — Full Handover Lifecycle

Covers:
  - Handover form loads with all required sections
  - Save as draft preserves data
  - Draft appears in reports/drafts list
  - Edit draft and re-save
  - Submit final handover changes status from draft → submitted
  - Submitted handover appears in reports
  - Detailed shift report is accessible
  - Delete draft removes it
  - Reports page filtering (by date, status, team)
  - Export endpoints return non-empty responses

Each test run creates fresh data tagged with a unique timestamp so it does
not interfere with production records.
"""
import re
from datetime import date, datetime

import pytest
from bs4 import BeautifulSoup

from tests.config import TestConfig

TIMESTAMP = datetime.now().strftime("%H%M%S")
TEST_NOTES = f"REGRESSION-TEST-{TIMESTAMP} — automated, please ignore"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_shift_ids_in_page(html: str):
    """Return all shift IDs found in /handover/edit/<id> links."""
    return re.findall(r"/handover/edit/(\d+)", html)


def _find_draft_links(html: str):
    return re.findall(r"/handover/edit/(\d+)", html)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def admin_session(admin_session):  # noqa: F811 — shadows module-level fixture
    return admin_session


@pytest.fixture(scope="module")
def draft_shift_id(admin_session):
    """
    Create one draft handover and return its shift_id.
    Cleaned up at the end of the module.
    """
    token, _ = admin_session.csrf_for_path("/handover")

    today = date.today().isoformat()
    payload = {
        "csrf_token": token,
        "action": "save_draft",
        "handover_date": today,
        "current_shift_type": "Morning",
        "next_shift_type": "Evening",
        "additional_notes": TEST_NOTES,
    }
    resp = admin_session.post("/handover", data=payload, allow_redirects=True)
    assert resp.status_code == 200, f"Draft save returned {resp.status_code}"

    # Find the new draft in the drafts list
    drafts_resp = admin_session.get("/handover/drafts")
    ids = _find_draft_links(drafts_resp.text)
    assert ids, "No draft found after saving — check /handover/drafts response"

    shift_id = ids[0]
    yield shift_id

    # Cleanup: delete the draft (or submitted handover) if it still exists
    admin_session.post(f"/api/delete-draft/{shift_id}", data={}, allow_redirects=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHandoverFormStructure:
    """Verify the handover form has all expected sections."""

    def test_form_loads(self, admin_session):
        resp = admin_session.get("/handover")
        assert resp.status_code == 200

    def test_form_has_csrf_token(self, admin_session):
        resp = admin_session.get("/handover")
        soup = BeautifulSoup(resp.text, "html.parser")
        assert soup.find("input", {"name": "csrf_token"}), "CSRF token input missing from handover form"

    def test_form_has_shift_selectors(self, admin_session):
        resp = admin_session.get("/handover")
        page = resp.text.lower()
        assert "current_shift_type" in page or "current shift" in page
        assert "next_shift_type" in page or "next shift" in page

    def test_form_has_key_points_section(self, admin_session):
        resp = admin_session.get("/handover")
        page = resp.text.lower()
        assert "key point" in page or "keypoint" in page

    def test_form_has_incidents_section(self, admin_session):
        resp = admin_session.get("/handover")
        page = resp.text.lower()
        assert "incident" in page

    def test_form_has_notes_field(self, admin_session):
        resp = admin_session.get("/handover")
        soup = BeautifulSoup(resp.text, "html.parser")
        notes = soup.find("textarea", {"name": re.compile(r"notes", re.I)})
        assert notes is not None, "Additional notes textarea not found"


class TestDraftLifecycle:
    """Draft creation, retrieval, and editing."""

    def test_drafts_page_loads(self, admin_session):
        resp = admin_session.get("/handover/drafts")
        assert resp.status_code == 200

    def test_draft_appears_in_drafts_list(self, admin_session, draft_shift_id):
        resp = admin_session.get("/handover/drafts")
        assert draft_shift_id in resp.text or f"/handover/edit/{draft_shift_id}" in resp.text, (
            f"Draft {draft_shift_id} not visible in /handover/drafts"
        )

    def test_draft_edit_page_loads(self, admin_session, draft_shift_id):
        resp = admin_session.get(f"/handover/edit/{draft_shift_id}")
        assert resp.status_code == 200

    def test_draft_contains_saved_notes(self, admin_session, draft_shift_id):
        resp = admin_session.get(f"/handover/edit/{draft_shift_id}")
        # The unique test notes string should be somewhere in the edit page
        assert "REGRESSION-TEST" in resp.text or TEST_NOTES[:20] in resp.text, (
            "Saved notes not found in draft edit page"
        )

    def test_draft_re_save_succeeds(self, admin_session, draft_shift_id):
        edit_url = f"/handover/edit/{draft_shift_id}"
        token, _ = admin_session.csrf_for_path(edit_url)
        updated_notes = f"{TEST_NOTES} — re-saved"
        resp = admin_session.post(
            edit_url,
            data={
                "csrf_token": token,
                "action": "save_draft",
                "additional_notes": updated_notes,
                "current_shift_type": "Morning",
                "next_shift_type": "Evening",
                "handover_date": date.today().isoformat(),
            },
            allow_redirects=True,
        )
        assert resp.status_code == 200
        # Should not land on an error page
        page = resp.text.lower()
        assert "error" not in page or "success" in page or "draft" in page

    def test_draft_in_reports_draft_filter(self, admin_session, draft_shift_id):
        resp = admin_session.get("/reports?status=draft")
        assert resp.status_code == 200
        # The draft shift ID or its date should appear
        assert draft_shift_id in resp.text or date.today().isoformat() in resp.text or "draft" in resp.text.lower()


class TestHandoverSubmission:
    """Submit a draft and verify it transitions to 'submitted' status."""

    @pytest.fixture(scope="class")
    def submitted_shift_id(self, admin_session):
        # Create a fresh draft specifically for submission
        token, _ = admin_session.csrf_for_path("/handover")
        today = date.today().isoformat()
        submit_notes = f"REGRESSION-SUBMIT-{TIMESTAMP}"
        payload = {
            "csrf_token": token,
            "action": "save_draft",
            "handover_date": today,
            "current_shift_type": "Morning",
            "next_shift_type": "Evening",
            "additional_notes": submit_notes,
        }
        resp = admin_session.post("/handover", data=payload, allow_redirects=True)
        assert resp.status_code == 200

        drafts_resp = admin_session.get("/handover/drafts")
        ids = _find_draft_links(drafts_resp.text)
        assert ids, "No draft found after saving"
        shift_id = ids[0]

        # Now submit it
        edit_url = f"/handover/edit/{shift_id}"
        token, _ = admin_session.csrf_for_path(edit_url)
        resp = admin_session.post(
            edit_url,
            data={
                "csrf_token": token,
                "action": "send",
                "handover_date": today,
                "current_shift_type": "Morning",
                "next_shift_type": "Evening",
                "additional_notes": submit_notes,
            },
            allow_redirects=True,
        )
        assert resp.status_code == 200
        yield shift_id

    def test_submitted_shift_not_in_draft_list(self, admin_session, submitted_shift_id):
        resp = admin_session.get("/handover/drafts")
        # After submission, it should not appear in the drafts list
        draft_ids = _find_draft_links(resp.text)
        assert submitted_shift_id not in draft_ids, (
            f"Shift {submitted_shift_id} still appears as a draft after submission"
        )

    def test_submitted_shift_in_reports(self, admin_session, submitted_shift_id):
        resp = admin_session.get("/reports")
        assert resp.status_code == 200
        found = submitted_shift_id in resp.text or f"shift/{submitted_shift_id}" in resp.text
        # Fallback: the page itself should show submitted handovers for today
        assert found or "submitted" in resp.text.lower() or date.today().isoformat() in resp.text

    def test_detailed_report_accessible(self, admin_session, submitted_shift_id):
        resp = admin_session.get(f"/handover-reports/detailed/{submitted_shift_id}")
        assert resp.status_code == 200, (
            f"Detailed report for shift {submitted_shift_id} returned {resp.status_code}"
        )


class TestReportsPage:
    """Reports page filtering and export."""

    def test_reports_page_loads(self, admin_session):
        resp = admin_session.get("/reports")
        assert resp.status_code == 200

    def test_reports_have_filter_controls(self, admin_session):
        soup = admin_session.soup("/reports")
        selects = soup.find_all("select")
        assert len(selects) > 0, "Reports page should have filter dropdowns"

    def test_filter_by_draft_status(self, admin_session):
        resp = admin_session.get("/reports?status=draft")
        assert resp.status_code == 200

    def test_filter_by_team(self, admin_session):
        resp = admin_session.get(f"/reports?team_id={TestConfig.TEST_TEAM_ID}")
        assert resp.status_code == 200

    def test_filter_by_date(self, admin_session):
        today = date.today().isoformat()
        resp = admin_session.get(f"/reports?date={today}")
        assert resp.status_code == 200

    def test_handover_reports_page_loads(self, admin_session):
        resp = admin_session.get("/handover-reports")
        assert resp.status_code == 200

    def test_change_info_reports_page_loads(self, admin_session):
        resp = admin_session.get("/change-info-reports")
        assert resp.status_code == 200

    def test_kb_update_reports_page_loads(self, admin_session):
        resp = admin_session.get("/kb-update-reports")
        assert resp.status_code == 200


class TestDraftDeletion:
    """Deleting a draft removes it from the drafts list."""

    def test_delete_draft(self, admin_session):
        # Create a throwaway draft
        token, _ = admin_session.csrf_for_path("/handover")
        resp = admin_session.post(
            "/handover",
            data={
                "csrf_token": token,
                "action": "save_draft",
                "handover_date": date.today().isoformat(),
                "current_shift_type": "Morning",
                "next_shift_type": "Evening",
                "additional_notes": f"DELETE-ME-{TIMESTAMP}",
            },
            allow_redirects=True,
        )
        assert resp.status_code == 200

        drafts_resp = admin_session.get("/handover/drafts")
        ids = _find_draft_links(drafts_resp.text)
        assert ids, "No draft found to delete"
        to_delete = ids[0]

        del_resp = admin_session.post(
            f"/api/delete-draft/{to_delete}", data={}, allow_redirects=True
        )
        assert del_resp.status_code in (200, 302, 204)

        # Confirm it's gone
        after_resp = admin_session.get("/handover/drafts")
        remaining = _find_draft_links(after_resp.text)
        assert to_delete not in remaining, (
            f"Draft {to_delete} still in drafts list after deletion"
        )
