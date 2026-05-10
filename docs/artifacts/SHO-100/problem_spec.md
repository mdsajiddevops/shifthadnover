# Problem Specification — SHO-100

## Meta

| Field | Value |
|-------|-------|
| feature_id | FEAT-0100 |
| ticket | SHO-100 |
| title | Collaborative Incident Management — Duplicate Detection, Polling & Pre-Submit Conflict Resolution |
| date | 2026-05-08 |
| author | Sajid Mohammad |
| status | approved |
| classification | Small Feature |

---

## Problem Statement

Multiple NOC engineers can edit the same shift handover form simultaneously via a collaborative session. When two engineers independently add the same incident (identified by Incident ID), duplicate entries silently appear in the submitted handover — there is no warning during entry or before submission. The previous mitigation (field-level keystroke sync with section locking) was blocking (one user had to wait for the other) and unreliable. This feature replaces the incident section's live sync with an optimistic, non-blocking approach: duplicate detection on blur, periodic polling for teammates' additions, and a pre-submit conflict gate.

---

## Requirements

| ID | Type | Priority | Description |
|----|------|----------|-------------|
| REQ-001 | functional | P0 | The system shall detect duplicate Incident IDs by checking the current user's entered ID against other users' draft incident records for the same shift on every blur of the Incident ID input, and shall display an inline warning when a duplicate is found |
| REQ-002 | functional | P0 | The system shall persist the current user's incident row to a draft store (upsert by stable row identifier) when the user leaves the Incident ID field with a non-empty value |
| REQ-003 | functional | P0 | The system shall initialise the set of known teammates' draft incident identifiers at collaboration session join so that the refresh badge does not surface pre-existing incidents as new |
| REQ-004 | functional | P1 | The system shall poll for new draft incidents added by other users every 30 seconds during an active collaboration session and update a visible counter in the incidents card header |
| REQ-005 | functional | P1 | The system shall append teammates' incidents to the form with visual attribution when the user activates the refresh control |
| REQ-006 | functional | P1 | The system shall present a conflict summary to the user before final submission when one or more of their Incident IDs match draft incidents entered by other users, giving the user the choice to proceed or return and review |
| REQ-007 | functional | P0 | The system shall not propagate incident field changes to other users in real time and shall not acquire exclusive editing rights on incident rows; live field propagation and exclusive editing shall remain active for all other handover sections |
| REQ-008 | functional | P2 | The system shall remove all draft incident records associated with a shift upon successful submission of the handover for that shift |
| REQ-009 | non-functional | P0 | The duplicate-check request shall complete in under 500 ms at the 95th percentile under normal operating load |
| REQ-010 | non-functional | P0 | All collaboration incident features (duplicate check, polling, refresh badge, pre-submit conflict check) shall produce no UI change and no API calls when a collaboration session is not active |

---

## Acceptance Criteria

- **AC-001 (REQ-001 — happy):** Given an active collaboration session, when a user enters "INC001" in an Incident ID field and moves focus away, and another user's draft record for the same shift contains "INC001", then an inline warning appears below the field attributing the duplicate to the other user
- **AC-002 (REQ-001 — unhappy):** Given an active collaboration session, when the duplicate-check request fails due to a network or server error, then no warning is shown, no error is surfaced to the user, and the user may continue entering data normally
- **AC-003 (REQ-002 — happy):** Given an active collaboration session, when a user enters a non-empty Incident ID and moves focus away, then a draft record for that row is created or updated for the current user and shift
- **AC-004 (REQ-002 — unhappy):** Given an active collaboration session, when the draft-save request fails, then the failure is not surfaced to the user and the form remains fully operable
- **AC-005 (REQ-003 — happy):** Given a user joins a collaboration session where other users already have draft incidents for the shift, when the seeding completes, then the refresh badge shows zero and does not treat those pre-existing drafts as new
- **AC-006 (REQ-003 — unhappy):** Given a user joins a collaboration session and the seeding request fails, then the session continues normally; the badge may transiently show pre-existing incidents as new on the next poll cycle
- **AC-007 (REQ-004):** Given an active collaboration session, when a poll cycle detects a new draft incident added by another user since the user joined, then the badge in the incidents card header increments and becomes visible
- **AC-008 (REQ-005):** Given the refresh badge is visible with count N, when the user clicks it, then N incident rows are appended to the form each labelled with the adding user's name, and the badge resets to zero and hides
- **AC-009 (REQ-006 — conflict exists):** Given the user clicks Submit and one of their Incident IDs matches a draft from another user, then a modal appears listing the conflicting IDs and their attributed users, with "Submit Anyway" and "Go Back & Review" options
- **AC-010 (REQ-006 — no conflict):** Given the user clicks Submit and none of their Incident IDs match any other user's drafts, then no modal appears and submission proceeds normally
- **AC-011 (REQ-007 — happy):** Given an active collaboration session, when a user types in any incident field, then no data is transmitted to other users and no editing lock is placed on the incident row
- **AC-012 (REQ-007 — other sections):** Given an active collaboration session, when a user types in a key points, change info, or KB update field, then the change is propagated to other users in real time as before
- **AC-013 (REQ-008):** Given a handover form is submitted successfully, then all draft incident records for that shift are deleted from the draft store
- **AC-014 (REQ-009):** Given the duplicate-check endpoint is called, when measured at the 95th percentile, the server responds in under 500 ms
- **AC-015 (REQ-010):** Given collaboration mode is not active, when a user fills in incidents and clicks Submit, then no collaboration API endpoints are called and no collaboration UI elements (badge, inline warning, conflict modal) appear

