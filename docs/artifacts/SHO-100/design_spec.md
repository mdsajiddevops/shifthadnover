# Design Specification — SHO-100

## Meta

| Field | Value |
|-------|-------|
| feature_id | FEAT-0100 |
| ticket | SHO-100 |
| title | Collaborative Incident Management — Duplicate Detection, Polling & Pre-Submit Conflict Resolution |
| date | 2026-05-08 |
| author | Sajid Mohammad |
| version | v1 |
| status | ready_for_implementation |
| ready_for_implementation | true |

---

## Problem Spec Reference

`docs/artifacts/SHO-100/problem_spec.md` — 10 requirements (REQ-001–REQ-010), 15 acceptance criteria, 4 non-goals, 5 edge cases.

Key constraints driving the design:
- Single Gunicorn worker — no shared in-memory state across processes
- No WebSockets — SSE for push, polling for pull
- `DraftIncident` model schema is fixed (`shift_id`, `temp_id`, `incident_id`, `created_by_id`)
- Collaboration features activate only when an SSE session is established

---

## Current Architecture

### Existing collaboration subsystem (before this feature)

| Component | File | Role |
|-----------|------|------|
| Collaboration blueprint | `routes/collaboration.py` | API endpoints for draft persistence, SSE streams |
| SSE stream | `routes/collab_sse.py` | Per-user event push |
| Collaboration partial | `templates/partials/collaborative_handover.html` | Client-side collab JS initialisation |
| Handover form | `templates/handover_form.html` | Main form (incidents, key points, sections) |
| DraftIncident model | `models/collaboration.py:292–355` | DB draft store for incident rows |
| DraftKeyPoint model | `models/collaboration.py:358+` | DB draft store for key points |

### Pre-feature incident sync behaviour (REMOVED by this feature)

The incident section previously participated in `observeDynamicEntries()` which broadcast every keystroke to other users via SSE. This created exclusive editing locks and blocking UX. **REQ-007** requires removing this live sync for incidents only.

### Modification points identified

| Location | What changes |
|----------|-------------|
| `routes/collaboration.py` | Add 3 new endpoints (incident save, duplicate check, others list) |
| `templates/partials/collaborative_handover.html` | Remove incidents from live sync; add polling functions |
| `templates/handover_form.html` | Add temp-id generation, blur handlers, refresh badge, conflict modal |
| `routes/handover.py:2139` | DraftIncident cleanup on submit — already present (REQ-008 satisfied) |

---

## Architecture

### Pattern: Optimistic Collaboration with Polling

The feature uses an **optimistic, non-blocking** pattern rather than the previous pessimistic locking approach:

1. Users edit incidents freely with no locks or live propagation
2. On blur of Incident ID field: save draft + check for duplicates (fire-and-forget on errors)
3. Background 30-second poll shows a badge when teammates add new incidents
4. Pre-submit gate fires one final duplicate check before `form.submit()`

### Component Map

| COMP-ID | Name | File | Responsibility |
|---------|------|------|----------------|
| COMP-001 | Draft Save Endpoint | `routes/collaboration.py` | `POST /api/collaboration/incident/save` — upsert DraftIncident by (shift_id, temp_id) for current user |
| COMP-002 | Duplicate Check Endpoint | `routes/collaboration.py` | `GET /api/collaboration/incident/check` — query other users' DraftIncidents for matching incident_id |
| COMP-003 | Others List Endpoint | `routes/collaboration.py` | `GET /api/collaboration/incidents/others` — return all DraftIncidents for shift not owned by current user |
| COMP-004 | Polling Engine | `templates/partials/collaborative_handover.html` | `startIncidentPolling()` / `stopIncidentPolling()` — 30-second interval calling COMP-003 |
| COMP-005 | Seed Known Incidents | `templates/partials/collaborative_handover.html` | `seedKnownIncidents()` — one-time call on session join to populate `_knownOtherTempIds` |
| COMP-006 | Refresh Badge | `templates/handover_form.html` | `#collab-incident-refresh-badge` button; shows count of unseen teammates' incidents |
| COMP-007 | Blur Handler | `templates/handover_form.html` | `checkIncidentDuplicate(input)` + `saveDraftIncident(row, shiftId)` triggered on Incident ID blur |
| COMP-008 | TempId Generator | `templates/handover_form.html` | `generateIncidentTempId()` — client-side stable row identifier |
| COMP-009 | Pre-Submit Conflict Gate | `templates/handover_form.html` | `validateIncidentDuplicatesBeforeSubmit()` — async call to COMP-002 for all Incident IDs |
| COMP-010 | Conflict Modal | `templates/handover_form.html` | `showIncidentConflictModal(conflicts)` — modal with "Submit Anyway" / "Go Back & Review" |
| COMP-011 | Draft Cleanup | `routes/handover.py:2139` | `DraftIncident.query.filter_by(shift_id=...).delete()` — already present, fires on submit |

