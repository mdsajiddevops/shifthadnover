# Manual Test Cases — SHO-100

## Meta

| Field | Value |
|-------|-------|
| Ticket | SHO-100 |
| Feature | Collaborative Incident Management — Duplicate Detection, Polling & Pre-Submit Conflict Resolution |
| Date | 2026-05-08 |
| Author | Sajid Mohammad |
| Status | Draft |
| Feature ID | FEAT-0100 |

---

## Test Environment

### Prerequisites

- Flask app running at `http://localhost:5000` (Docker or local dev)
- MySQL database accessible (or SQLite for local dev)
- Two separate browser sessions open simultaneously (use one regular + one incognito window, or two different browsers)
- At least one shift in `Draft` status that both test users can access (same team)
- Test users:
  - **User A (primary):** `superadmin` / `admin123`
  - **User B (secondary):** `noc_admin` / `Admin@123`
  - **User C (tertiary):** `alice` / `User@123`

### Setup Steps

1. Log in as `superadmin` in Browser 1 and navigate to a draft handover form for the current team's active shift.
2. Log in as `noc_admin` in Browser 2 (incognito) and navigate to the **same** draft handover form URL.
3. Confirm both users can see the "Collaborate" button in the form header.
4. Confirm the `draft_incident` table is empty for the target shift before each test (run: `SELECT * FROM draft_incident WHERE shift_id = <id>;`).

### Key Identifiers (referenced throughout test cases)

| Element | Selector / ID |
|---------|---------------|
| Collaborate toggle button | `#collab-toggle-btn` |
| Toggle button label | `#collab-toggle-label` |
| Refresh badge | `#collab-incident-refresh-badge` |
| Refresh badge counter text | `#collab-incident-refresh-text` |
| Incidents container | `#incidents-container` |
| Incident ID inputs | `input[name="incident_id[]"]` |
| Inline duplicate warning | `.collab-incident-warning` |
| Pre-submit conflict modal | `#incidentConflictModal` |
| Submit button | `#submit-btn` |

### API Endpoints Under Test

| Purpose | Method | URL |
|---------|--------|-----|
| Save draft incident | POST | `/api/collaboration/incident/save` |
| Duplicate check | GET | `/api/collaboration/incident/check?shift_id=&incident_id=` |
| Poll for others' incidents | GET | `/api/collaboration/incidents/others?shift_id=` |

---

## Happy Path Test Cases

**TC-HP-001: Inline duplicate warning appears when two users enter the same Incident ID**

- Preconditions: Both User A (Browser 1) and User B (Browser 2) have clicked "Collaborate" on the same draft handover form and the toggle label reads "Leave Session" for both. The `draft_incident` table is empty for this shift.
- Steps:
  1. In Browser 2 (User B), click "Add Incident" to create a new incident row.
  2. In the Incident ID field, type `INC0001234` and tab/click away from the field (blur).
  3. Verify that Browser 2 receives a `200 OK` from `POST /api/collaboration/incident/save` (check Network tab in DevTools).
  4. In Browser 1 (User A), click "Add Incident" to create a new incident row.
  5. In the Incident ID field, type `INC0001234` and tab/click away from the field (blur).
  6. Observe the area directly below the Incident ID input in Browser 1.
- Expected result: An inline warning becomes visible below the Incident ID input in Browser 1 containing the text "INC0001234 was already entered by" followed by User B's display name or username. The input field gains a `border-warning` (yellow) CSS class. No error alert or page disruption occurs. User A can continue typing in other fields normally.
- AC covered: AC-001

---

**TC-HP-002: Draft incident record is persisted to the database on blur with a non-empty Incident ID**

- Preconditions: User A has clicked "Collaborate" and the toggle label reads "Leave Session". The `draft_incident` table is empty for this shift.
- Steps:
  1. In Browser 1 (User A), click "Add Incident".
  2. Fill in Application Name: `MyApp`, Incident ID: `INC0009999`, Short Description: `Test incident`.
  3. Click away from the Incident ID field (trigger blur).
  4. Immediately query the database: `SELECT * FROM draft_incident WHERE shift_id = <id> AND incident_id = 'INC0009999';`
