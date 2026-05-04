"""
Regression tests — Collaborative Editing

Covers the DB-polling collaboration layer used when multiple engineers
co-edit a handover draft simultaneously.

Routes exercised:
  POST /session/join/<shift_id>
  POST /session/heartbeat/<shift_id>
  POST /session/leave/<shift_id>
  POST /lock/acquire
  POST /lock/release
  POST /incident/add  (draft incident)
  POST /keypoint/add  (draft key point)
  GET  /stream/<shift_id>  (SSE — just verify it starts, don't consume)
  POST /sync/<shift_id>    (if available)

All tests require a real draft shift to collaborate on.
If no draft exists the fixture creates one and cleans it up afterwards.
"""
import re
from datetime import date, datetime

import pytest

from tests.config import TestConfig

TIMESTAMP = datetime.now().strftime("%H%M%S")


# ---------------------------------------------------------------------------
# Fixture: a live draft shift to collaborate on
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def collab_shift_id(admin_session):
    """Create a draft shift, yield its ID, then clean up."""
    token, _ = admin_session.csrf_for_path("/handover")
    resp = admin_session.post(
        "/handover",
        data={
            "csrf_token": token,
            "action": "save_draft",
            "handover_date": date.today().isoformat(),
            "current_shift_type": "Morning",
            "next_shift_type": "Evening",
            "additional_notes": f"COLLAB-TEST-{TIMESTAMP}",
        },
        allow_redirects=True,
    )
    assert resp.status_code == 200, f"Draft creation for collab tests returned {resp.status_code}"

    drafts_resp = admin_session.get("/handover/drafts")
    ids = re.findall(r"/handover/edit/(\d+)", drafts_resp.text)
    assert ids, "No draft found after creation for collab tests"
    shift_id = int(ids[0])

    yield shift_id

    admin_session.post(f"/api/delete-draft/{shift_id}", data={}, allow_redirects=True)


# ---------------------------------------------------------------------------
# Session join / leave / heartbeat
# ---------------------------------------------------------------------------


