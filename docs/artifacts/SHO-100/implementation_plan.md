# Implementation Plan — SHO-100
## Collaborative Incident Management: Duplicate Detection, Polling & Pre-Submit Conflict Resolution

### Context

Multiple NOC engineers can edit the same shift handover form simultaneously. Previously, the incidents section used live keystroke broadcasting with section locks — blocking UX that caused one user to wait while another typed. This feature replaces that approach with an optimistic, non-blocking pattern: duplicate detection on blur, 30-second polling with a refresh badge, and a pre-submit conflict gate. The `DraftIncident` model (`shift_id`, `temp_id`, `incident_id`, `created_by_id`) is the authoritative draft store and already exists in the DB.

**Status: Implementation is complete.** All code was verified present before this plan was written.

---

## Implementation Steps

### Step 1 — Backend: 3 New API Endpoints
**File:** `routes/collaboration.py` (MODIFY — lines 1435–1541)  
**Status:** DONE  
**Components:** COMP-001, COMP-002, COMP-003  
**Satisfies:** REQ-001, REQ-002, REQ-004, REQ-006, REQ-008

| Endpoint | Method | Route | Purpose |
|----------|--------|-------|---------|
| `save_draft_incident` | POST | `/api/collaboration/incident/save` | Upsert DraftIncident by (shift_id, temp_id) for current user |
| `check_incident_duplicate` | GET | `/api/collaboration/incident/check` | Query other users' drafts for matching incident_id |
| `get_others_incidents` | GET | `/api/collaboration/incidents/others` | Return all other users' DraftIncidents for a shift |

Key implementation details:
- Ownership check: 403 if `draft.created_by_id != current_user.id`
- Duplicate check excludes current user (`created_by_id != current_user.id`)
- Returns `added_by` display_name for attribution in inline warning
- All endpoints wrapped in try/except with db.session.rollback() on error

**Verify:** `curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000/api/collaboration/incident/check?shift_id=1&incident_id=X"` → 302

---

### Step 2 — Frontend: Live Sync Removal + Polling Engine
**File:** `templates/partials/collaborative_handover.html` (MODIFY — lines 160–180, 498–685)  
**Status:** DONE  
**Components:** COMP-004, COMP-005  
**Satisfies:** REQ-003, REQ-004, REQ-007

- Removed `#incidents-container` from `observeDynamicEntries()` — live keystroke broadcast for incidents removed (REQ-007)
- Filtered incident inputs out of `setupLiveInputTracking()`
- `startIncidentPolling(shiftId)` called after session join (line 172)
- `stopIncidentPolling()` called on session disconnect (line 668)
- `let _knownOtherTempIds = new Set()` — tracks already-shown temp_ids
- New: `startIncidentPolling`, `seedKnownIncidents`, `stopIncidentPolling`, `pollForOthersIncidents`, `loadOthersIncidents`, `appendOthersIncident`

---

### Step 3 — Frontend: Handover Form (Badge, Blur Handlers, Conflict Modal)
**File:** `templates/handover_form.html` (MODIFY — lines 718–740, 1280–1295, 2383–2415, 3915–3930, 5060–5250)  
**Status:** DONE  
**Components:** COMP-006, COMP-007, COMP-008, COMP-009, COMP-010  
**Satisfies:** REQ-001, REQ-002, REQ-005, REQ-006, REQ-010

- Refresh badge: `#collab-incident-refresh-badge` with `style="display:none"` (not `d-none`)
- DOMContentLoaded wires blur events to existing carryforward incident rows
- `addUnifiedIncident()` assigns `dataset.collabTempId` and `onblur="checkIncidentDuplicate(this)"`
- Submit handler made `async`; gates on `await validateIncidentDuplicatesBeforeSubmit()`
- New functions: `generateIncidentTempId`, `checkIncidentDuplicate`, `clearIncidentDuplicateWarning`, `saveDraftIncident`, `validateIncidentDuplicatesBeforeSubmit`, `showIncidentConflictModal`
- All functions guarded by `if (!window.collabInstance || !window.collabInstance.isConnected) return;`

---

### Step 4 — Draft Cleanup on Submit (Pre-existing)
**File:** `routes/handover.py` (READ-ONLY VERIFY — lines 2139–2145)  
**Status:** ALREADY PRESENT  
**Components:** COMP-011  
**Satisfies:** REQ-008

```python
deleted_incidents = DraftIncident.query.filter_by(shift_id=shift_id).delete()
```

---

## Pre-Implementation Baseline

| Check | Result |
|-------|--------|
| All 3 endpoints registered under `/api/collaboration` | Verified |
| `_knownOtherTempIds` seeded before first poll | Verified |
| Incidents excluded from `observeDynamicEntries()` | Verified |
| Refresh badge uses `style="display:none"` not `d-none` | Verified |
| Submit handler is `async` | Verified |
| Draft cleanup at handover submit | Verified |
| Session guard on all client-side collab functions | Verified |

---

## Verification Plan

### Manual Tests

**TC-1 (REQ-010):** Open handover form without Collaborate → enter Incident ID, blur → Network tab shows zero calls to `/api/collaboration/incident/*` → Submit → no conflict modal.

**TC-2 (REQ-001):** User A joins collab, enters `INC001`, blurs. User B joins same session, enters `INC001`, blurs → User B sees inline warning with User A's name.

**TC-3 (REQ-003/004/005):** User A joins. User B adds incident row, enters ID, blurs. Within 30s User A's badge shows "1 new incidents added". User A clicks → row appended with purple border + attribution.

**TC-4 (REQ-006):** Both users have `INC001`. User B submits → conflict modal. "Go Back" → blocked. "Submit Anyway" → proceeds.

**TC-5 (REQ-008):** After submission: `SELECT * FROM draft_incident WHERE shift_id=X` → empty.

### Regression Tests

```bash
pytest tests/test_application.py -v
python3 tests/run_tests.py --url http://localhost:5000 --user superadmin --password $TEST_SUPERADMIN_PASSWORD --verbose
```

---

## Pipeline Continuation

**Next phases:** simplify → review → verification → pr  
**Branch:** `SHO-100-collab-incident-mgmt`  

**Modified files:**
1. `routes/collaboration.py` — 3 new endpoints (lines 1435–1541)
2. `templates/partials/collaborative_handover.html` — polling engine (lines 160–180, 498–685)
3. `templates/handover_form.html` — badge, blur handlers, conflict modal (lines 718–740, 1280–1295, 2383–2415, 3915–3930, 5060–5250)

**Security note for review phase:** Verify `escapeHtml()` is called on `added_by` attribution strings before DOM insertion to prevent XSS.