- Expected result: Exactly one row is returned in the query result with `created_by_id` matching User A's user ID, `incident_id = 'INC0009999'`, `app_name = 'MyApp'`, and `title = 'Test incident'`. The `temp_id` column is populated with a non-empty string.
- AC covered: AC-003

---

**TC-HP-003: Upsert behaviour — re-entering a field updates the existing draft row, not create a duplicate**

- Preconditions: User A is in an active collaboration session. User A has already blurred an Incident ID field containing `INC0001111` (so one `draft_incident` row exists for that `temp_id`).
- Steps:
  1. In Browser 1 (User A), click back into the same Incident ID field.
  2. Clear the field and type `INC0001111-REVISED`.
  3. Tab/click away from the field (blur).
  4. Query the database: `SELECT COUNT(*) FROM draft_incident WHERE shift_id = <id> AND created_by_id = <user_a_id>;`
  5. Also query: `SELECT incident_id FROM draft_incident WHERE shift_id = <id> AND created_by_id = <user_a_id>;`
- Expected result: The COUNT returns `1` (not 2). The `incident_id` value is `INC0001111-REVISED`. No duplicate row was created; the existing row was updated in place via the `shift_id + temp_id` unique constraint.
- AC covered: AC-003

---

**TC-HP-004: Seeding — refresh badge starts at zero when joining a session with pre-existing teammate drafts**

- Preconditions: User B is already in a collaboration session and has entered incident `INC0002222` (draft row exists in DB). User A has NOT yet clicked "Collaborate".
- Steps:
  1. In Browser 1 (User A), click the "Collaborate" button and wait for the toggle label to read "Leave Session".
  2. Observe the `#collab-incident-refresh-badge` element immediately after the session connects (within 5 seconds, before the first 30-second poll fires).
- Expected result: The refresh badge is hidden (`display: none`). The badge counter shows `0`. User B's pre-existing incident `INC0002222` is NOT surfaced as a new incident; it is silently added to `_knownOtherTempIds` during session seeding.
- AC covered: AC-005

---

**TC-HP-005: Polling — refresh badge increments when a teammate adds a new incident after session join**

- Preconditions: Both User A and User B are in an active collaboration session on the same draft. No incidents have been entered. User A's session seeding has completed (toggle shows "Leave Session"). `_incidentPollTimer` is running (30-second interval).
- Steps:
  1. In Browser 2 (User B), click "Add Incident", type `INC0003333` in the Incident ID field, then blur the field to save the draft.
  2. Wait up to 35 seconds for the next poll cycle to fire in Browser 1 (User A).
  3. Observe the `#collab-incident-refresh-badge` in Browser 1 after the poll completes.
- Expected result: The refresh badge becomes visible (changes from `display: none` to `display: inline-flex`) in Browser 1. The badge counter text reads "1 new incident added". The badge `data-count` attribute equals `"1"`.
- AC covered: AC-007

---

**TC-HP-006: Clicking the refresh badge loads teammates' incidents and resets the badge**

- Preconditions: The refresh badge in User A's browser is visible with count `2` (two new incidents added by User B since A joined). The `data-pending-temp-ids` attribute contains two temp ID strings.
- Steps:
  1. In Browser 1 (User A), click the `#collab-incident-refresh-badge` button.
  2. Observe the `#incidents-container` for new rows.
  3. Observe the badge visibility after the click.
- Expected result: Two new incident rows are appended to `#incidents-container`. Each new row is visually distinguished with a purple-left-border style (`border-left-color: #6f42c1`). A toast notification appears confirming "Loaded 2 incidents from teammates". The refresh badge is hidden (`display: none`) and its `data-count` resets to `"0"` and `data-pending-temp-ids` resets to `"[]"`.
- AC covered: AC-008

---

**TC-HP-007: Pre-submit conflict modal appears and blocks submission when duplicates exist**