---

## Constraints

- Single Gunicorn worker process — in-memory collaboration state cannot be shared across workers; horizontal scaling requires external cache (out of scope)
- No WebSockets available — all real-time communication uses Server-Sent Events (SSE) for push; polling is used for pull
- No external cache (Redis not used for collaboration state) — draft incident records are stored in the relational database
- Collaboration features activate only when an SSE session is established; the feature is entirely passive otherwise
- The `DraftIncident` model (`shift_id`, `temp_id`, `incident_id`, `created_by_id`) is the authoritative draft store; the schema must not change in this feature

---

## Non-Goals

| ID | Description | Rationale |
|----|-------------|-----------|
| NG-001 | Live keystroke synchronisation for incident fields | Deliberately removed — caused blocking UX and unreliable state when two users typed simultaneously |
| NG-002 | Automatic merging or resolution of duplicate incidents | Merging requires domain knowledge about which incident record is authoritative; user decision is safer |
| NG-003 | Changes to the handover form POST payload or submission data model | Minimises regression risk; the collaborative layer is purely advisory before submission |
| NG-004 | Duplicate detection or polling for solo (non-collaborative) sessions | No benefit without a second user; would add unnecessary server load for the common single-user case |

---

## Assumptions

| ID | Assumption | Risk if Wrong | Validation Needed |
|----|------------|---------------|-------------------|
| ASM-001 | `shift_id` is sufficient to scope draft incident isolation between teams and accounts — no two teams share the same shift ID | Low — shift IDs are per-team by design | false |
| ASM-002 | Poll failures are transient; the 30-second retry cadence is sufficient recovery without exponential backoff or circuit breaking | Medium — extended server downtime leaves the badge stale | false |
| ASM-003 | Draft cleanup on submission is best-effort; orphaned rows from concurrent or failed submissions are acceptable and cause no functional harm | Low — orphaned rows are ignored by all queries scoped to the submitting user | false |
| ASM-004 | The duplicate-check endpoint will consistently respond in under 500 ms given a properly indexed `DraftIncident` table | Low — single-row lookup on indexed `shift_id` + `incident_id` | false |

---

## Edge Cases

| ID | Scenario | Expected Behaviour | Related Requirement |
|----|----------|--------------------|---------------------|
| EC-001 | User enters the same Incident ID in two of their own rows on the same form | No server-side warning shown (self-duplicate is not caught by the check which only queries other users' drafts) | REQ-001 |
| EC-002 | SSE connection drops while the refresh badge is visible with a non-zero count | Polling stops; badge remains frozen at last known count; no new warnings are generated; pre-submit check still fires on submit | REQ-004, REQ-010 |
| EC-003 | Two users submit the handover simultaneously | First submission's cleanup deletes draft rows; second submission's cleanup finds no rows and completes silently; no error | REQ-008 |
| EC-004 | User dismisses the pre-submit conflict modal via the close button or backdrop click | Treated equivalently to "Go Back & Review" — submission is blocked and the user returns to the form | REQ-006 |
| EC-005 | User loads the handover form for a shift with no collaborative session ever started | All collaboration incident features remain completely inactive; no API calls, no UI elements rendered | REQ-010 |

---

## Backward Compatibility

✅ **No breaking changes identified.**

All collaboration incident features are guarded by runtime checks on the presence and connected state of the collaboration session object. Existing handover form behaviour for non-collaborative sessions, previously submitted shifts, and all non-incident form sections is entirely unaffected. No database schema changes are required beyond what is already present in the `DraftIncident` table.

---

## Glossary

| Term | Definition |
|------|------------|
| NOC | Network Operations Centre — the operational team that uses this application to manage shift handovers |
| Shift handover | The structured process of transferring operational context (incidents, key points, roster) from one on-duty team to the next |
| Collaborative session | An active SSE connection that links multiple users editing the same shift handover simultaneously; initiated explicitly by clicking "Collaborate" |
| DraftIncident | A database record representing an incident row being composed by a user in a collaborative session; identified by `shift_id` + `temp_id`; distinct from a submitted incident |
| temp_id | A client-generated stable identifier for a single incident row within a collaborative session, used to upsert draft records without primary-key conflicts |
| SSE | Server-Sent Events — an HTTP-based protocol for server-to-client push; used for presence updates and field-change broadcasts in this application |
| Incident ID | The canonical identifier for a ServiceNow or operational incident (e.g., "INC0001234"); expected to be unique per handover |
| Presence panel | The UI strip showing which users are currently viewing or editing the handover form; driven by SSE; not affected by this feature |
| Refresh badge | The button that appears in the incidents card header showing the count of new incidents added by teammates since the user joined; clicking it loads those incidents |
| Pre-submit conflict modal | The modal dialog shown before final submission when duplicate Incident IDs are detected between the current user's entries and teammates' drafts |
| shift_id | The database primary key of a `Shift` record; used as the scoping boundary for all collaborative draft data |