### Feature Guard Pattern

All client-side collaboration functions are guarded by:

```
window.collabInstance && window.collabInstance.isConnected
```

When no SSE session is active, no API calls are made and no collaboration UI renders. This satisfies REQ-010 and AC-015.

### Collaboration Session Lifecycle

```
User joins SSE session
  └─► initializeCollaborationV2() called
        ├─► seedKnownIncidents(shiftId)   [COMP-005: populates _knownOtherTempIds silently]
        └─► startIncidentPolling(shiftId) [COMP-004: begins 30s interval after seed completes]

Every 30 seconds:
  └─► pollForOthersIncidents(shiftId)
        ├─► GET /api/collaboration/incidents/others?shift_id=X
        ├─► Filters out _knownOtherTempIds
        └─► If new found: increment badge counter

User clicks refresh badge:
  └─► loadOthersIncidents()
        ├─► GET /api/collaboration/incidents/others?shift_id=X
        ├─► appendOthersIncident() for each new incident
        └─► Reset badge to zero, hide badge

User types in Incident ID field, then blurs:
  └─► checkIncidentDuplicate(input)       [COMP-007]
        ├─► saveDraftIncident(row, shiftId) [fire-and-forget]
        └─► GET /api/collaboration/incident/check?shift_id=X&incident_id=Y
              ├─► If duplicate: show inline warning with attribution
              └─► If not / on error: no UI change

User clicks Submit:
  └─► validateIncidentDuplicatesBeforeSubmit() [COMP-009, async]
        ├─► Collects all non-empty incident_id[] values
        ├─► GET /api/collaboration/incident/check for each
        ├─► If any conflicts: showIncidentConflictModal(conflicts) [COMP-010]
        │     ├─► "Submit Anyway" → form.submit()
        │     └─► "Go Back & Review" / close → return false (block submit)
        └─► If no conflicts: form.submit() proceeds immediately

User disconnects SSE session:
  └─► stopIncidentPolling() [COMP-004]
        └─► clearInterval(_incidentPollTimer)
```

---

## API Contracts

### POST /api/collaboration/incident/save

**Auth:** `@login_required`  
**Blueprint:** `collaboration_bp` (`/api/collaboration`)  
**Purpose:** Upsert a DraftIncident record for the current user's incident row.

**Request Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| shift_id | integer | yes | Shift database PK |
| temp_id | string | yes | Client-generated stable row identifier (max 64 chars) |
| incident_id | string | no | Incident ID value (e.g. "INC001") |
| app_name | string | no | Application name |
| title | string | no | Incident title |
| status | string | no | Incident type (Open/Closed/Priority/Handover/Escalated) |
| priority | string | no | Incident priority |
| assigned_to | string | no | Assignee name |
| escalated_to | string | no | Escalation target |
| notes | string | no | Free-text description |

**Responses:**

| Status | Body | Condition |
|--------|------|-----------|
| 200 | `{"success": true, "temp_id": "<temp_id>"}` | Upsert succeeded |
| 400 | `{"success": false, "error": "Missing shift_id or temp_id"}` | Missing required params |
| 403 | `{"success": false, "error": "Not your incident"}` | Attempt to update another user's draft |
| 404 | Flask 404 | shift_id not found |
| 500 | `{"success": false, "error": "<message>"}` | DB error (rollback performed) |

**Upsert logic:** If a DraftIncident with `(shift_id, temp_id)` exists and `created_by_id == current_user.id`, update the fields. If it doesn't exist, create it. Ownership check prevents cross-user tampering.

---

### GET /api/collaboration/incident/check

**Auth:** `@login_required`  
**Blueprint:** `collaboration_bp`  
**Purpose:** Check if another user has already entered the same Incident ID for this shift.

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| shift_id | integer | yes | Shift database PK |
| incident_id | string | yes | Incident ID to check |

**Responses:**

| Status | Body | Condition |
|--------|------|-----------|
| 200 | `{"success": true, "duplicate": false}` | No other user has this ID |
| 200 | `{"success": true, "duplicate": true, "added_by": "<name>", "added_by_id": <int>}` | Duplicate found |
| 400 | `{"success": false, "error": "Missing params"}` | Missing shift_id or incident_id |