- Preconditions: User A is in a collaboration session. User B has entered `INC0005555` in their draft (a `draft_incident` row exists attributed to User B). User A has also entered `INC0005555` in their own incident row on the form.
- Steps:
  1. In Browser 1 (User A), click the "Submit" button.
  2. Wait for the pre-submit validation to complete (it calls `GET /api/collaboration/incidents/others`).
  3. Observe whether a modal appears.
  4. Read the modal content.
- Expected result: A modal with id `incidentConflictModal` appears, styled with a warning (`bg-warning`) header reading "Duplicate Incident IDs Detected". The modal body contains a table row with `INC0005555` in the first column and User B's display name in the second column. Two action buttons are visible: "Go Back & Review" and "Submit Anyway". The form is NOT submitted at this point.
- AC covered: AC-009

---

**TC-HP-008: Clicking "Submit Anyway" on the conflict modal proceeds with form submission**

- Preconditions: The conflict modal from TC-HP-007 is visible on screen.
- Steps:
  1. In Browser 1 (User A), click the "Submit Anyway" button in the modal footer.
  2. Observe the modal closing and form submission behaviour.
- Expected result: The modal closes. The form submits with `action = 'submit'`. The browser navigates away to the post-submission page (or shows a success notification). The submission is not blocked a second time.
- AC covered: AC-009

---

**TC-HP-009: No conflict modal when submitted Incident IDs do not match any teammate drafts**

- Preconditions: User A is in a collaboration session. User A has entered `INC0007777` in their incident row. User B has entered `INC0008888` (a different ID) in their draft — no overlap exists.
- Steps:
  1. In Browser 1 (User A), click the "Submit" button.
  2. Wait for the pre-submit validation to complete.
  3. Observe whether the modal appears.
- Expected result: No `#incidentConflictModal` is rendered. The form proceeds directly to submission without interruption.
- AC covered: AC-010

---

**TC-HP-010: Draft incidents for the shift are deleted from the database after successful submission**

- Preconditions: User A is in a collaboration session. User A and User B have each saved at least one draft incident for the shift (two or more rows in `draft_incident` for this `shift_id`).
- Steps:
  1. In Browser 1 (User A), click "Submit Anyway" (or submit normally if no conflict) to submit the handover.
  2. Wait for the submission to complete and the page to redirect/reload.
  3. Query the database: `SELECT COUNT(*) FROM draft_incident WHERE shift_id = <id>;`
- Expected result: The count returns `0`. All draft incident rows for the submitted shift have been deleted by the cleanup in `routes/handover.py` (line 2139: `DraftIncident.query.filter_by(shift_id=shift_id).delete()`).
- AC covered: AC-013

---

**TC-HP-011: Incident fields do not propagate to other users in real time while typing**

- Preconditions: Both User A and User B are in an active collaboration session on the same draft. No incidents have been entered.
- Steps:
  1. In Browser 1 (User A), click "Add Incident" and begin typing `INC0006666` into the Incident ID field (do NOT blur — keep the field focused).
  2. Monitor Browser 2 (User B) for any updates to the incidents section.
  3. Monitor the Network tab in Browser 1 for any outgoing fetch/XHR requests to the collaboration broadcast endpoint while typing.
- Expected result: No data appears in User B's incident section while User A is typing. No network request to the collaboration broadcast endpoint is triggered by keystrokes in incident fields. The `setupLiveInputTracking` function explicitly excludes `#incidents-container` fields (confirmed in source code filter `.filter(el => !el.closest('#incidents-container'))`).
- AC covered: AC-011

---

**TC-HP-012: Incident section does not acquire an exclusive editing lock**

- Preconditions: Both User A and User B are in an active collaboration session.
- Steps:
  1. In Browser 1 (User A), click into an Incident ID field and begin typing.
  2. In Browser 2 (User B), simultaneously click into an Incident ID field on a different row and begin typing.
  3. Observe whether either user sees a "locked" indicator on their incident row.
  4. Check the presence panel in both browsers for any lock icons on the incidents section.
- Expected result: Neither user sees any lock indicator on any incident row. Both users can type freely in their respective rows without being blocked or queued. No `acquireLock` call is made for incident fields (the lock mechanism only applies to non-incident fields).
- AC covered: AC-011