class TestCollaborationSession:

    def test_join_session_returns_json(self, admin_session, collab_shift_id):
        resp = admin_session.post(
            f"/session/join/{collab_shift_id}",
            json={"section": "incidents"},
        )
        assert resp.status_code in (200, 201, 409), (
            f"join_session returned {resp.status_code}: {resp.text[:200]}"
        )
        if resp.status_code in (200, 201):
            assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_heartbeat_keeps_session_alive(self, admin_session, collab_shift_id):
        # Join first to ensure a session exists
        admin_session.post(f"/session/join/{collab_shift_id}", json={})

        resp = admin_session.post(
            f"/session/heartbeat/{collab_shift_id}",
            json={},
        )
        assert resp.status_code in (200, 204), (
            f"heartbeat returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_leave_session(self, admin_session, collab_shift_id):
        admin_session.post(f"/session/join/{collab_shift_id}", json={})

        resp = admin_session.post(
            f"/session/leave/{collab_shift_id}",
            json={},
        )
        assert resp.status_code in (200, 204), (
            f"leave_session returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_join_nonexistent_shift_returns_error(self, admin_session):
        resp = admin_session.post("/session/join/999999999", json={})
        assert resp.status_code in (404, 400, 403), (
            f"Joining non-existent shift should return 4xx, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Section Locking
# ---------------------------------------------------------------------------


class TestSectionLocking:

    def test_acquire_lock(self, admin_session, collab_shift_id):
        resp = admin_session.post(
            "/lock/acquire",
            json={"shift_id": collab_shift_id, "section": "incidents"},
        )
        assert resp.status_code in (200, 201, 409), (
            f"lock/acquire returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_release_lock(self, admin_session, collab_shift_id):
        # Acquire first
        admin_session.post(
            "/lock/acquire",
            json={"shift_id": collab_shift_id, "section": "key_points"},
        )
        resp = admin_session.post(
            "/lock/release",
            json={"shift_id": collab_shift_id, "section": "key_points"},
        )
        assert resp.status_code in (200, 204), (
            f"lock/release returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_lock_extend(self, admin_session, collab_shift_id):
        admin_session.post(
            "/lock/acquire",
            json={"shift_id": collab_shift_id, "section": "change_info"},
        )
        resp = admin_session.post(
            "/lock/extend",
            json={"shift_id": collab_shift_id, "section": "change_info"},
        )
        assert resp.status_code in (200, 204, 404), (
            f"lock/extend returned {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Draft Incident CRUD via collaboration API
# ---------------------------------------------------------------------------


class TestDraftIncidentCollaboration:

    @pytest.fixture(scope="class")
    def draft_incident_id(self, admin_session, collab_shift_id):
        resp = admin_session.post(
            "/incident/add",
            json={
                "shift_id": collab_shift_id,
                "incident_type": "open",
                "title": f"COLLAB-INC-{TIMESTAMP}",
                "description": "Regression collaboration incident",
                "status": "Open",
            },
        )
        assert resp.status_code in (200, 201), (
            f"incident/add returned {resp.status_code}: {resp.text[:200]}"
        )
        data = resp.json()
        inc_id = data.get("id") or data.get("incident_id") or data.get("data", {}).get("id")
        assert inc_id, f"No incident ID returned: {data}"
        yield inc_id

    def test_add_draft_incident(self, draft_incident_id):
        assert draft_incident_id is not None

    def test_update_draft_incident(self, admin_session, collab_shift_id, draft_incident_id):
        resp = admin_session.post(
            "/incident/update",
            json={
                "incident_id": draft_incident_id,
                "shift_id": collab_shift_id,
                "title": f"COLLAB-INC-{TIMESTAMP}-updated",
                "status": "In Progress",
            },
        )
        assert resp.status_code in (200, 204), (
            f"incident/update returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_delete_draft_incident(self, admin_session, collab_shift_id, draft_incident_id):
        resp = admin_session.post(
            "/incident/delete",
            json={"incident_id": draft_incident_id, "shift_id": collab_shift_id},
        )
        assert resp.status_code in (200, 204), (
            f"incident/delete returned {resp.status_code}: {resp.text[:200]}"
        )


# ---------------------------------------------------------------------------
# Draft Key Point CRUD via collaboration API
# ---------------------------------------------------------------------------


class TestDraftKeyPointCollaboration:

    @pytest.fixture(scope="class")
    def draft_kp_id(self, admin_session, collab_shift_id):
        resp = admin_session.post(
            "/keypoint/add",
            json={
                "shift_id": collab_shift_id,
                "description": f"COLLAB-KP-{TIMESTAMP}",
                "status": "Open",
                "jira_id": f"KP-REG-{TIMESTAMP}",
            },
        )
        assert resp.status_code in (200, 201), (
            f"keypoint/add returned {resp.status_code}: {resp.text[:200]}"
        )
        data = resp.json()
        kp_id = data.get("id") or data.get("keypoint_id") or data.get("data", {}).get("id")
        assert kp_id, f"No keypoint ID returned: {data}"
        yield kp_id

    def test_add_draft_keypoint(self, draft_kp_id):
        assert draft_kp_id is not None

    def test_update_draft_keypoint(self, admin_session, collab_shift_id, draft_kp_id):
        resp = admin_session.post(
            "/keypoint/update",
            json={
                "keypoint_id": draft_kp_id,
                "shift_id": collab_shift_id,
                "description": f"COLLAB-KP-{TIMESTAMP}-updated",
                "status": "In Progress",
            },
        )
        assert resp.status_code in (200, 204), (
            f"keypoint/update returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_delete_draft_keypoint(self, admin_session, collab_shift_id, draft_kp_id):
        resp = admin_session.post(
            "/keypoint/delete",
            json={"keypoint_id": draft_kp_id, "shift_id": collab_shift_id},
        )
        assert resp.status_code in (200, 204), (
            f"keypoint/delete returned {resp.status_code}: {resp.text[:200]}"
        )


# ---------------------------------------------------------------------------
# SSE Stream (smoke test only — don't consume the stream)
# ---------------------------------------------------------------------------


class TestEventStream:

    def test_stream_endpoint_is_reachable(self, admin_session, collab_shift_id):
        """Verify the SSE stream endpoint opens without error (don't read the stream)."""
        resp = admin_session.session.get(
            f"{admin_session.base_url}/stream/{collab_shift_id}",
            stream=True,
            timeout=5,
        )
        # 200 with text/event-stream, or 404 if collaboration tables don't exist yet
        assert resp.status_code in (200, 404), (
            f"SSE stream endpoint returned {resp.status_code}"
        )
        if resp.status_code == 200:
            ct = resp.headers.get("Content-Type", "")
            assert "text/event-stream" in ct or "text/" in ct, (
                f"SSE stream should return text/event-stream, got {ct}"
            )
        resp.close()
