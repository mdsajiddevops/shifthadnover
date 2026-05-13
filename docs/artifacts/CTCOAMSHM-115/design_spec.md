# Architecture Design Specification
## Shifthandover: Gap Remediation & Core Feature Implementation

---

## Meta

| Field | Value |
|-------|-------|
| **Ticket ID** | CTCOAMSHM-115 [J:CTCOAMSHM-115] |
| **Project** | shifthandover_v3 |
| **Spec Date** | 2026-05-12 |
| **Problem Spec** | `docs/phase-2/problem_spec.md` |
| **Status** | Draft — Pending Architecture Review |

---

## Problem Spec Reference

See [problem_spec.md](problem_spec.md) — implements REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012. [J:CTCOAMSHM-115]

---

## Current Architecture

### Deployment Topology

The platform is a server-side rendered Flask monolith (`shifthandover_v3`) deployed behind Nginx (TLS termination) with Gunicorn as the WSGI server. [C:Api_Contracts] No dedicated REST versioning prefix exists; all routes are served from the application root, with a Swagger UI available at `/apidocs`. [C:Api_Contracts]

### Blueprint Organisation

Approximately 45–48 Flask Blueprints are registered in `app.py`, each scoped to a single domain area — handover management, roster/scheduling, admin, escalation, collaboration, SSO, and reporting. [C:Api_Contracts] Route handlers are organised under a `routes/` directory, one file per blueprint domain.

### Authentication & Session Management

Two authentication paths are active: OAuth 2.0/SAML SSO (primary) and Fernet-encrypted local credential login (fallback). [C:Api_Contracts] Session state is backed by server-side tokens in the `session_tokens` table; the `validate_session()` middleware executes on **every inbound request**, enabling server-side forced logout without client co-operation. [C:Api_Contracts]

### Real-Time Collaborative Editing

Real-time collaborative drafting uses Server-Sent Events with a DB-polling backend — no WebSocket or Redis pub-sub operates in the canonical production deployment. [C:Api_Contracts] An earlier branch introduced a YJS CRDT layer with Redis pub-sub for presence/locking, but this is not the default production path. [C:Api_Contracts]

### Existing Concurrency Primitives

The `SectionLock` model backs per-section pessimistic locking; acquire and release endpoints are already part of the collaborative editing surface. [C:Api_Contracts] `DraftIncident`, `DraftKeyPoint`, and `HandoverChange` models back draft persistence and the immutable change audit log. [C:Api_Contracts]

### Pre-Remediation State of Gap Artefacts

| Artefact | Current State |
|----------|--------------|
| `develop` branch | No Git-server push protection; direct pushes accepted |
| GitLab MR approval rules | No Maintainer-approval or self-approval-prevention policy in place |
| `requirements.txt` | Contains range specifiers (e.g., `>=`) for at least flask-sock and potentially other packages |
| `docker-compose.yml` | Includes `volumes: - .:/app` bind-mount that shadows the image COPY layer at runtime |
| `.gitlab-ci.yml` | No regression test stage; the 10 files under `tests/regression/` do not execute in CI |

### Components Requiring Modification vs. Net-New

| Artefact | Change Type | Driver |
|----------|-------------|--------|
| GitLab project settings | Modified (external) | REQ-001, REQ-002, REQ-003 |
| `.gitlab-ci.yml` | Modified | REQ-006 |
| `requirements.txt` | Modified | REQ-004 |
| `docker-compose.yml` | Modified | REQ-005 |
| `app.py` | Modified (blueprint registration) | REQ-007–012 |
| All CoreAction application files | Net-new | REQ-007–012 |

The CoreAction application feature does not modify any existing HTTP API response schema, session management contract, or data structure used by existing platform features. [C:Api_Contracts]

---

## Architecture

### Pattern

**Layered Service Architecture within the Existing Flask Monolith.** The CoreAction feature follows the identical blueprint → service → repository layering already established across the ~45 existing blueprints. [C:Api_Contracts] Infrastructure gap remediations (REQ-001–006) are configuration and manifest artefacts with no application-layer code surface. This pattern is elaborated in ADR-001.

---

### Components

#### Group A — Infrastructure / Configuration Artefacts

---

**COMP-001 — Protected Branch Rule**
- **Type:** GitLab project configuration artefact
- **Responsibility:** Enforces rejection of all direct pushes to the `develop` branch at the Git server's pre-receive layer, permitting only commits that arrive via approved merge requests. Addresses REQ-001.
- **Dependencies:** None (GitLab server-side control; resistant to client-side or API-level bypass)
- **File Path:** Administered via GitLab project settings UI or GitLab REST API — not a repository file. Operational configuration documented at `docs/ops/branch-protection.md`.

---

**COMP-002 — MR Approval Policy**
- **Type:** GitLab project-level approval policy configuration
- **Responsibility:** Enforces the requirement for at least one independent Maintainer approval — preventing self-approval — before a merge request targeting `develop` is permitted to merge. Addresses REQ-002 and REQ-003.
- **Dependencies:** COMP-001 (branch protection must be active for approval rules to be meaningful)
- **File Paths:**
  - `.gitlab/approval_rules.yml` — declarative approval policy: minimum 1 Maintainer, self-approval disabled
  - `CODEOWNERS` — maps repository path patterns to Maintainer group(s), backing approval-eligibility checks

---

**COMP-003 — CI Regression Test Stage**
- **Type:** GitLab CI/CD pipeline stage configuration
- **Responsibility:** Executes all pytest files found in `tests/regression/` as a mandatory blocking stage on every merge request pipeline targeting `develop`, reporting each file's individual result. Addresses REQ-006.
- **Dependencies:** COMP-001 (pipeline is only triggered on MR-scoped pipelines once branch protection is active)
- **File Path:** `.gitlab-ci.yml` *(modified — new `regression-tests` stage block added)*

---

**COMP-004 — Dependency Pin Validator**
- **Type:** CI utility script
- **Responsibility:** Scans `requirements.txt` for any package specifier that is not an exact `==` pin, exits non-zero, and reports all offending package names. Addresses REQ-004 (AC-004b).
- **Dependencies:** COMP-003 (executes as a step within the CI pipeline); COMP-005 (file under scan)
- **File Path:** `scripts/validate_pins.py`

---