---

## Edge Case Test Cases

**TC-EC-001: Self-duplicate in two rows of the same form is not flagged as a collaborative duplicate**

- Preconditions: User A is in an active collaboration session. User A is the ONLY user who has entered data — no other users have `draft_incident` rows for this shift.
- Steps:
  1. In Browser 1 (User A), click "Add Incident" twice to create two incident rows.
  2. In Row 1, type `INC0004444` in the Incident ID field and blur.
  3. In Row 2, type `INC0004444` (the same ID) in the Incident ID field and blur.
  4. Observe the inline warning area on Row 2.
- Expected result: No inline warning appears on Row 2. The `/api/collaboration/incident/check` endpoint only queries `DraftIncident` records where `created_by_id != current_user.id`, so self-duplicates are not detected. The self-duplicate is a user concern (not a collaboration concern) and is outside the scope of this feature.
- AC covered: AC-001 (boundary: EC-001)

---

**TC-EC-002: SSE connection drop — badge freezes, polling stops, pre-submit check still fires**

- Preconditions: User A is in an active collaboration session. The refresh badge in User A's browser shows count `1` (one pending incident from User B). The `_incidentPollTimer` is running.
- Steps:
  1. Simulate an SSE connection drop: In Browser 1, open DevTools → Network tab → select the SSE stream request and block/cancel it; OR disable network interface temporarily; OR navigate the app away and back without re-joining collaboration.
  2. Wait 35 seconds to confirm the poll timer no longer fires (no new network requests to `/api/collaboration/incidents/others`).
  3. Observe the refresh badge count.
  4. Click the "Submit" button while `window.collabInstance.isConnected` is `false`.
- Expected result: The poll timer stops (`pollForOthersIncidents` returns early because `!window.collabInstance.isConnected`). The badge remains frozen at count `1` — it does not increment or reset. No new warnings are generated. When Submit is clicked, `validateIncidentDuplicatesBeforeSubmit` returns `true` immediately (early-return guard on `!window.collabInstance.isConnected`), and the form submits without a conflict modal.
- AC covered: AC-007 (boundary: EC-002)

---

**TC-EC-003: Two users submit the handover simultaneously — no error from concurrent draft cleanup**

- Preconditions: User A and User B both have the same draft handover form open. Both are in collaboration sessions. Both have saved draft incidents to the DB. The handover is in a state both can submit (e.g., both are admins).
- Steps:
  1. In Browser 1 (User A), click "Submit" and immediately (within 1 second) click "Submit" in Browser 2 (User B).
  2. If a conflict modal appears in either browser, click "Submit Anyway".
  3. Wait for both submissions to complete.
  4. Observe error logs and the UI in both browsers.
  5. Query: `SELECT COUNT(*) FROM draft_incident WHERE shift_id = <id>;`
- Expected result: One submission succeeds and one may receive an error or duplicate-submission warning from the app layer. The draft cleanup in `handover.py` (line 2139) performs a bulk delete — the first submission deletes all rows, and the second finds zero rows and completes silently (per ASM-003). No 500 error surfaces to either user from the cleanup logic. The `draft_incident` table count is `0` after both submissions complete.
- AC covered: AC-013 (boundary: EC-003)

---

**TC-EC-004: Dismissing the conflict modal via the X button or backdrop blocks submission**

- Preconditions: User A is in a collaboration session and has triggered the pre-submit conflict modal (same setup as TC-HP-007).
- Steps:
  1. In Browser 1 (User A), with the `#incidentConflictModal` visible, click the X close button (`btn-close`) in the modal header.
  2. Observe whether the form submits.
  3. Repeat the test: re-click Submit to trigger the modal again, then click outside the modal dialog (backdrop area). Observe whether the form submits.
- Expected result: In both cases (X button and backdrop click), the modal closes and the form does NOT submit. The `showIncidentConflictModal` Promise resolves `false` via the `hidden.bs.modal` fallback handler, which causes `validateIncidentDuplicatesBeforeSubmit` to return `false` and the submit handler to `return` early. The user remains on the handover form. This is equivalent to clicking "Go Back & Review".
- AC covered: AC-009 (boundary: EC-004)