**Query:** `SELECT * FROM draft_incident WHERE shift_id=? AND incident_id=? AND created_by_id != ?` (current user excluded). Returns first match only.

**Performance:** Single indexed lookup on `idx_draft_incident_shift` + `incident_id` equality filter. Meets REQ-009 (sub-500ms at p95).

---

### GET /api/collaboration/incidents/others

**Auth:** `@login_required`  
**Blueprint:** `collaboration_bp`  
**Purpose:** Retrieve all draft incidents entered by other users for a shift (used by polling and refresh).

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| shift_id | integer | yes | Shift database PK |

**Responses:**

| Status | Body | Condition |
|--------|------|-----------|
| 200 | `{"success": true, "incidents": [...], "count": <int>}` | Success |
| 400 | `{"success": false, "error": "Missing shift_id"}` | Missing param |

**Incident object fields:** `id`, `shift_id`, `temp_id`, `incident_type`, `app_name`, `incident_id`, `title`, `description`, `priority`, `status`, `assigned_to`, `escalated_to`, `resolution`, `created_by_id`, `created_by_name`, `created_at`, `updated_by_id`, `updated_by_name`, `updated_at`, `version` (from `DraftIncident.to_dict()`).

---

## Data Models

### DraftIncident (`models/collaboration.py:292`)

**Table:** `draft_incident`  
**Schema is fixed — no changes required for this feature.**

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | Integer | PK, auto-increment | |
| shift_id | Integer | FK → shift.id, NOT NULL, INDEX | Scopes drafts to a shift |
| temp_id | String(64) | NOT NULL | Client-generated; stable per row |
| incident_type | String(32) | NOT NULL | Maps to status dropdown |
| app_name | String(128) | nullable | |
| incident_id | String(64) | nullable | The canonical ID checked for duplicates |
| title | String(256) | nullable | |
| description | Text | nullable | |
| priority | String(32) | nullable | |
| status | String(32) | nullable | |
| assigned_to | String(128) | nullable | |
| escalated_to | String(128) | nullable | |
| resolution | Text | nullable | |
| created_by_id | Integer | FK → user.id, NOT NULL | Ownership |
| created_at | DateTime | default=utcnow | |
| updated_by_id | Integer | FK → user.id, nullable | |
| updated_at | DateTime | onupdate=utcnow | |
| version | Integer | default=1 | Incremented on each update |

**Unique constraint:** `uq_draft_incident (shift_id, temp_id)` — prevents duplicate temp_ids per shift.  
**Index:** `idx_draft_incident_shift (shift_id)` — fast lookup for all drafts in a shift.

### Client-side State

| Variable | Location | Type | Purpose |
|----------|----------|------|---------|
| `_knownOtherTempIds` | `collaborative_handover.html:501` | `Set<string>` | Tracks already-displayed teammates' temp_ids; prevents badge spuriousness |
| `_incidentPollTimer` | `collaborative_handover.html` | `number\|null` | `setInterval` handle; cleared on session disconnect |
| `row.dataset.collabTempId` | DOM attribute on incident rows | string | Per-row temp_id assigned at row creation or form load |

### TempId Format

`'inc_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7)`

Example: `inc_1715191234567_k3a9z` — collision probability negligible for session-lifetime uniqueness.

---

## Decisions (ADRs)

### ADR-001: Optimistic Non-Blocking Pattern Over Pessimistic Locking

**Status:** Accepted  
**Context:** The previous incident sync used field-level keystroke broadcasting with section locks. This blocked User 2 from entering any incident while User 1 was typing, causing UX complaints and race conditions.

**Decision:** Replace with optimistic concurrency — no locks, no live propagation. Each user edits freely. Duplicate detection fires on blur (point-in-time check), not continuously.

**Alternatives considered:**
1. **Pessimistic locking (status quo)** — Row-level locks while a user is in the field. Rejected: blocking UX; lock cleanup on disconnect is fragile.
2. **CRDT-based merging (YJS)** — YJS is already self-hosted for other sections. Rejected: incidents are semantically distinct records (not collaborative text); auto-merge risks combining two engineers' separate incidents into one corrupted row.
3. **Optimistic with polling (chosen)** — No locks, point-in-time duplicate detection, periodic badge for visibility.

**Consequences:** Two users can still submit the same incident if both ignore the inline warning and the conflict modal. This is a deliberate design choice (see NG-002 in problem_spec.md) — the user retains agency.

---

### ADR-002: Draft Cleanup on Submission (Existing Pattern Reused)

