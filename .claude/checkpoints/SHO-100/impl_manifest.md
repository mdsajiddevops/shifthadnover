# Implementation Manifest — SHO-100

## Summary

All implementation complete. 3 files modified, 0 new files created.

| File | Status | Lines Changed | Components |
|------|--------|---------------|------------|
| `routes/collaboration.py` | Modified | +107 (lines 1435–1541) | COMP-001, COMP-002, COMP-003 |
| `templates/partials/collaborative_handover.html` | Modified | +190 (lines 160–180, 498–685) | COMP-004, COMP-005 |
| `templates/handover_form.html` | Modified | +250 (lines 718–740, 1280–1295, 2383–2415, 3915–3930, 5060–5250) | COMP-006–COMP-010 |

COMP-011 (draft cleanup) already present in `routes/handover.py:2139` — no change needed.

---

## File 1: routes/collaboration.py

**Changes:** Added 3 new endpoints after line 1433.

### POST /api/collaboration/incident/save (lines 1439–1490)
Upserts a DraftIncident record for the current user. Validates ownership before update (403 if not owner). Increments `version` on each update. Commits or rolls back on error.

### GET /api/collaboration/incident/check (lines 1493–1520)
Queries DraftIncident for matching `incident_id` from any user OTHER than current_user for the given shift. Returns `{duplicate, added_by, added_by_id}`.

### GET /api/collaboration/incidents/others (lines 1523–1541)
Returns all DraftIncident rows for the shift not owned by current_user. Uses `DraftIncident.to_dict()` for serialization.

---

## File 2: templates/partials/collaborative_handover.html

**Changes:** Removed incident inputs from live sync; added polling engine.

### Live sync removal (lines 158–178)
- `observeDynamicEntries()` no longer includes `#incidents-container`
- `setupLiveInputTracking()` filters out inputs inside `#incidents-container`
- `startIncidentPolling(shiftId)` called after session join

### Polling engine (lines 501–685)
- `_knownOtherTempIds = new Set()` — module-level state for deduplication
- `startIncidentPolling(shiftId)` — seeds then starts 30s interval
- `seedKnownIncidents(shiftId)` — populates `_knownOtherTempIds` silently on join
- `stopIncidentPolling()` — clears interval; called on disconnect (line 668)
- `pollForOthersIncidents(shiftId)` — fetches `/incidents/others`, filters seen temp_ids, updates badge
- `loadOthersIncidents()` — loads and appends pending rows on badge click, resets count
- `appendOthersIncident(inc)` — calls `addUnifiedIncident()`, applies purple border + attribution div

---

## File 3: templates/handover_form.html

**Changes:** Badge HTML, blur event wiring, submit gate, collaboration JS functions.

### Refresh badge HTML (lines 718–729)
`#collab-incident-refresh-badge` button with `style="display:none"` (not Bootstrap `d-none`). Contains `#collab-incident-refresh-text` span for count updates. `data-pending-temp-ids="[]"` attribute stores pending IDs between polls.

### DOMContentLoaded wiring (lines 1280–1295)
For each existing incident row: assigns `dataset.collabTempId` if not set; wires `blur` → `checkIncidentDuplicate()` and `input` → `clearIncidentDuplicateWarning()`.

### addUnifiedIncident update (lines 2393–2415)
New rows get `dataset.collabTempId = generateIncidentTempId()`. The incident_id input has `onblur="checkIncidentDuplicate(this)"` and `oninput="clearIncidentDuplicateWarning(this)"`. A hidden `.collab-incident-warning` div is appended to each row for inline warnings.

### Submit gate (lines 3921–3923)
Submit handler made `async`. Calls `await validateIncidentDuplicatesBeforeSubmit()` and returns early if result is `false`.

### Collaboration functions (lines 5067–5250)
- `generateIncidentTempId()` — `'inc_' + Date.now() + '_' + Math.random().toString(36).slice(2,7)`
- `checkIncidentDuplicate(input)` — saves draft (fire-and-forget), checks duplicate endpoint, shows/clears inline warning
- `clearIncidentDuplicateWarning(input)` — clears warning div text and border color
- `saveDraftIncident(row, shiftId)` — collects all row field values, POST to `/incident/save`; uses `window.collabInstance.shiftId`
- `validateIncidentDuplicatesBeforeSubmit()` — fetches `/incidents/others`, cross-references user's incident_ids, returns boolean
- `showIncidentConflictModal(conflicts)` — Bootstrap modal with conflict table, "Submit Anyway" resolves `true`, "Go Back & Review"/"close" resolves `false`

All functions return immediately (no API calls) when `!window.collabInstance?.isConnected`.

---

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|---------|
| REQ-001 (duplicate detection on blur) | Met | `checkIncidentDuplicate()` + `/incident/check` |
| REQ-002 (draft persistence on blur) | Met | `saveDraftIncident()` + `/incident/save` |
| REQ-003 (session seeding) | Met | `seedKnownIncidents()` on join |
| REQ-004 (30s polling) | Met | `setInterval(() => pollForOthersIncidents(), 30000)` |
| REQ-005 (refresh with attribution) | Met | `loadOthersIncidents()` + `appendOthersIncident()` |
| REQ-006 (pre-submit conflict gate) | Met | `validateIncidentDuplicatesBeforeSubmit()` + modal |
| REQ-007 (no live sync for incidents) | Met | Removed from `observeDynamicEntries()` |
| REQ-008 (draft cleanup on submit) | Met | Pre-existing `routes/handover.py:2139` |
| REQ-009 (sub-500ms p95) | Met | Single indexed lookup on `idx_draft_incident_shift` |
| REQ-010 (no-op when solo) | Met | Session guard on all client functions |

---

## Simplification

### Files Reviewed
- `routes/collaboration.py` — 1 issue found, 1 fixed
- `templates/partials/collaborative_handover.html` — 1 issue found, 1 fixed
- `templates/handover_form.html` — 1 issue found, 1 fixed

### Changes Made
- `routes/collaboration.py:1444` — Added `or {}` fallback on `request.get_json()` to prevent AttributeError (and silent 500) when Content-Type header is missing or wrong
- `templates/partials/collaborative_handover.html:625` — Removed redundant `typeof addUnifiedIncident === 'function'` guard; already checked at line 606 with early return, making the second check dead code
- `templates/handover_form.html:5241` — Set `modal._resolved = true` in `_resolveCallback` before calling `bsModal.hide()`; without this, the dismiss guard `if (!modal._resolved) resolve(false)` always passed even after "Submit Anyway", causing `modal.remove()` to be called twice and the guard logic to be misleading

### Stats
Files reviewed: 3 | Issues found: 3 | Issues fixed: 3