---

**TC-EC-005: No collaboration API calls or UI elements when collaboration is not active (solo session)**

- Preconditions: User A is logged in and viewing a draft handover form. User A has NOT clicked the "Collaborate" button — `window.collabInstance` is `null` or `undefined`.
- Steps:
  1. In Browser 1 (User A), open DevTools → Network tab, filter by XHR/Fetch.
  2. Click "Add Incident" and enter `INC0009000` into the Incident ID field.
  3. Blur the Incident ID field.
  4. Wait 35 seconds to confirm no polling requests fire.
  5. Click the "Submit" button.
  6. Inspect the Network tab for any requests to `/api/collaboration/incident/check`, `/api/collaboration/incident/save`, or `/api/collaboration/incidents/others`.
  7. Inspect the DOM for `#incidentConflictModal` and `.collab-incident-warning` visibility.
- Expected result: Zero requests to any `/api/collaboration/incident*` endpoint appear in the Network tab. The inline warning `.collab-incident-warning` remains hidden (`display: none`). The `#collab-incident-refresh-badge` remains hidden. No `#incidentConflictModal` is injected into the DOM. The form submits normally. This is consistent with EC-005 and NG-004.
- AC covered: AC-015 (boundary: EC-005)

---

**TC-EC-006: Seeding failure — session continues and badge may transiently show pre-existing incidents**

- Preconditions: User B has draft incidents already in the DB for the shift. User A is about to click "Collaborate".
- Steps:
  1. In Browser 1 (User A), open DevTools → Network tab.
  2. Add a request block rule for `/api/collaboration/incidents/others` (simulate a network failure for the seeding call).
  3. Click "Collaborate" — wait for the toggle to read "Leave Session".
  4. Remove the request block rule.
  5. Wait 35 seconds for the next poll cycle.
  6. Observe the refresh badge.
- Expected result: The collaboration session connects successfully despite the seeding failure (no error toast about seeding). After the first successful poll cycle, the badge shows User B's pre-existing incidents as "new" (because `_knownOtherTempIds` was not seeded). This is acceptable and documented in AC-006. The session remains functional for all other collaboration features.
- AC covered: AC-006

---

## Regression Test Cases

**TC-REG-001: Key Points section still live-syncs in real time during an active collaboration session**

- Preconditions: Both User A and User B are in an active collaboration session on the same draft handover.
- Steps:
  1. In Browser 1 (User A), locate the Key Points section and type in any Key Point description field (e.g., "Production patching scheduled").
  2. Observe Browser 2 (User B) within 3 seconds.
- Expected result: The text "Production patching scheduled" appears in real time in the same Key Point field in Browser 2 without any action from User B. This confirms that `setupLiveInputTracking` continues to broadcast changes for non-incident fields via the collaboration broadcast endpoint, unaffected by the incident-section exclusion.
- AC covered: AC-012

---

**TC-REG-002: Change Info section still live-syncs in real time during an active collaboration session**

- Preconditions: Both User A and User B are in an active collaboration session on the same draft handover.
- Steps:
  1. In Browser 1 (User A), navigate to the Change Info section and type a change number (e.g., `CHG0001234`) into the Change Number field.
  2. Observe Browser 2 (User B) within 3 seconds.
  3. Repeat for the KB Updates section if visible.
- Expected result: The change number `CHG0001234` appears live in Browser 2's corresponding field. KB Update field changes also propagate live. No regression in live sync for these sections.
- AC covered: AC-012

---

**TC-REG-003: Solo session — no collaboration UI elements render on the form**

- Preconditions: User C (`alice`) is logged in and opens a draft handover form without clicking "Collaborate". No other user is editing the same form.
- Steps:
  1. In Browser 1 (User C), inspect the DOM for the following elements: `#collab-incident-refresh-badge`, `#collab-panel`, and `.collab-incident-warning`.
  2. Fill in three complete incident rows with Incident IDs `INC0010001`, `INC0010002`, `INC0010003`.
  3. Click the Submit button and observe the submission flow.