**COMP-005 — Python Dependency Manifest**
- **Type:** Dependency declaration artefact
- **Responsibility:** Declares all 45+ Python runtime dependencies at exact `==` version specifiers, ensuring identical package resolution across independent fresh installs. Addresses REQ-004.
- **Dependencies:** None
- **File Path:** `requirements.txt` *(modified — all range specifiers replaced with `==`; flask-sock pinned to a confirmed exact version per Open Item #8 in `docs/phase-2/interrogation_summary.md`)*

---

**COMP-006 — Production Container Compose Configuration**
- **Type:** Docker Compose configuration artefact
- **Responsibility:** Declares the production container runtime such that the application directory is populated exclusively from the image build artefact, with no host bind-mounts targeting `/app`. Addresses REQ-005.
- **Dependencies:** None
- **File Paths:**
  - `docker-compose.prod.yml` *(new — production-safe compose file; no `/app` bind-mount)*
  - `docker-compose.yml` *(modified — bind-mount either removed or restricted to a dev-only override per ADR-004)*
  - `docker-compose.override.yml` *(new — development bind-mount declared here, never referenced by production deployment automation)*

---

#### Group B — Application Components (CoreAction Feature)

---

**COMP-007 — CoreAction Blueprint**
- **Type:** Flask Blueprint (route handler)
- **Responsibility:** Exposes the HTTP surface for the CoreAction feature — request intake, response serialisation, and SSE stream endpoint registration — without containing any business or validation logic. Addresses REQ-007, REQ-011.
- **Dependencies:** COMP-008, COMP-010, COMP-014
- **File Path:** `routes/core_action.py`

---

**COMP-008 — CoreAction Service**
- **Type:** Service (business logic orchestrator)
- **Responsibility:** Orchestrates the single atomic execution of the CoreAction — sequencing lock acquisition, repository write, audit log write, and SSE event publication — and returns a structured result to the blueprint. Addresses REQ-007, REQ-011, REQ-012.
- **Dependencies:** COMP-009, COMP-011, COMP-013, COMP-014, COMP-015, COMP-016
- **File Path:** `services/core_action_service.py`

---

**COMP-009 — CoreAction Input Validator**
- **Type:** Validator (validation layer)
- **Responsibility:** Validates all fields of a CoreAction submission against type, length, format, and nullability rules, returning a structured map of field-level error messages for every distinct failure encountered. Addresses REQ-008.
- **Dependencies:** None (pure function receiving a typed input DTO)
- **File Path:** `validators/core_action_validator.py`

---

**COMP-010 — Permission Guard Decorator**
- **Type:** Python decorator (RBAC enforcement)
- **Responsibility:** Verifies that the currently authenticated session holds the `CORE_ACTION_EXECUTE` permission, short-circuiting the request with a 403 response and triggering an audit entry before any business logic executes. Addresses REQ-010.
- **Dependencies:** Existing `validate_session()` middleware [C:Api_Contracts]; COMP-016
- **File Path:** `decorators/permission_guard.py`

---

**COMP-011 — CoreAction Repository**
- **Type:** Repository (data access layer)
- **Responsibility:** Performs all database reads and writes for the CoreAction resource — create, status update, and rollback — within a single committed transaction boundary. Addresses REQ-007, REQ-009 (atomicity).
- **Dependencies:** COMP-012
- **File Path:** `repositories/core_action_repository.py`

---

**COMP-012 — CoreAction Data Model**
- **Type:** SQLAlchemy ORM model
- **Responsibility:** Defines the persistent schema for a `CoreActionRecord` row, including state, actor identity, resource reference, version counter, and timestamps. Addresses REQ-007, REQ-009.
- **Dependencies:** None (standalone ORM model)
- **File Path:** `models/core_action.py`

---

**COMP-013 — Section Lock Coordinator**
- **Type:** Service (concurrency control)
- **Responsibility:** Brokers acquire and release operations on the existing `SectionLock` model for the CoreAction's target resource section, returning a structured success or denial result to the caller. Addresses REQ-009.
- **Dependencies:** Existing `SectionLock` model [C:Api_Contracts]
- **File Path:** `services/section_lock_coordinator.py`

---

**COMP-014 — CoreAction SSE Publisher**
- **Type:** Service (real-time event delivery)
- **Responsibility:** Writes a `HandoverChange`-compatible event record to the DB change log so that the existing SSE polling loop delivers it to connected peer clients on the next poll cycle. Addresses REQ-011 (peer visibility).
- **Dependencies:** Existing SSE polling infrastructure [C:Api_Contracts]; existing `HandoverChange` model [C:Api_Contracts]
- **File Path:** `services/sse_publisher.py`

---

**COMP-015 — Degradation Logger**
- **Type:** Utility (error capture and degradation signalling)
- **Responsibility:** Captures transient dependency failures during CoreAction execution — logs the error internally with full structured context — and returns a typed degradation signal that COMP-008 propagates to COMP-007 for user-facing notification. Addresses REQ-012.
- **Dependencies:** None (wraps standard Python `logging`)
- **File Path:** `services/degradation_logger.py`

---

**COMP-016 — Audit Log Writer**
- **Type:** Service (immutable audit trail)
- **Responsibility:** Appends an immutable audit entry for every permission-denial event and every CoreAction state transition, capturing user identity, operation type, resource ID, timestamp, and outcome. Addresses REQ-010 (denial audit), REQ-007 (state transition audit).
- **Dependencies:** Existing handover audit log infrastructure [C:Api_Contracts]; COMP-017
- **File Path:** `services/audit_log_writer.py`

---

**COMP-017 — CoreAction Audit Log Model**
- **Type:** SQLAlchemy ORM model
- **Responsibility:** Defines the append-only schema for `CoreActionAuditEntry` rows, supporting both permission-denial events (where no `CoreActionRecord` yet exists) and successful action-completion events. Addresses REQ-010, REQ-007.
- **Dependencies:** None (standalone ORM model)
- **File Path:** `models/core_action_audit.py`

---

### Data Flows

#### DF-01 — Direct Push Rejected (REQ-001)

```
Developer Git client
  → git push origin develop
  → COMP-001 (Protected Branch Rule) pre-receive hook fires
  → Push rejected; error message returned to developer before any commit recorded on develop
```

#### DF-02 — MR Approval Enforcement (REQ-002, REQ-003)

```
Developer → Merge request created targeting develop
  → COMP-002 (MR Approval Policy) evaluates submitter identity vs approver identity
  → If self-approval attempted: approval not counted; MR blocked from merging
  → If independent Maintainer approval received: merge-readiness condition satisfied
  → Maintainer (distinct from author) initiates merge → merge completes
```

#### DF-03 — CI Pipeline on Merge Request (REQ-004, REQ-006)

```
Merge request opened or updated targeting develop
  → GitLab CI triggered (pipeline scoped to MR)
  → COMP-003 (CI Regression Test Stage): pytest discovers all files in tests/regression/;
      individual pass/fail results reported per file; any failure marks stage failed and blocks merge
  → COMP-004 (Dependency Pin Validator): scans COMP-005 for non-== specifiers;
      exits non-zero with offending package names if found; blocks merge
```

#### DF-04 — CoreAction Happy Path (REQ-007, REQ-008, REQ-010, REQ-011)

```
Authenticated user → POST /core-action (request with session cookie)
  → validate_session() middleware: verifies session token against session_tokens table [C:Api_Contracts]
  → COMP-007 (CoreAction Blueprint): receives validated request
  → COMP-010 (Permission Guard Decorator): checks session user role for CORE_ACTION_EXECUTE
      → If denied: COMP-016 records permission-denial audit entry; 403 returned immediately; halt
  → COMP-009 (Input Validator): validates all fields
      → If any field fails: 422 returned with field-keyed error map; halt
  → COMP-008 (CoreAction Service) begins orchestration:
      → COMP-013 (Section Lock Coordinator): acquire lock on target resource section
          → If lock denied: 409 returned; halt
      → COMP-011 (CoreAction Repository): open DB transaction; persist CoreActionRecord (status=pending)
      → COMP-016 (Audit Log Writer): append action_initiated entry
      → COMP-011: update CoreActionRecord (status=completed); commit transaction
      → COMP-016: append action_completed entry
      → COMP-014 (SSE Publisher): write HandoverChange event record to DB
  → COMP-007: return 200 with CoreAction confirmation payload
  [Target: ≤ 100 ms from request receipt to HTTP response delivered to initiating user]
```

#### DF-05 — Concurrent Lock Conflict (REQ-009)

```
User B → POST /core-action on a section locked by User A
  → validate_session(), COMP-007, COMP-010, COMP-009 all pass
  → COMP-008 → COMP-013: lock acquire attempted
      → SectionLock already held by User A: coordinator returns LOCK_DENIED with lock-holder identity
  → COMP-008 returns conflict signal to COMP-007
  → COMP-007: 409 Conflict with lock-holder message; no data written; resource consistent
```

#### DF-06 — Dependency Failure / Degradation (REQ-012)

```
COMP-008 (CoreAction Service) executing
  → DB call within COMP-011 or COMP-013 raises timeout or connection error
  → COMP-008 catches exception; delegates to COMP-015 (Degradation Logger)
  → COMP-015: structured log entry written (exception type, dependency, user_id, resource_id, timestamp)
  → COMP-011: DB transaction rolled back; no CoreActionRecord row persisted
  → COMP-008 returns degradation signal to COMP-007
  → COMP-007: 503 with degradation notice body
  [User session remains active; all other platform routes unaffected]
```

#### DF-07 — Expired Session on Submission (EC-02)

```
User submits POST /core-action with expired session cookie
  → validate_session() middleware: token absent or expired in session_tokens table [C:Api_Contracts]
  → Request short-circuited at middleware level before reaching COMP-007
  → 401 response; client redirected to /login or /sso/login
```

#### DF-08 — Mid-Operation Server Error with Rollback (AC-007b, EC-04)

```
COMP-011 write succeeds; COMP-016 or COMP-014 raises unrecoverable exception
  → COMP-008 catches; marks transaction for rollback
  → COMP-011: DB transaction rolled back; CoreActionRecord not persisted
  → COMP-015: internal log entry written with full exception context
  → COMP-007 catch-all: 500 with non-revealing error message; internal log entry
  [User may safely retry; no partial state exists in DB]
```

#### DF-09 — SSE Peer Delivery (REQ-011)

```
COMP-014 (SSE Publisher): HandoverChange event row inserted into DB change log
  → Existing SSE DB-polling loop [C:Api_Contracts]: detects new row on next poll cycle
  → SSE event pushed to all connected peer clients subscribed to that resource
  [Peer latency bounded by DB poll interval — see ADR-006 for 100 ms budget interpretation]
```

---

## API Contracts

> **Scope note:** The specific CoreAction operation has not yet been confirmed (Open Item #5, `docs/phase-2/interrogation_summary.md`). The `payload` field schema is a placeholder; it must be fully specified once the operation is identified. All other existing API response schemas remain unmodified. [C:Api_Contracts]

---

### `POST /core-action`

**Component:** COMP-007  
**Auth:** Active `Flask-Login` session with a server-side–validated session token. [C:Api_Contracts] Requests without a valid token are rejected by `validate_session()` before reaching this handler. Required permission: `CORE_ACTION_EXECUTE` (evaluated by COMP-010).

**Request Schema:**

```
Content-Type: application/json

{
  "resource_id"  : string   [required | UUID format | non-empty]
  "section_id"   : string   [required | max 128 chars | non-empty]
  "payload"      : object   [required | non-null | structure confirmed per Open Item #5]
}
```

**Success Response — 200 OK:**

```json
{
  "status"         : "success",
  "core_action_id" : "<uuid>",
  "resource_id"    : "<uuid>",
  "section_id"     : "<string>",
  "completed_at"   : "<ISO-8601 UTC timestamp>",
  "actor"          : "<user_id>"
}
```

**Error Responses:**

| HTTP Status | Condition | Body Shape |
|-------------|-----------|------------|
| `401 Unauthorized` | No valid session token present | `{"error": "authentication_required", "redirect": "/login"}` |
| `403 Forbidden` | Valid session; `CORE_ACTION_EXECUTE` permission absent | `{"error": "permission_denied", "message": "<human-readable>", "required_permission": "CORE_ACTION_EXECUTE"}` |
| `404 Not Found` | `resource_id` does not identify an existing resource | `{"error": "resource_not_found", "resource_id": "<value>"}` |
| `409 Conflict` | Target section locked by another user | `{"error": "section_locked", "locked_by": "<user_id>", "expires_at": "<ISO-8601>", "message": "<human-readable>"}` |
| `422 Unprocessable Entity` | One or more input fields fail validation | `{"error": "validation_failed", "fields": {"<field_name>": "<field-specific error message>", ...}}` |
| `500 Internal Server Error` | Unrecoverable server-side error; transaction rolled back | `{"error": "server_error", "message": "An unexpected error occurred. Please try again or contact support."}` |
| `503 Service Unavailable` | Dependency timeout or unavailability; partial state rolled back | `{"error": "service_degraded", "message": "This feature is temporarily unavailable due to a service issue. Other parts of the application remain accessible."}` |

---

### `POST /core-action/<resource_id>/lock`

**Component:** COMP-007 → COMP-013  
**Auth:** Active validated session. Required permission: `CORE_ACTION_EXECUTE`.

**Request Schema:**

```
Path: resource_id [UUID]

Content-Type: application/json
{
  "section_id": string [required | non-empty | max 128 chars]
}
```

**Success Response — 200 OK:**

```json
{
  "status"     : "acquired",
  "lock_id"    : "<uuid>",
  "section_id" : "<string>",
  "expires_at" : "<ISO-8601 UTC timestamp>"
}
```

**Error Responses:**

| HTTP Status | Condition | Body Shape |
|-------------|-----------|------------|
| `401` | No valid session | `{"error": "authentication_required"}` |
| `403` | Insufficient permission | `{"error": "permission_denied"}` |
| `404` | Resource not found | `{"error": "resource_not_found", "resource_id": "<value>"}` |
| `409` | Section already locked | `{"error": "section_locked", "locked_by": "<user_id>", "expires_at": "<ISO-8601>"}` |

---

### `DELETE /core-action/<resource_id>/lock/<lock_id>`

**Component:** COMP-007 → COMP-013  
**Auth:** Active validated session. Lock ownership verified against session user — only the holding user may release.

**Success Response — 200 OK:**

```json
{
  "status"     : "released",
  "lock_id"    : "<uuid>",
  "section_id" : "<string>"
}
```

**Error Responses:**

| HTTP Status | Condition | Body Shape |
|-------------|-----------|------------|
| `401` | No valid session | `{"error": "authentication_required"}` |
| `403` | Lock held by a different user | `{"error": "permission_denied", "message": "Lock is not owned by the requesting user."}` |
| `404` | Lock not found or already expired | `{"error": "lock_not_found", "lock_id": "<value>"}` |

---

### `GET /core-action/stream`

**Component:** COMP-007 → COMP-014  
**Description:** SSE stream endpoint delivering real-time CoreAction change events to the connected client, using the existing DB-polling SSE infrastructure. [C:Api_Contracts]  
**Auth:** Active validated session required. Stream is user-scoped.

**Response:**

```
Content-Type: text/event-stream
Cache-Control: no-cache

event: core_action_change
data: {"core_action_id": "<uuid>", "event_type": "<string>", "resource_id": "<uuid>", "actor": "<user_id>", "timestamp": "<ISO-8601>"}

event: heartbeat
data: {}
```

**Error Handling:**

| Condition | Behaviour |
|-----------|-----------|
| No valid session | 401 before stream opens |
| DB poll failure | Stream emits `event: degraded\ndata: {}` then closes; COMP-015 logs internally |

---

## Data Models

### New Table: `core_action_records` — COMP-012

**File:** `models/core_action.py`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | `PRIMARY KEY, NOT NULL` | Auto-generated on insert |
| `resource_id` | UUID | `NOT NULL, FK → <target table per Open Item #5>` | Resource acted upon |
| `section_id` | VARCHAR(128) | `NOT NULL` | Section within resource |
| `actor_user_id` | VARCHAR(128) | `NOT NULL, FK → users/accounts table` | Initiating user |
| `status` | VARCHAR(32) | `NOT NULL, CHECK IN ('pending','completed','failed','rolled_back')` | State machine field |
| `payload` | JSONB | `NOT NULL` | Operation-specific data; schema confirmed per Open Item #5; encrypted at rest if payload contains sensitive fields (see Security §6) |
| `version` | INTEGER | `NOT NULL, DEFAULT 1` | Monotonically incrementing version counter |
| `created_at` | TIMESTAMPTZ | `NOT NULL, DEFAULT NOW()` | |
| `completed_at` | TIMESTAMPTZ | `NULLABLE` | Populated when `status = 'completed'` |
| `failure_reason` | TEXT | `NULLABLE` | Populated when `status IN ('failed', 'rolled_back')` |

**Indexes:**
- `idx_ca_record_resource_id` on `resource_id` — supports lock coordinator queries and per-resource lookups
- `idx_ca_record_actor` on `actor_user_id` — supports per-user history queries
- `idx_ca_record_status_created` on `(status, created_at)` — supports dashboard/reporting queries

**Relationships:**
- `resource_id` → FK to target handover/resource table (FK target confirmed when core action is identified per Open Item #5)
- `actor_user_id` → FK to existing user/accounts table

**Migration Notes:**
- Net-new table; no existing schema is altered.
- Migration script: `migrations/versions/<timestamp>_add_core_action_records.py`
- No backward compatibility impact.

---

### New Table: `core_action_audit_entries` — COMP-017

**File:** `models/core_action_audit.py`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | `PRIMARY KEY, NOT NULL` | |
| `core_action_id` | UUID | `NULLABLE, FK → core_action_records.id` | Null for denial events where no record was created |
| `event_type` | VARCHAR(64) | `NOT NULL, CHECK IN ('permission_denied','lock_denied','action_initiated','action_completed','action_failed','action_rolled_back')` | |
| `actor_user_id` | VARCHAR(128) | `NOT NULL` | Requesting user identity |
| `resource_id` | UUID | `NULLABLE` | Null when denial fires before resource resolution |
| `denied_operation` | VARCHAR(128) | `NULLABLE` | Populated for `permission_denied` events |
| `details` | JSONB | `NULLABLE` | Structured supplementary context (e.g., required permission, section_id) |
| `recorded_at` | TIMESTAMPTZ | `NOT NULL, DEFAULT NOW()` | Immutable write time |

**Constraints:**
- Application code issues no `UPDATE` or `DELETE` against this table. The row is append-only by convention enforced at the repository layer (COMP-016).
- `idx_ca_audit_actor` on `actor_user_id`; `idx_ca_audit_event_type` on `event_type`; `idx_ca_audit_recorded_at` on `recorded_at`

**Migration Notes:**
- Net-new table.
- Migration script: `migrations/versions/<timestamp>_add_core_action_audit_entries.py`

---

### Modified Artefact: `requirements.txt` — COMP-005

All 45+ entries migrated from range specifiers to `==` exact pins. The installed package set at runtime does not change if prior ranges had resolved to the versions now pinned explicitly. The specific pinned version of flask-sock is recorded once confirmed (Open Item #8, `docs/phase-2/interrogation_summary.md`). Compatibility is verified by `pip install -r requirements.txt` in a clean virtualenv (AC-004a) before the manifest is merged.

---

### Modified Artefact: Container Compose Files — COMP-006

- `docker-compose.prod.yml` (new): Contains no `volumes` directive targeting `/app`; the `app` service uses the image build artefact exclusively.
- `docker-compose.yml` (modified): Bind-mount isolated to `docker-compose.override.yml` (development-only). The production deployment automation exclusively references `docker-compose.prod.yml`. CI configuration lint validates that `docker-compose.prod.yml` contains no `/app` bind-mount (AC-005b).

---

## Decisions (ADRs)

---

### ADR-001 — Architecture Pattern: Monolith Extension vs. Microservice Extraction

**Context:** The CoreAction feature (REQ-007–012) must be integrated into `shifthandover_v3`. The platform is an established Flask monolith with ~45–48 blueprints. [C:Api_Contracts] A decision is needed on whether the feature extends the existing process or introduces a service boundary.

**Decision:** Extend the existing Flask monolith with a new CoreAction blueprint and supporting layered service components, following the same pattern in use for collaborative editing, handover management, and roster. [C:Api_Contracts]

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **A — Monolith extension (selected)** | Consistent with established blueprint pattern [C:Api_Contracts]; shares existing session validation, RBAC, and SectionLock infrastructure at zero network cost; lowest operational risk; no new deployment topology | Increases blueprint count; future independent scaling of CoreAction requires extraction at that time |
| **B — Separate microservice** | Independent deployability; isolated scaling; hard service boundary | Inter-service auth token propagation required; `validate_session()` is monolith-internal [C:Api_Contracts]; adds a network hop between permission check and action execution, threatening REQ-011; introduces significant out-of-scope infrastructure |
| **C — Inline within an existing blueprint** | Zero new files | Violates single-responsibility; business logic entangled with routing makes error handling and independent testing impractical |

**Consequences:**
- *Positive:* Proven auth, RBAC, SectionLock, SSE, and audit patterns reused without re-engineering. [C:Api_Contracts]
- *Negative:* Monolith surface grows; layer-separation discipline must be maintained via code review.
- *Risk:* The 100 ms latency budget (REQ-011) requires baseline validation — see Assumption A-04 and ADR-006.

---

### ADR-002 — Concurrent Modification Strategy: Pessimistic vs. Optimistic Locking

**Context:** REQ-009 requires that simultaneous modification attempts on the same resource section do not produce data corruption or inconsistency. The platform already operates a `SectionLock` pessimistic locking model for collaborative editing. [C:Api_Contracts]

**Decision:** Reuse the existing `SectionLock` pessimistic locking model via COMP-013. A lock acquire must succeed within the same DB transaction as the resource write; a failed acquire returns a structured 409 denial immediately.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **A — Pessimistic locking via SectionLock (selected)** | Consistent with existing collaborative model [C:Api_Contracts]; conflict prevented pre-write; deterministic outcome; no retry loop needed | Explicit lock lifecycle required; lock leaks if client disconnects (mitigated by lock TTL on existing `SectionLock`) |
| **B — Optimistic locking with version counter** | No lock acquisition overhead; higher throughput when conflicts are rare | Requires retry logic on conflict; the CoreAction is a single atomic operation (Assumption A-05) where retry adds complexity and user-perceived latency |
| **C — Last-write-wins** | Trivially simple to implement | Silently discards one concurrent user's modification — a direct violation of REQ-009 and AC-009b |

**Consequences:**
- *Positive:* Conflict is detected before any write occurs; AC-009b is satisfied without retry logic.
- *Negative:* Lock contention serialises concurrent requestors; second user receives an explicit denial.
- *Risk:* The `SectionLock` TTL must be reviewed against CoreAction expected execution time to prevent premature lock expiry during a valid operation.

---

### ADR-003 — Dependency Pinning Strategy: Manual `==` vs. `pip-compile`

**Context:** REQ-004 requires all 45+ Python dependencies pinned to exact versions. Two strategies are in common use: manually edited `==` specifiers in `requirements.txt`, or a generated lockfile via `pip-compile` / `pip-tools`.

**Decision:** Apply exact `==` specifiers directly in `requirements.txt` for all 45+ packages. COMP-004 enforces compliance in CI by scanning for any non-`==` specifier on every merge request.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **A — Manual `==` in `requirements.txt` (selected)** | No new tooling; single-file; compatible with existing `pip install -r` build step; COMP-004 enforces compliance in CI | Transitive dependency pinning is manual; dependency graph updates require manual version bumps |
| **B — `pip-compile` with `requirements.in` + lockfile** | Automatically pins transitive dependencies; generates complete reproducible lockfile | Introduces `pip-tools` as a new build dependency; changes developer workflow for adding packages; `requirements.in` vs `.txt` distinction requires team orientation |
| **C — Retain range specifiers (status quo)** | Zero effort | Violates REQ-004; permits silent breaking changes across environments; explicitly rejected |

**Consequences:**
- *Positive:* Immediate REQ-004 compliance; CI enforcement prevents regression.
- *Negative:* Transitive dependency pinning is managed manually; accepted as a known limitation for this scope.
- *Risk (A-06):* flask-sock pin compatibility is verified as a natural step of install validation; identified as low risk.

---

### ADR-004 — Container Configuration: Dev/Prod Compose Split vs. Single File Modification

**Context:** REQ-005 requires that the production container's `/app` directory be populated exclusively from the image build artefact. The existing `docker-compose.yml` contains a `.:/app` bind-mount. Development workflows likely depend on the bind-mount for hot-reload.

**Decision:** Introduce `docker-compose.prod.yml` as the authoritative production compose file (no `/app` bind-mount). A separate `docker-compose.override.yml` preserves the bind-mount for local development and is explicitly excluded from production deployment automation.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **A — Dev/prod compose split (selected)** | Production file is unambiguously safe; developer hot-reload preserved; CI lint validates `docker-compose.prod.yml` for absence of `/app` bind-mount (AC-005b) | Two files to maintain; risk of operators using the wrong file — mitigated by deployment runbook and CI lint |
| **B — Remove bind-mount from the single `docker-compose.yml` entirely** | Single source of truth; no ambiguity | Destroys local developer hot-reload; likely to be circumvented via ad-hoc command-line volume flags |
| **C — Environment-variable conditional in a single compose file** | Single file | Docker Compose YAML does not natively support conditional volume mounting; solutions are fragile and non-standard |

**Consequences:**
- *Positive:* REQ-005 satisfied in production; development workflow unaffected.
- *Negative:* Deployment runbook must reference `docker-compose.prod.yml`; operators must be oriented.
- *Risk:* A CI lint check must validate that `docker-compose.prod.yml` contains no `/app` bind-mount directive (AC-005b) — this check is incorporated into COMP-003.

---

### ADR-005 — CI Test Discovery: Directory Glob vs. Explicit File List

**Context:** REQ-006 requires all 10 regression pytest files to execute in CI. EC-06 identifies the risk that a newly added test file could be silently excluded if the CI configuration uses an explicit file list.

**Decision:** The `regression-tests` CI stage invokes `pytest tests/regression/` with directory-level discovery. pytest's default collection behaviour automatically includes new files added under that directory.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **A — Directory-glob discovery: `pytest tests/regression/` (selected)** | New files auto-included (EC-06 satisfied); minimal CI config; standard pytest convention | A file placed outside `tests/regression/` is silently excluded — mitigated by CODEOWNERS path rule and code review convention |
| **B — Explicit file list in `.gitlab-ci.yml`** | Precise control over exactly which files run | Violates EC-06: new files must be manually added to CI config; fragile as the suite grows; omissions go undetected |
| **C — Pytest marker-based selection (`-m regression`)** | Flexible grouping; works across directories | Requires decorating the 10 existing test files with markers — modifying test files is explicitly a non-goal |

**Consequences:**
- *Positive:* EC-06 satisfied without CI config changes per new test file.
- *Negative:* Files must be placed in `tests/regression/` — enforced by CODEOWNERS path rule in COMP-002.
- *Risk:* The Assumption A-01 CI dry-run validation gate must verify that all 10 files appear individually in pipeline output before REQ-006 is treated as satisfied.

---

### ADR-006 — Real-Time Delivery: DB-Poll SSE vs. WebSocket/Redis for 100 ms Target

**Context:** REQ-011 requires the initiating user to receive a visible result within 100 ms of their input. COMP-014 also delivers events to connected peer clients. The production platform uses DB-polling SSE with no Redis or WebSocket. [C:Api_Contracts]

**Decision:** For the **initiating user**, the 100 ms budget is satisfied by the synchronous HTTP response to `POST /core-action` (DF-04) — no SSE dependency. For **peer clients**, COMP-014 writes to the `HandoverChange` log and the existing SSE polling loop delivers the event on the next cycle. Peer SSE latency is bounded by the poll interval; REQ-011 targets the initiating user's input-to-response path, not peer delivery latency.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **A — Synchronous HTTP response + existing DB-poll SSE for peers (selected)** | Consistent with production architecture [C:Api_Contracts]; initiating user within 100 ms via HTTP response; no new infrastructure | Peer SSE latency bounded by poll interval, not 100 ms; acceptable given REQ-011's stated scope |
| **B — WebSocket + Redis pub-sub (YJS CRDT branch)** | Sub-poll-interval peer notification; richer presence semantics | Non-default production path [C:Api_Contracts]; introduces Redis as new production dependency; significant infrastructure and operational complexity; out of scope for CTCOAMSHM-115 [J:CTCOAMSHM-115] |
| **C — Client-side polling for result confirmation** | Simple | Adds visible latency proportional to poll interval; contradicts the direct-feedback expectation of REQ-011; inconsistent with platform SSE pattern [C:Api_Contracts] |

**Consequences:**
- *Positive:* No new infrastructure; 100 ms target for initiating user achievable via indexed DB write + HTTP response.
- *Negative:* Peer clients experience SSE poll-interval latency; acceptable for the confirmed feature scope.
- *Risk (A-04):* Baseline interactive latency measurement must precede treating 100 ms as a verified, testable target.

---

### ADR-007 — Permission Guard: Decorator vs. Blueprint `before_request` vs. Inline Check

**Context:** REQ-010 requires that permission checking fires before any business logic, with no partial execution on denial. The platform's `validate_session()` middleware runs on every request. [C:Api_Contracts] A dedicated RBAC enforcement point for CoreAction routes is needed.

**Decision:** Implement COMP-010 as a Python decorator applied to each CoreAction route handler function, composing atop the upstream `validate_session()` middleware.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **A — Decorator per route (selected)** | Explicit at the route level; independently unit-testable; permission requirement visible at the function declaration | Must be applied to each route handler; risk of omission on future routes — mitigated by code review and integration tests asserting 403 on unpermissioned requests |
| **B — Blueprint `before_request` hook** | Applied automatically to all routes in the blueprint | Blueprint must carry RBAC knowledge; harder to unit-test; a single blueprint hosting routes with different permission requirements cannot use a single hook cleanly |
| **C — Inline permission check within route handler** | No additional abstraction | Business and auth logic co-located; violates single-responsibility; duplicated across every handler; not testable in isolation |

**Consequences:**
- *Positive:* COMP-010 is independently testable; permission denial fires before COMP-008 is ever reached.
- *Negative:* Developer must consciously apply the decorator; mitigated by CODEOWNERS review and integration test coverage of 403 paths.
- *Risk:* A route without the decorator silently bypasses RBAC — integration tests asserting 403 for unpermissioned requests on every CoreAction endpoint are mandatory to catch this.

---

## Implementation Guidelines

### File Structure

| File Path | Status | Component | Purpose |
|-----------|--------|-----------|---------|
| `.gitlab-ci.yml` | Modified | COMP-003 | Add `regression-tests` stage; add dependency pin lint step; add docker-compose lint step |
| `.gitlab/approval_rules.yml` | New | COMP-002 | Declarative MR approval policy: min 1 Maintainer, self-approval disabled |
| `CODEOWNERS` | New | COMP-002 | Maps path patterns to Maintainer groups for approval eligibility |
| `requirements.txt` | Modified | COMP-005 | All 45+ packages pinned to exact `==` versions |
| `docker-compose.prod.yml` | New | COMP-006 | Production-safe compose; no `/app` bind-mount |
| `docker-compose.yml` | Modified | COMP-006 | Bind-mount isolated to override file only |
| `docker-compose.override.yml` | New | COMP-006 | Development-only bind-mount; excluded from production deployment |
| `scripts/validate_pins.py` | New | COMP-004 | Scans `requirements.txt` for non-`==` specifiers; exits non-zero on failure |
| `app.py` | Modified | COMP-007 | Register `core_action_bp` blueprint |
| `routes/core_action.py` | New | COMP-007 | CoreAction Flask Blueprint — route definitions and response serialisation only |
| `services/core_action_service.py` | New | COMP-008 | CoreAction business logic orchestrator |
| `validators/core_action_validator.py` | New | COMP-009 | Field-level input validation; returns structured `{field: message}` error map |
| `decorators/permission_guard.py` | New | COMP-010 | RBAC decorator enforcing `CORE_ACTION_EXECUTE` permission pre-business logic |
| `repositories/core_action_repository.py` | New | COMP-011 | DB read/write for CoreAction records within a single transaction boundary |
| `models/core_action.py` | New | COMP-012 | SQLAlchemy ORM model for `core_action_records` table |
| `models/core_action_audit.py` | New | COMP-017 | SQLAlchemy ORM model for `core_action_audit_entries` table |
| `services/section_lock_coordinator.py` | New | COMP-013 | Acquire/release wrapper over existing `SectionLock` model [C:Api_Contracts] |
| `services/sse_publisher.py` | New | COMP-014 | Writes `HandoverChange`-compatible event record to DB for SSE delivery |
| `services/degradation_logger.py` | New | COMP-015 | Captures dependency failures; writes structured internal log; returns degradation signal |
| `services/audit_log_writer.py` | New | COMP-016 | Append-only audit entry writer for permission-denial and action-lifecycle events |
| `migrations/versions/<ts>_add_core_action_records.py` | New | COMP-012 | Alembic migration: create `core_action_records` table |
| `migrations/versions/<ts>_add_core_action_audit_entries.py` | New | COMP-017 | Alembic migration: create `core_action_audit_entries` table |
| `tests/regression/` | Existing (10 files) | COMP-003 | Executed by COMP-003 CI stage — not modified per non-goal |
| `docs/ops/branch-protection.md` | New | COMP-001 | Operational documentation for GitLab protected branch configuration |

---

### Naming Conventions

Following conventions observable in the existing codebase: [C:Api_Contracts]

- Blueprint files: `snake_case.py` under `routes/` (e.g., `core_action.py`)
- Blueprint registration variable: `<domain>_bp` (e.g., `core_action_bp`)
- Service classes: `PascalCase` with `Service` suffix (e.g., `CoreActionService`)
- Repository classes: `PascalCase` with `Repository` suffix (e.g., `CoreActionRepository`)
- Validator classes/functions: `<Entity>Validator` class or `validate_<entity>` function
- Model classes: singular `PascalCase` matching table name (e.g., `CoreActionRecord`)
- DB table names: `snake_case` plural (e.g., `core_action_records`)
- Error response keys: `snake_case` strings throughout all JSON bodies
- CI stage names: `kebab-case` (e.g., `regression-tests`)

---

### Patterns to Use

| Pattern | Rationale |
|---------|-----------|
| Flask Blueprint per domain area | Consistent with the ~45-blueprint pattern already in production [C:Api_Contracts]; isolates route surface from service logic |
| Decorator-based RBAC guard (COMP-010) | Permission requirement visible at the declaration site; independently unit-testable (ADR-007) |
| DB transaction wrapping in repository (COMP-011) | Guarantees atomicity; enables full rollback on mid-operation failure (REQ-007, EC-04) |
| Structured `{field: message}` error response body | Enables per-field client-side rendering without additional parsing (REQ-008) |
| Append-only audit table (COMP-017) | Mirrors the existing `HandoverChange` immutability pattern [C:Api_Contracts]; preserves tamper-evident trail |
| SSE DB-poll for peer events (COMP-014) | Consistent with the canonical production real-time model [C:Api_Contracts]; introduces no new infrastructure |
|| Directory-glob pytest discovery in CI (COMP-003) | Automatically includes new test files; satisfies EC-06 without CI config changes (ADR-005) |

---

### Patterns to Avoid

| Anti-Pattern | Reason |
|-------------|--------|
| Business logic inside route handler functions (COMP-007) | Violates single-responsibility; couples HTTP concerns to domain logic; makes unit testing without an HTTP context impossible |
| Permission check inside service methods (COMP-008) | Permission denial must occur before any business logic executes (REQ-010); inlining the check inside the service allows the call frame to reach the service, creating a partial-execution window |
| `UPDATE` or `DELETE` against audit tables (COMP-017) | Audit integrity requires append-only writes; any mutability pathway defeats the evidentiary purpose of the log |
| Range specifiers (`>=`, `~=`, `>`) in `requirements.txt` | Introduces non-determinism between environments; violates REQ-004; blocked by COMP-004 in CI — any reintroduction causes pipeline failure |
| `/app` bind-mount in production compose configuration | Shadows the image COPY layer at runtime; violates REQ-005; detected by CI lint step on `docker-compose.prod.yml` |
| Explicit test file enumeration in `.gitlab-ci.yml` | Violates EC-06; a new file added to `tests/regression/` would be silently excluded; directory-glob is the mandated approach (ADR-005) |
| Catch-all exception handlers that swallow errors without logging or signalling | Violates REQ-012; every transient failure must produce an internal log entry via COMP-015 and a visible degradation response to the user |
| Bare `except Exception` around the entire route handler | Masks the error category, preventing appropriate HTTP status code mapping; COMP-007's catch-all is the last resort only, not a substitute for specific error handling at each call site |

---

### New Dependencies

No net-new Python library dependencies are introduced by any application component. All components consume existing Flask, SQLAlchemy, and Flask-Login primitives already present in `requirements.txt`. The `validate_pins.py` script (COMP-004) uses Python stdlib exclusively (`re`, `sys`, `pathlib`). No ADR for a new library is required.

---

## Testing Strategy

### Unit Tests

| Component | Scope | Location |
|-----------|-------|----------|
| COMP-009 (Input Validator) | Each validation rule in isolation: null field, empty string, UUID format failure, value exceeding max length, valid inputs that clear all rules. Every field-level error message string asserted by exact content. | `tests/unit/validators/test_core_action_validator.py` |
| COMP-010 (Permission Guard) | (1) Session with `CORE_ACTION_EXECUTE` — handler invoked; (2) Session without permission — 403 returned and COMP-016 trigger asserted; (3) No session — 401 returned before guard logic executes. | `tests/unit/decorators/test_permission_guard.py` |
| COMP-013 (Section Lock Coordinator) | Acquire when unlocked — success result; acquire when locked by another user — denial result with lock-holder identity; release by owning user — success; release attempt by non-owner — rejection. | `tests/unit/services/test_section_lock_coordinator.py` |
| COMP-015 (Degradation Logger) | Correct structured log event emitted for each exception category (timeout, connection error, generic); returned degradation signal structure matches the contract expected by COMP-008. | `tests/unit/services/test_degradation_logger.py` |
| COMP-016 (Audit Log Writer) | `permission_denied` entry written with correct `actor_user_id`, `denied_operation`, and `resource_id`; `action_completed` entry written with correct `core_action_id` and timestamp. | `tests/unit/services/test_audit_log_writer.py` |
| COMP-004 (Dependency Pin Validator) | Exits non-zero for manifests containing `>=`, `~=`, `>`; reports all offending package names; exits zero for an all-`==` manifest; handles empty file and comment-only lines gracefully. | `tests/unit/scripts/test_validate_pins.py` |

---

### Integration Tests

| Integration Surface | Scenario | Location |
|--------------------|----------|----------|
| COMP-007 → `validate_session()` → COMP-010 | Request with no session cookie → 401; request with session but role lacking `CORE_ACTION_EXECUTE` → 403 with correct body; 403 response triggers an audit entry row in `core_action_audit_entries`. | `tests/integration/test_core_action_auth.py` |
| COMP-007 → COMP-009 | POST with missing `resource_id` → 422 with `fields.resource_id` key; POST with invalid UUID → 422 with field-name and description; POST with null payload → 422. | `tests/integration/test_core_action_validation.py` |
| COMP-007 → COMP-008 → COMP-013 → COMP-011 → COMP-012 | Successful request → 200; `core_action_records` row exists with `status='completed'`; `core_action_audit_entries` row exists with `event_type='action_completed'`. | `tests/integration/test_core_action_happy_path.py` |
| COMP-007 → COMP-008 → COMP-013 | Second concurrent request on section locked by first user → 409 with `locked_by` populated; no `core_action_records` row inserted for the denied request. | `tests/integration/test_core_action_concurrency.py` |
| COMP-007 → COMP-008 → COMP-015 | Simulated DB timeout injected at COMP-011 write → 503; no `core_action_records` row persisted; internal log entry captured. | `tests/integration/test_core_action_degradation.py` |
| COMP-003 (CI dry-run) | All 10 files in `tests/regression/` appear individually in pipeline test-execution output — Assumption A-01 validation gate. Verified once via a manual CI dry-run before treating REQ-006 as satisfied. | CI pipeline output review |
| COMP-004 (CI pin lint) | CI pipeline stage with a deliberately malformed `requirements.txt` (one `>=` specifier injected) → stage exits non-zero and names the offending package. | `.gitlab-ci.yml` stage test |

---

### E2E Scenarios

| Scenario | Journey | Acceptance Tie |
|----------|---------|---------------|
| Happy-path CoreAction | Authenticated permissioned user submits valid CoreAction → 200 within 100 ms → confirmation rendered to initiating user | AC-007a, AC-011a |
| Permission denial | Authenticated user without `CORE_ACTION_EXECUTE` submits → 403 → no DB mutation → audit entry recorded | AC-010b |
| Unauthenticated access | No session cookie → 401 → redirect to `/login` | AC-010c |
| Input validation — empty field | Required field omitted → 422 with field name in error body | AC-008b |
| Input validation — invalid format | UUID field contains non-UUID value → 422 with format description | AC-008c |
| Concurrent lock conflict | User A acquires lock → User B submits CoreAction on same section → 409; User A's subsequent submission completes successfully | AC-009b |
| Mid-operation server error rollback | Fault injected post-lock, pre-commit → 500; `core_action_records` table contains no partial row | AC-007b |
| Branch protection enforcement | Developer attempts `git push origin develop` directly → push rejected with error message; no commit recorded on `develop` | AC-001b |
| Self-approval blocked | MR author attempts self-approval → approval not counted; MR blocked; independent Maintainer approval → merge permitted | AC-003b, AC-002a |
| CI test stage blocks merge on failure | Code change that breaks one regression test → regression-tests stage marked failed → MR blocked from merging | AC-006b |

---

### Coverage Approach

- COMP-009 and COMP-010 target **100% branch coverage** — both are pure or near-pure functions with a fully enumerable input space.
- Integration tests cover every documented HTTP error response (401, 403, 404, 409, 422, 500, 503) for `POST /core-action`.
- The 10 existing files under `tests/regression/` are executed as-is per REQ-006; their internal assertions are not modified (non-goal).
- Performance validation methodology (P50/P95/P99 percentile targets, automated vs. manual) is deferred pending agreement with the engineering lead before implementation begins (Assumption A-04, constraint in `docs/phase-2/problem_spec.md`).

---

## Security Considerations

### 1 — Authentication: Token Validation on Every Request

- **Concern:** A request reaching CoreAction endpoints without a valid server-side session.
- **Mitigation:** `validate_session()` executes on every inbound request, including all CoreAction routes. [C:Api_Contracts] Server-side session tokens in `session_tokens` are invalidated immediately on logout; no client-held credential can extend a terminated session. COMP-010 additionally asserts session presence as a precondition before any permission check runs.
- **OWASP:** A07:2021 — Identification and Authentication Failures

---

### 2 — Authorisation: RBAC Enforcement Before Business Logic

- **Concern:** An authenticated but unauthorised user reaching CoreAction business logic.
- **Mitigation:** COMP-010 short-circuits to 403 before COMP-008 is invoked — no partial execution occurs (REQ-010). Every denial event is recorded in `core_action_audit_entries` with `actor_user_id`, `denied_operation`, `resource_id`, and `recorded_at`. [J:CTCOAMSHM-115]
- **OWASP:** A01:2021 — Broken Access Control

---

### 3 — Input Validation: Injection and Malformed Input

- **Concern:** Malformed, oversized, or injection-bearing values reaching the DB or service layer.
- **Mitigation:** COMP-009 validates every field for type, length, format, and nullability before COMP-008 is invoked. COMP-011 uses SQLAlchemy ORM parameterised queries exclusively — no raw SQL string construction at any call site. The `payload` JSONB field is schema-validated in COMP-009 against the confirmed operation schema (Open Item #5) before persistence.
- **OWASP:** A03:2021 — Injection

---

### 4 — Concurrency: Lock Acquire and Write Atomicity

- **Concern:** A time-of-check/time-of-use race between lock verification and the resource write.
- **Mitigation:** COMP-013 acquires the `SectionLock` within the same DB transaction opened by COMP-011. Lock acquire and resource write are committed atomically — no window exists between check and write in which a second actor could interleave. [C:Api_Contracts]
- **OWASP:** A04:2021 — Insecure Design (race condition variant)

---

### 5 — PII Handling: User Identity in Audit and Internal Logs

- **Concern:** User identity appearing in audit entries and internal log sinks.
- **Mitigation:** `core_action_audit_entries` rows are stored in the DB under the existing RBAC access model — not in plaintext log files. COMP-015 writes `actor_user_id` (an opaque internal identifier) to log sinks — no display names, email addresses, or other PII. HTTP error response bodies surface only opaque IDs (`user_id`, `lock_id`); no PII is exposed in response payloads.
- **OWASP:** A02:2021 — Cryptographic Failures / PII exposure in logs

---

### 6 — Stored Data: Payload Encryption for Sensitive Fields

- **Concern:** The `payload` JSONB column in `core_action_records` may contain operationally sensitive data once the core action is identified (Open Item #5).
- **Mitigation:** If the confirmed payload schema contains sensitive fields, those fields are encrypted before persistence using the platform's existing Fernet-based `SecretsManager`. [C:Api_Contracts] The encryption requirement is binding once the payload schema is defined; it is a precondition for the data model migration being accepted into review.
- **OWASP:** A02:2021 — Cryptographic Failures

---

### 7 — Branch Protection: Resistance to Bypass

- **Concern:** A developer bypassing branch protection via direct GitLab API calls or elevated tokens.
- **Mitigation:** COMP-001 configures the protected branch rule at the GitLab server level. Modifying protected-branch rules requires a Maintainer-level personal access token; the pre-receive hook enforcement is not bypassable by ordinary repository push access. [J:CTCOAMSHM-115]
- **OWASP:** A08:2021 — Software and Data Integrity Failures

---

### 8 — Supply Chain: Dependency Manifest Integrity

- **Concern:** A dependency version range resolving to a malicious or breaking package version across environments.
- **Mitigation:** COMP-004 enforces `==` pinning on every merge-request CI run; any range specifier causes pipeline failure and blocks the merge. COMP-005 pins all 45+ packages. Hash-pinning via `--require-hashes` is a future hardening option outside this scope.
- **OWASP:** A08:2021 — Software and Data Integrity Failures

---

## Error Handling Strategy

### Propagation Chain

Errors propagate outward through the component chain without being silently absorbed at any intermediate layer:

```
DB / dependency layer
  raises: timeout, connection error, integrity constraint violation
    → COMP-011 / COMP-013
      raises typed exception or returns structured error result
        → COMP-008 (CoreAction Service)
          categorises error; delegates transient failures to COMP-015
            → COMP-015 (Degradation Logger)
              writes structured internal log entry; returns typed degradation signal
                → COMP-007 (CoreAction Blueprint)
                  maps service result to HTTP status code + JSON error body
                    → HTTP client receives appropriate status and user-facing message
```

COMP-007 holds a final catch-all that maps any exception that escapes COMP-008 to a 500 response with an internal log entry. The catch-all is not a substitute for per-category handling — it is a last-resort safety net only.

---

### User-Facing Messages vs. Internal Log Content

| Error Category | User-Facing Message | Internal Log Fields |
|----------------|--------------------|--------------------|
| Validation failure (COMP-009) | `{"fields": {"<field>": "<what failed and what is expected>", ...}}` | Input DTO snapshot + full field error map |
| Permission denied (COMP-010) | `"You do not have permission to perform this action."` + `required_permission` label | `actor_user_id`, `required_permission`, `session_id`, `timestamp` |
| Section locked (COMP-013) | `"This section is currently being edited by another user. Please try again shortly."` | `lock_id`, `lock_holder_user_id`, `resource_id`, `section_id`, `lock_expires_at` |
| Service degraded (COMP-015) | `"This feature is temporarily unavailable due to a service issue. Other parts of the application remain accessible."` | Full exception type, stack trace, dependency name, `actor_user_id`, `resource_id`, `timestamp` |
| Unrecoverable server error (COMP-007 catch-all) | `"An unexpected error occurred. Please try again or contact support."` | Full exception + sanitised request context (no raw body) |

---

### Retry Strategy

Proactive retry logic, fallback routing, and message queuing are explicitly out of scope. [J:CTCOAMSHM-115] The strategy for transient failures is:

1. COMP-015 logs the failure internally with full structured context.
2. COMP-011 rolls back the DB transaction — no partial `CoreActionRecord` row persists.
3. COMP-007 returns 503 with the degradation notice body.
4. The user may safely retry manually; transaction rollback guarantees idempotency (EC-04).

---

### Graceful Degradation

When a dependency failure is detected during CoreAction execution:

- The `CoreActionRecord` transaction is rolled back by COMP-011 — no partial state persists in any table.
- COMP-015 writes a structured internal log entry: exception type, dependency name, `actor_user_id`, `resource_id`, `section_id`, timestamp.
- COMP-007 returns 503 with the degradation notice body (see message above).
- The user's session remains active. All other platform routes — handover management, roster, admin, SSE streams, reporting — are unaffected, because the failure is isolated to the CoreAction service call chain.
- No circuit-breaker, retry queue, or fallback route is activated. This is the agreed degradation boundary, confirmed per Assumption A-03. [J:CTCOAMSHM-115]
- Visible degradation (the 503 response body) satisfies the "explicitly degraded rather than silently unavailable" contract of REQ-012 and AC-012b.

---

### Backward Compatibility

All changes are additive or internal to developer and build process:

- No existing HTTP API response schema is altered. [C:Api_Contracts]
- No existing session management contract changes. [C:Api_Contracts]
- Dependency pinning (`requirements.txt`) does not change the effective installed package set if prior range specifiers had resolved to the same versions; verified by install comparison (AC-004a).
- Container bind-mount removal does not alter application-observable behaviour — the image COPY directive and the bind-mount previously carried the same files; COPY becomes the sole source.
- CI addition of the regression test stage does not alter application behaviour; pre-existing failures may surface and block merges — this is the intended outcome.
- The CoreAction blueprint registers as a new route namespace; no existing blueprint route is modified, renamed, or removed.