**Status:** Accepted  
**Context:** REQ-008 requires deleting all DraftIncidents for a shift on successful submission.

**Decision:** Reuse the existing `DraftIncident.query.filter_by(shift_id=shift_id).delete()` at `routes/handover.py:2139`. No new code needed.

**Alternatives considered:**
1. **Cascade delete via FK** — Would clean up automatically but requires schema change (out of scope per constraint in problem_spec.md).
2. **Async cleanup via Celery** — Adds latency and complexity. The synchronous delete at submit time is simpler and already present.

**Consequences:** If two users submit simultaneously, the second cleanup finds no rows and completes silently (EC-003 in problem_spec.md). Acceptable.

---

### ADR-003: shift_id Source on Client Side

**Status:** Accepted  
**Context:** The duplicate check and draft save endpoints require `shift_id`. The handover form's `<form action>` URL contains the shift_id, but there is no hidden `<input id="shift_id">` field.

**Decision:** Read `window.collabInstance.shiftId` — the collaboration instance always carries the shift_id and is available when the feature is active.

**Alternatives considered:**
1. **Parse from `window.location.pathname`** — Fragile; URL structure could change.
2. **Add hidden `<input id="shift_id">`** — Template change in `handover_form.html`; acceptable but unnecessary given the collab instance is already available.
3. **Read from `window.collabInstance.shiftId` (chosen)** — Zero template change; collab guard already required for feature activation.

**Consequences:** The incident collaboration functions are inherently coupled to `window.collabInstance` existing. This is correct — REQ-010 requires no action when collab is inactive.

---

### ADR-004: Polling Interval of 30 Seconds

**Status:** Accepted  
**Context:** REQ-004 specifies 30-second polling. A shorter interval increases server load; a longer interval reduces badge responsiveness.

**Decision:** 30 seconds as specified. No exponential backoff or jitter — poll failures are silent (AC-006 pattern).

**Alternatives considered:**
1. **SSE push for incident additions** — Would provide instant notification but requires server-side fan-out of draft saves. The single-process SSE architecture makes this feasible but adds complexity to the save endpoint (must broadcast to all connected users for the shift).
2. **10-second polling** — More responsive but 3× more server load with no functional benefit for the use case.
3. **30-second polling (chosen)** — Matches specification; acceptable latency for a non-critical notification.

**Consequences:** A teammate's incident can take up to 30 seconds to appear in the badge. This is acceptable per ASM-002.

---

## Implementation Guidelines

### File Modification Order

1. `routes/collaboration.py` — Add 3 new route functions after line 1433
2. `templates/partials/collaborative_handover.html` — Remove incident inputs from live sync; add polling functions
3. `templates/handover_form.html` — Add temp-id generation, blur event wiring, refresh badge, conflict modal, submit gate

### Naming Conventions

- API route functions: `snake_case` matching Flask convention (`save_draft_incident`, `check_incident_duplicate`, `get_others_incidents`)
- JS functions: `camelCase` (`checkIncidentDuplicate`, `saveDraftIncident`, `validateIncidentDuplicatesBeforeSubmit`)
- JS module-level state: `_camelCase` prefix for private variables (`_knownOtherTempIds`, `_incidentPollTimer`)
- DOM IDs for collab UI: `collab-incident-*` prefix

### Anti-Patterns to Avoid

- Do NOT throw or surface errors from `saveDraftIncident` or `checkIncidentDuplicate` to the user (AC-004, AC-002) — use `.catch(() => {})` silently
- Do NOT block form submission if the duplicate check network call fails — only block on confirmed duplicates
- Do NOT add `incidents-container` back into `observeDynamicEntries()` — live sync for incidents is deliberately removed (REQ-007)
- Do NOT create versioned template files — update in place

### Session Boundary

The blur handler and polling functions MUST check for an active session before calling any endpoint:

```
if (!window.collabInstance || !window.collabInstance.isConnected) return;
```

This single guard satisfies REQ-010 entirely.

### Refresh Badge HTML Structure

The badge button lives inside the incidents card header. Structure:

```
<button id="collab-incident-refresh-badge" style="display:none" onclick="loadOthersIncidents()">
  <i class="fas fa-sync-alt"></i>
  <span id="collab-incident-refresh-text">0 new incidents added</span>
</button>
```

Use `style="display:none"` (not Bootstrap `d-none`) — JS sets `badge.style.display = 'inline-flex'` to show, `badge.style.display = 'none'` to hide. Bootstrap's `d-none` uses `!important` which prevents JS override.