- Expected result: `#collab-incident-refresh-badge` is present in DOM but `display: none`. `#collab-panel` is absent or hidden (collaboration panel not shown without active session). No `.collab-incident-warning` elements are visible. The Submit button proceeds directly to form submission without triggering `validateIncidentDuplicatesBeforeSubmit` checks (the function returns `true` immediately due to `!window.collabInstance`). No collaboration API calls are made during the entire session.
- AC covered: AC-015

---

**TC-REG-004: Existing handover form submit flow (non-collaborative) remains unchanged**

- Preconditions: User A opens a draft handover form. Collaboration is NOT active. The handover has two key points and one incident pre-filled.
- Steps:
  1. In Browser 1 (User A), make a minor edit to any key point field.
  2. Click the "Save as Draft" button and verify it saves without error.
  3. Click the "Submit" button.
  4. If any standard validation fails (e.g., shift mismatch), resolve it and re-click Submit.
  5. Confirm the post-submission page loads correctly.
- Expected result: The save-as-draft flow works correctly. The submit flow runs existing validation (key points, change date/time, change numbers, KB numbers) and completes normally. No collaboration-related elements, modals, or API calls interfere. The handover is submitted successfully.
- AC covered: AC-015

---

## Acceptance Criteria Traceability Matrix

| AC ID | Requirement | Test Case(s) | Notes |
|-------|-------------|--------------|-------|
| AC-001 | REQ-001 (happy) — duplicate warning appears on blur | TC-HP-001 | Verifies inline warning text and yellow border |
| AC-002 | REQ-001 (unhappy) — network error during duplicate check → silent fail | TC-EC-006 (partial) | Network block during check; see also: silent catch in `checkIncidentDuplicate` |
| AC-003 | REQ-002 (happy) — draft record created/updated on blur | TC-HP-002, TC-HP-003 | Covers both create (new row) and upsert (update) |
| AC-004 | REQ-002 (unhappy) — draft-save failure → silent fail, form operable | TC-EC-006 (partial) | Same network-block pattern applied to `/incident/save`; silent catch in `saveDraftIncident` |
| AC-005 | REQ-003 (happy) — badge at zero when joining with pre-existing drafts | TC-HP-004 | Seeding completes before first poll; no phantom badge increment |
| AC-006 | REQ-003 (unhappy) — seeding fails → session continues, badge may show pre-existing | TC-EC-006 | Network block on seeding call; session still connects |
| AC-007 | REQ-004 — poll detects new incidents and increments badge | TC-HP-005, TC-EC-002 | Happy path (badge increments); edge case (badge freezes on SSE drop) |
| AC-008 | REQ-005 — clicking refresh badge appends incidents and resets badge | TC-HP-006 | N incidents appended, badge resets to 0, toast shown |
| AC-009 | REQ-006 (conflict) — conflict modal shown before submit | TC-HP-007, TC-HP-008, TC-EC-004 | Modal appears; Submit Anyway proceeds; X/backdrop blocks |
| AC-010 | REQ-006 (no conflict) — no modal when no duplicates | TC-HP-009 | Clean submit path with non-overlapping incident IDs |
| AC-011 | REQ-007 (happy) — no live propagation or lock for incident fields | TC-HP-011, TC-HP-012 | No broadcast on keystroke; no lock acquired |
| AC-012 | REQ-007 (other sections) — key points, change info, KB update still live-sync | TC-REG-001, TC-REG-002 | Regression: non-incident sections unaffected |
| AC-013 | REQ-008 — draft incidents deleted after successful submission | TC-HP-010, TC-EC-003 | Happy path cleanup; concurrent-submission edge case |
| AC-014 | REQ-009 — duplicate-check endpoint responds under 500 ms p95 | TC-HP-001 (timing) | During TC-HP-001 execution, measure response time in Network tab; should be well under 500 ms on indexed DB |
| AC-015 | REQ-010 — no UI or API activity without active collaboration session | TC-EC-005, TC-REG-003, TC-REG-004 | Three angles: explicit check, solo-user render, non-collab submit flow |