### Pre-Submit Gate Pattern

The submit handler must be `async` to await the duplicate check:

```
submitButton.addEventListener('click', async (e) => {
  e.preventDefault();
  if (window.collabInstance?.isConnected) {
    const canProceed = await validateIncidentDuplicatesBeforeSubmit();
    if (!canProceed) return;
  }
  form.submit();
});
```

---

## Testing Strategy

### Unit Test Targets

- `check_incident_duplicate`: verify returns `duplicate: false` when only current user has the ID; returns `duplicate: true` with `added_by` when another user has the same ID
- `save_draft_incident`: verify upsert creates new record on first call; updates existing record on second call; returns 403 when temp_id belongs to another user
- `get_others_incidents`: verify excludes current user's records; returns all other users' records for the shift

**Framework:** pytest + Flask test client  
**Fixtures:** Use `app.test_client()` with seeded `DraftIncident` records

### Integration Test Targets

- Two-user scenario: User A saves draft with `incident_id="INC001"`, User B calls check endpoint → receives `duplicate: true, added_by: "User A"`
- Polling cycle: User A creates draft, User B polls → badge count increments by 1
- Pre-submit gate: User A has INC001, User B has INC001 → conflict modal appears on User B's submit click
- Session guard: with no active SSE session, blur on Incident ID field → no network calls made

### E2E Scenarios

1. **Duplicate detection flow:** Open two browser sessions (User A, User B) on same shift. User B enters "INC001" that User A already has → inline warning shows "⚠️ INC001 was already entered by [User A name]".
2. **Refresh badge flow:** User A adds a new incident row and blurs incident_id. Within 30 seconds, User B's badge shows "1 new incident added". User B clicks → row appears attributed to User A.
3. **Pre-submit conflict flow:** Both users have "INC001". User B submits → conflict modal appears. User B clicks "Submit Anyway" → submission proceeds. Or clicks "Go Back & Review" → modal closes, form remains.
4. **Non-collab session:** Solo user fills incidents, clicks Submit → no modal, no badge, no API calls.

### Coverage Target

≥80% on new route functions in `routes/collaboration.py` (COMP-001, COMP-002, COMP-003).

---

## Security Considerations

### Authorization on Draft Save

**Concern:** A malicious user could supply another user's `temp_id` to overwrite their draft.  
**Mitigation:** `save_draft_incident` checks `draft.created_by_id != current_user.id` and returns 403.  
**OWASP:** A01 — Broken Access Control

### shift_id Scope Isolation

**Concern:** A user could supply a `shift_id` from another team's shift to see their draft incidents.  
**Mitigation:** All three endpoints require `@login_required`. The current user must be authenticated. Shift access is scoped by team membership enforced at session level. The `Shift.query.get_or_404(shift_id)` call in `save_draft_incident` validates the shift exists; however, it does not verify the user belongs to the shift's team. **Implementation note:** consider adding a team-membership check on shift_id for defense in depth.  
**OWASP:** A01 — Broken Access Control

### Input Validation

**Concern:** Oversized strings in draft fields could strain the DB or cause truncation issues.  
**Mitigation:** Model columns have length limits (`incident_id` String(64), `title` String(256), etc.). SQLAlchemy will raise DataError on overflow. The save endpoint wraps in try/except with rollback.  
**OWASP:** A03 — Injection

### XSS via Teammate Attribution

**Concern:** `added_by` value from the duplicate check response is rendered into the DOM inline warning. If the user's display name contains HTML, it could inject markup.  
**Mitigation:** Use `escapeHtml()` (already defined in `collaborative_handover.html`) when inserting `added_by` into the DOM. Do not use `innerHTML` with raw API values — use `textContent` or escape first.  
**OWASP:** A03 — XSS

### Rate Limiting

**Concern:** The duplicate check is called on every blur event; a script could flood the endpoint.  
**Mitigation:** Endpoint is `@login_required` (session auth). No anonymous calls possible. For production, Nginx rate limiting applies at the reverse proxy layer.  
**OWASP:** A04 — Insecure Design

### Draft Data PII

**Concern:** Draft incidents may contain incident IDs, assignee names, and descriptions — operational data.  
**Mitigation:** Draft records are scoped to authenticated users. The `get_others_incidents` endpoint returns only data from the same shift scope. Drafts are deleted on shift submission (REQ-008). No PII is stored beyond what already exists in submitted incident records.

---

## Design Changes Log

| Version | Changes | Rationale |
|---------|---------|-----------|
| v1 | Initial design spec | No prior version |
