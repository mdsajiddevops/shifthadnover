# Architecture Design Specification: ShiftOps — Archaeology Gap Remediation

---

## Meta

| Field | Value |
|---|---|
| **Ticket ID** | CTCOAMSHM-6 |
| **Project** | Shifthandover (ShiftOps / shifthandover_v3) |
| **Creation Date** | 2026-05-02 |
| **Spec Reference** | Functional Specification: ShiftOps — Archaeology Gap Remediation (Draft) |
| **Design Status** | Ready for Engineering Review |
| **Author** | Architecture Design Agent |

---

## Problem Spec Reference

The approved specification (CTCOAMSHM-6) identifies 18 requirements across 8 medium-severity gaps: an inconsistent application entrypoint (REQ-001/002), in-process background job scheduling that creates duplicate-execution risk under multi-worker deployment (REQ-003–006), hardcoded test credentials (REQ-007), an absent CI security stage (REQ-008), binary artefacts tracked in version control (REQ-009), untracked schema migration history (REQ-010/011), no peer-review enforcement on the primary branch (REQ-012), blocking scheduler status queries (REQ-013), no fail-fast startup validation (REQ-014), silently-failable audit operations (REQ-015), absent field-level form validation (REQ-016), and generic RBAC error responses (REQ-017/018). Full requirements, acceptance criteria, and constraints are documented in the approved specification. This document does not duplicate them.

---

## Current Architecture

### Existing Components Relevant to This Work

**Application Server:** The Flask application is started via `python app.py`, which uses Flask's built-in development server. This is the entrypoint targeted by `docker-compose.yml`. The development server is not suitable for production and does not support multi-worker operation.

**Background Job Scheduler:** APScheduler runs embedded within the Flask process. When `docker-compose.yml` starts two or more `web` service replicas, each replica spawns its own APScheduler instance, resulting in each scheduled job (email digest, ServiceNow poll, task retry handler, ctask assignment check) executing once per active process per trigger interval — a direct duplicate-execution risk.

**Celery Infrastructure:** Celery is already present in the codebase as a dependency, used for ad-hoc async task dispatch. A Celery worker process and Redis broker are referenced in configuration but are not the canonical execution path for the four scheduled job types. Celery Beat is not deployed.

**Scheduler Management Service:** `services/ctask_scheduler.py` exposes `start()`, `stop()`, `get_status()`, and `force_check()` operations. The current implementation calls APScheduler's internal API for state management. `routes/scheduler.py` maps these to HTTP endpoints.

**Authentication and Session Management:** `auth.py` and `routes/auth.py` handle local login. `routes/sso_auth.py` handles OAuth 2.0 / SAML via EPAM Microsoft identity provider. `validate_session()` middleware runs on every request, validating the `session_token` against the database. These mechanisms are not modified by this work.

**RBAC:** Authorization is enforced inline within each of the ~45–50 Blueprint route handler functions. There is no shared decorator or centralized policy object. No RBAC logic is removed or weakened by this work; the inline pattern is preserved.

**Test Configuration:** `tests/config.py` contains test credential values that include valid (non-localhost) credential strings mixed with configuration data. Three credential fields require extraction to environment variables.

**CI/CD Pipeline:** A `.gitlab-ci.yml` exists for the project. It does not currently include a security stage. No dependency CVE scan, SAST, or committed-secret detection job is defined.

**Version Control:** `.gitignore` does not currently exclude binary document formats (`.pdf`, `.doc`, `.docx`, `.xlsx`, `.pptx`). At least 4 binary document files are tracked in the repository history.

**Database Migrations:** `migrations/` contains Alembic revision files. An `ad-hoc SQL scripts` directory may also exist. No registry file (`README.md`) catalogs these artefacts with status and execution order.

### Patterns in Use

- **Server-Side Rendering:** All user-facing routes return rendered HTML via Jinja2 templates. Limited JSON endpoints exist for in-page operations.
- **Blueprint Modularisation:** Each domain area (handover, incidents, scheduler, etc.) is a separate Flask Blueprint registered in `app.py`.
- **Inline Authorization:** RBAC checks are written directly inside route handler functions with no decorator abstraction.
- **Fernet Encryption for Secrets:** OAuth credentials and sensitive config are stored encrypted in the database, loaded via `Config.init_from_database()` at startup.
- **Session-Token Database Validation:** Every request passes through `validate_session()`, which reads the `session_tokens` table.

### What is Modified vs. What is New

| File / Component | Status |
|---|---|
| `services/ctask_scheduler.py` | **Modified** — internal execution backing replaced with Celery |
| `routes/scheduler.py` | **Modified** — response format preservation; no URL changes |
| `docker-compose.yml` | **Modified** — CMD updated; worker and beat services added |
| `tests/config.py` | **Modified** — credentials sourced from env vars |
| `.gitlab-ci.yml` | **Modified** — security stage added |
| `.gitignore` | **Modified** — binary extensions added |
| `start.sh` | **New** |
| `gunicorn.conf.py` | **New** |
| `startup_checks.py` | **New** |
| `celery_app.py` | **New** |
| `celeryconfig.py` | **New** |
| `tasks/` package | **New** |
| `services/audit_service.py` | **New** |
| `utils/validators.py` | **New** |
| `utils/rbac_errors.py` | **New** |
| `migrations/README.md` | **New** |

---

## Architecture

### Pattern

**Layered Monolith with Separated Async Execution Tier.** The existing Flask monolith is retained as the HTTP-serving layer (no decomposition into microservices). A discrete Celery execution tier is formalized as the exclusive path for all background job execution. The two tiers communicate only through the Redis message broker and share no in-process scheduler state. This pattern is chosen because: (a) it closes REQ-003/005 without requiring application restructuring, (b) Celery Beat's single-process design provides native deduplication for scheduled jobs, eliminating the multi-worker duplicate-execution problem at the architectural level, and (c) it preserves all existing Blueprint contracts, session mechanics, and RBAC patterns.

---

### Components

| ID | Name | Type | Responsibility | Dependencies | File Path |
|---|---|---|---|---|---|
| **COMP-001** | Startup Script | Shell Script | Runs startup health checks and, on success, launches the Gunicorn process; serves as the sole container entrypoint. | COMP-002, COMP-004 | `start.sh` |
| **COMP-002** | Gunicorn Process Configuration | Configuration | Declares all Gunicorn server parameters (worker count, bind address, timeout, log level, access log format) in a version-controlled file. | — | `gunicorn.conf.py` |
| **COMP-003** | Container Orchestration Configuration | Configuration | Defines all service processes (web, worker, beat, redis) and their startup commands; the `web` service CMD is updated to invoke COMP-001. | COMP-001 | `docker-compose.yml` |
| **COMP-004** | Startup Health Checker | Utility Script | Validates that all required application secrets are present and decryptable and that the primary database is reachable; exits non-zero with a descriptive message on any failure. | — | `startup_checks.py` |
| **COMP-005** | Celery Application Factory | Service Module | Creates and configures the single shared Celery application instance, sourcing broker URL and result backend URL exclusively from environment variables. | COMP-006 | `celery_app.py` |
| **COMP-006** | Celery Periodic Schedule Configuration | Configuration Module | Declares the Celery Beat schedule: maps each of the four periodic job types to their task function reference and trigger interval. | COMP-007, COMP-008, COMP-009, COMP-010 | `celeryconfig.py` |
| **COMP-007** | Email Digest Task | Celery Task | Defines and executes the periodic email digest delivery job as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/email_tasks.py` |
| **COMP-008** | ServiceNow Polling Task | Celery Task | Defines and executes the periodic external ServiceNow API polling job as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/servicenow_tasks.py` |
| **COMP-009** | Task Retry Sweep Task | Celery Task | Defines and executes the periodic task retry handling sweep as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/retry_tasks.py` |
| **COMP-010** | CTask Assignment Check Task | Celery Task | Defines and executes the periodic ctask assignment verification job as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/ctask_tasks.py` |
| **COMP-011** | Dead-Letter Queue Handler | Celery Task / Service | Receives exhausted tasks (those that have consumed all retries), persists a record to the `failed_tasks` table, and dispatches an alert to the operations team. | COMP-005 | `tasks/dlq_handler.py` |
| **COMP-012** | Scheduler Management Service | Service | Exposes `start()`, `stop()`, `get_status()`, and `force_check()` operations backed exclusively by Celery; `get_status()` uses a bounded-timeout inspect call to remain non-blocking. | COMP-005, COMP-010 | `services/ctask_scheduler.py` |
| **COMP-013** | Scheduler HTTP Route Handler | Flask Blueprint | Maps HTTP requests to COMP-012 operations and formats responses; preserves all existing route paths, HTTP methods, and response shapes. | COMP-012 | `routes/scheduler.py` |
| **COMP-014** | Audit Transaction Service | Service | Executes handover record persistence and audit log writes within a single atomic database transaction; rolls back both operations if either fails and surfaces a specific error to the caller. | — | `services/audit_service.py` |
| **COMP-015** | Form Field Validator | Utility | Accepts a map of field names to submitted values and a validation rule set; returns a map of field names to actionable error messages for each invalid field, or an empty map if all fields are valid. | — | `utils/validators.py` |
| **COMP-016** | RBAC Error Message Resolver | Utility | Accepts the user's current role and the required role/privilege for a given operation; returns a specific, human-readable error message identifying the exact missing permission context. | — | `utils/rbac_errors.py` |
| **COMP-017** | CI/CD Pipeline Configuration | CI Configuration | Adds a `security` stage to the pipeline containing three jobs: dependency CVE scan (pip-audit), Python SAST (Bandit), and git history secret detection (GitLab template); the CVE scan job is configured as a blocking gate. | — | `.gitlab-ci.yml` |
| **COMP-018** | Version Control Ignore Rules | Configuration | Adds binary document extension patterns (`*.pdf`, `*.doc`, `*.docx`, `*.xlsx`, `*.pptx`) to prevent future tracking; includes a comment directing developers to the Confluence documentation source. | — | `.gitignore` |
| **COMP-019** | Test Credential Configuration | Test Configuration | Sources all three test credential values from named environment variables; falls back to localhost-only sentinel values when env vars are absent; includes a guard that aborts test execution if credentials are the sentinel values and the target is not localhost. | — | `tests/config.py` |
| **COMP-020** | Migration Registry | Documentation File | Catalogues every Alembic revision file and every ad-hoc SQL script in `migrations/` with its identifier, application status (applied / pending / superseded), and required execution order. | — | `migrations/README.md` |

---

### Data Flow

#### DF-01: Container Startup (REQ-001, REQ-002, REQ-014)

```
Container orchestration (docker-compose.yml / COMP-003)
  → invokes: start.sh (COMP-001)
      → invokes: startup_checks.py (COMP-004)
          → reads: required secrets from secrets store
          → attempts: primary database connectivity probe
          ← exits 1 + descriptive message if any check fails → Container exits; no port bound
          ← exits 0 if all checks pass
      → invokes: gunicorn with gunicorn.conf.py (COMP-002)
          → binds port 5000
          → starts 1 HTTP worker process
          ← serving HTTP requests
```

#### DF-02: Scheduled Background Job Execution (REQ-003, REQ-005, REQ-006)

```
Celery Beat process (configured via COMP-006)
  → at trigger interval: enqueues task message to Redis broker
      → Celery worker process dequeues message
          → executes task function (COMP-007 / COMP-008 / COMP-009 / COMP-010)
              → on success: task completes; result written to result backend
              → on transient failure (attempt ≤ 3):
                  → task re-enqueued with 30-second countdown delay
              → on final failure (attempt 3 exhausted):
                  → COMP-011 (DLQ handler) invoked
                      → writes record to failed_tasks table
                      → dispatches operations alert
```

> **Deduplication note:** Celery Beat is a single process separate from gunicorn workers. It enqueues each job exactly once per interval regardless of how many gunicorn HTTP workers are running, eliminating the duplicate-execution problem at the architectural level (REQ-005/EC-006).

#### DF-03: Scheduler Status Query (REQ-004, REQ-013)

```
HTTP client
  → GET /scheduler/status
      → routes/scheduler.py (COMP-013)
          → services/ctask_scheduler.get_status() (COMP-012)
              → celery.control.inspect(timeout=2.0)
                  → on broker available: returns live worker state
                  → on broker unavailable (timeout):
                      → returns degraded-state indicator object within ≤5s
          ← formats response (preserving existing response shape)
      ← HTTP 200 (nominal or degraded indicator)
```

#### DF-04: Scheduler Force Check (REQ-004)

```
HTTP client
  → POST /scheduler/force_check
      → routes/scheduler.py (COMP-013)
          → services/ctask_scheduler.force_check() (COMP-012)
              → ctask_tasks.run_ctask_assignment.delay() (COMP-010)
                  → task enqueued to Redis broker within ≤1s
          ← returns dispatch confirmation
      ← HTTP 200 with confirmation
```

#### DF-05: Handover Submission with Atomic Audit (REQ-015, REQ-016)

```
HTTP client (authenticated user)
  → POST /handover/submit (existing route, UNCHANGED path)
      → inline RBAC check (existing inline pattern)
          → on insufficient role: COMP-016 resolves specific error message ← HTTP 403 with role context
      → COMP-015 (Form Field Validator) validates all input fields
          → on validation failure: returns field-level error map ← HTTP 400 with field errors
      → COMP-014 (Audit Transaction Service)
          → opens database transaction
          → writes handover record
          → writes audit log entry
          → on both writes succeed: commits transaction ← HTTP 200 success
          → on either write fails: rolls back entire transaction ← HTTP 500 with specific error
```

#### DF-06: CI Security Gate (REQ-008)

```
Developer pushes to branch
  → GitLab CI pipeline triggered (.gitlab-ci.yml / COMP-017)
      → security stage (runs before merge is permitted):
          → job: dependency-scan
              → pip-audit scans requirements.txt
              → on CVE found: job fails, CVE ID + package reported; pipeline blocked
              → on clean: job passes
          → job: sast
              → Bandit scans Python source under src/
              → on HIGH severity finding: job fails
              → on clean or LOW/MEDIUM (configurable): job passes
          → job: secret-detection
              → GitLab Secret Detection template scans full git history
              → on secret found: job fails, commit reference reported
              → on clean: job passes
      → all three jobs must pass before merge to master is permitted
```

---

## API Contracts

> All scheduler endpoint paths, HTTP methods, and response content types are **unchanged** from the existing interface. Only the internal execution backing changes. Route handlers in COMP-013 translate between HTTP and COMP-012's service interface.

---

### ENDPOINT-001: Get Scheduler Status

| Field | Value |
|---|---|
| **HTTP Method** | `GET` |
| **Path** | `/scheduler/status` (existing, unchanged) |
| **Description** | Returns the current state of the Celery task queue workers and whether scheduled jobs are active. Must return within 5 seconds regardless of broker availability. |
| **Auth** | Session required; `team_admin` role minimum (existing RBAC check preserved). |

**Request:** No body. No query parameters.

**Success Response (200):**
```
{
  "status": "ok",                       // string enum: "ok" | "degraded"
  "workers_active": integer,            // count of live Celery workers; 0 if none
  "scheduled_jobs": [                   // array of job status objects
    {
      "name": string,                   // job identifier (e.g. "email_digest")
      "last_run": string | null,        // ISO-8601 datetime or null
      "next_run": string | null,        // ISO-8601 datetime or null
      "state": string                   // "active" | "idle" | "unknown"
    }
  ],
  "broker_reachable": boolean
}
```

**Degraded Response (200 — broker unavailable):**
```
{
  "status": "degraded",
  "workers_active": 0,
  "scheduled_jobs": [],
  "broker_reachable": false,
  "message": "Task queue broker unreachable; scheduler status unavailable"
}
```

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Session invalid or absent | 401 | Existing session error (unchanged) |
| Insufficient role | 403 | `{"error": "team_admin access is required to view scheduler status"}` |
| Inspect call times out | 200 | Degraded response (not 500) — see above |

---

### ENDPOINT-002: Start Scheduler

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/scheduler/start` (existing, unchanged) |
| **Description** | Signals Celery Beat to begin processing its configured periodic schedule. |
| **Auth** | Session required; `account_admin` role minimum. |

**Request:** No body required.

**Success Response (200):**
```
{
  "status": "ok",
  "message": "Scheduler started"
}
```

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Session invalid | 401 | Existing session error |
| Insufficient role | 403 | `{"error": "account_admin access is required to start the scheduler"}` |
| Broker unavailable | 503 | `{"error": "Scheduler unavailable: task queue broker is unreachable"}` |

---

### ENDPOINT-003: Stop Scheduler

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/scheduler/stop` (existing, unchanged) |
| **Description** | Signals Celery Beat to pause its periodic schedule. In-flight tasks are not cancelled. |
| **Auth** | Session required; `account_admin` role minimum. |

**Request:** No body required.

**Success Response (200):**
```
{
  "status": "ok",
  "message": "Scheduler stopped"
}
```

**Error Responses:** Same shape as ENDPOINT-002.

---

### ENDPOINT-004: Force Check (Immediate CTask Assignment Dispatch)

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/scheduler/force_check` (existing, unchanged) |
| **Description** | Immediately enqueues a single ctask assignment check job to the Celery task queue, bypassing the periodic schedule. Responds within 1 second. |
| **Auth** | Session required; `team_admin` role minimum. |

**Request:** No body required.

**Success Response (200):**
```
{
  "status": "ok",
  "message": "Assignment check dispatched",
  "task_id": string   // Celery task UUID for tracking
}
```

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Session invalid | 401 | Existing session error |
| Insufficient role | 403 | `{"error": "team_admin access is required to force a scheduler check"}` |
| Broker unavailable | 503 | `{"error": "Force check failed: task queue broker is unreachable"}` |

---

### ENDPOINT-005: Handover Submission (Modified Behavior)

> **Path and method are unchanged.** Only the internal execution model changes to enforce atomic audit writes (REQ-015) and field-level validation (REQ-016).

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/handover/submit` (existing, unchanged) |
| **Description** | Submits a completed handover. Validates all fields, checks RBAC, then atomically writes the handover record and audit log entry. |
| **Auth** | Session required; `user` role minimum. |

**Request Body:** Existing form fields (unchanged). All fields are now explicitly validated by COMP-015 before processing.

**Success Response:** Existing success response (unchanged — rendered HTML redirect or JSON confirmation per existing content type).

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Field validation failure | 400 | `{"errors": {"field_name": "actionable message", ...}}` |
| Insufficient role | 403 | `{"error": "user access is required to submit a handover; approval requires team_admin"}` |
| Audit log write failure (triggers rollback) | 500 | `{"error": "Handover submission failed: audit record could not be written. No data was saved. Please retry."}` |
| Database connectivity failure | 500 | `{"error": "Handover submission failed: database unavailable. Please retry."}` |

---

## Data Models

### New Table: `failed_tasks`

Stores records of Celery tasks that have exhausted all retry attempts, enabling operator inspection and recovery. Written exclusively by COMP-011.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Surrogate key |
| `celery_task_id` | VARCHAR(255) | NOT NULL, UNIQUE | Celery-assigned task UUID |
| `task_name` | VARCHAR(255) | NOT NULL | Fully qualified task function name (e.g., `tasks.email_tasks.send_digest`) |
| `task_args` | JSON | NOT NULL | Positional arguments passed to the task at dispatch |
| `task_kwargs` | JSON | NOT NULL | Keyword arguments passed to the task at dispatch |
| `error_message` | TEXT | NOT NULL | Exception message from the final failure |
| `error_trace` | TEXT | NOT NULL | Full traceback from the final failure |
| `failure_count` | INTEGER | NOT NULL, DEFAULT 3 | Number of attempts made before DLQ routing |
| `failed_at` | DATETIME | NOT NULL | Timestamp of the final failure (UTC) |
| `alerted_at` | DATETIME | NULLABLE | Timestamp when the operations alert was dispatched |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'failed' | Enum: `failed` \| `alerted` \| `resolved` |
| `resolved_at` | DATETIME | NULLABLE | Timestamp when an operator marked the task resolved |
| `resolved_by` | VARCHAR(255) | NULLABLE | User identifier of the resolving operator |

**Relationships:** No foreign keys. Standalone audit table.

**Indexes:** `idx_failed_tasks_status` on `(status)` for operator queue views; `idx_failed_tasks_task_name` on `(task_name)` for per-job DLQ queries.

**Migration Notes:** This is a new table requiring a new Alembic migration. The migration file must be created via `flask db migrate -m "add_failed_tasks_table"` and registered in `migrations/README.md` (COMP-020) before merging.

---

### Existing Table: `audit_log` (Behavioral Contract Change — No Schema Change)

No schema modification. The behavioral contract changes: all writes to `audit_log` that accompany a handover submission are now executed within the same SQLAlchemy transaction as the handover record write (enforced by COMP-014). If the audit log write raises any exception, the transaction is rolled back and neither record is persisted. The table structure, column definitions, and existing indexes are preserved exactly.

---

### Celery Result Backend State (Redis — No Application DB Table)

Celery task results (for non-exhausted tasks) are stored in Redis using Celery's built-in result backend. This is not managed by the application's Alembic migrations. Key schema elements:

- **Key pattern:** `celery-task-meta-{task_uuid}` (Redis string)
- **Value:** JSON object with fields: `task_id`, `status` (`PENDING` \| `STARTED` \| `SUCCESS` \| `FAILURE` \| `RETRY`), `result`, `traceback`, `date_done`
- **TTL:** Configurable via `CELERY_RESULT_EXPIRES` (recommended: 86400 seconds / 24 hours)

Application code must not read from the Celery result backend directly. COMP-012's `get_status()` uses `celery.control.inspect()`, not result backend reads.

---

## Decisions (ADRs)

### ADR-001: Overall Architecture Pattern — Monolith + Discrete Async Execution Tier

**Context:** ShiftOps is a Flask monolith. Background jobs currently execute within the HTTP-serving process via APScheduler. With multi-worker deployment, each worker spawns its own APScheduler instance, causing every job to execute once per worker per interval. The system needs a reliable scheduling mechanism that works correctly regardless of HTTP worker count.

**Decision:** Retain the Flask monolith as the HTTP-serving layer. Establish Celery (backed by Redis) as the exclusive execution tier for all background jobs. Celery Beat runs as a separate, single process and enqueues tasks; Celery workers dequeue and execute them. The HTTP workers have no scheduler. This eliminates duplicate execution at the architectural level: only one Beat process exists, so each job is enqueued exactly once per interval regardless of HTTP worker count.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Keep APScheduler, configure master-process election** | No new infrastructure dependency; avoids Celery rollout | Fragile — leader election in APScheduler requires external lock (Redis anyway); adds complexity without eliminating the dependency; does not satisfy REQ-003 (jobs still in HTTP process) |
| **A2: Full microservice decomposition** | Clean separation of concerns; independent scaling per service | Requires extensive refactoring of all ~45–50 Blueprints; weeks of work; explicitly out of scope; introduces network latency and distributed transaction complexity |
| **A3: Do nothing — disable APScheduler in workers via `--preload` flag** | Zero code change | Requires Gunicorn `--preload` which only works with fork-based workers; fragile; does not work in all deployment configurations; does not satisfy REQ-003 |
| **A4 (Chosen): Flask monolith + Celery execution tier** | Celery Beat single-process design guarantees deduplication; minimal refactoring of HTTP tier; established Python pattern; clear operational model | Adds Redis as a required infrastructure dependency; Celery Beat is a new process to operate; worker health monitoring required |

**Consequences:**
- ✅ Duplicate job execution impossible by design (REQ-005)
- ✅ HTTP tier fully isolated from task queue availability for non-critical operations (REQ-013)
- ✅ Retry and DLQ mechanics are Celery-native, not custom-built (REQ-006)
- ⚠️ Redis and Celery worker availability become operational dependencies; addressed by assumption A-002/A-003 and monitoring open items

---

### ADR-002: Message Broker and Result Backend — Redis

**Context:** Celery requires a message broker for task transport and (optionally) a result backend for task state storage. The choice of broker affects operational complexity, HA requirements, and existing infrastructure.

**Decision:** Redis serves as both the message broker and the result backend. The broker URL and result backend URL are sourced exclusively from environment variables (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`); they do not appear in source code or version-controlled configuration files.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: RabbitMQ as broker, Redis as backend** | RabbitMQ has stronger message durability guarantees; native dead-letter exchange support | Adds a second infrastructure component; higher operational complexity; no existing deployment; Celery supports Redis broker fully for this workload |
| **A2: Redis for broker + SQLAlchemy for result backend** | Result state visible in application DB without extra tooling | Adds DB load for every task state update; slower; not recommended for high-throughput Celery usage |
| **A3 (Chosen): Redis for both broker and result backend** | Single infrastructure component; already referenced in project configuration; fast; widely supported by Celery; simpler operational model | Redis is a single point of failure if not replicated; result TTL must be managed to prevent memory growth |

**Consequences:**
- ✅ Single broker service to deploy and monitor
- ✅ Broker URL never appears in source code (security constraint satisfied)
- ⚠️ Redis HA (replication/sentinel) is required for production reliability; deployment manifests must specify this

---

### ADR-003: WSGI Server — Gunicorn

**Context:** Flask's built-in development server is not suitable for production. A production-grade WSGI server is required. The application is synchronous and CPU-light (background work is delegated to Celery).

**Decision:** Gunicorn is the WSGI server. Initial configuration: 1 worker, bound to `0.0.0.0:5000`, with server parameters declared in `gunicorn.conf.py`. The worker count is explicitly set to 1 at initial deployment; scaling policy is deferred (non-goal).

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: uWSGI** | Feature-rich; native process management; supports Emperor mode for multi-app | Complex configuration syntax; heavier operational footprint; unnecessary for a single synchronous Flask app |
| **A2: Uvicorn / ASGI** | Async-native; high throughput for I/O-bound workloads | Requires rewriting Flask app in async style (or wrapping); substantial code change; out of scope |
| **A3 (Chosen): Gunicorn** | Official Flask/Django recommendation; simple configuration; well-documented; supports pre-fork multi-worker if scaling is needed later | Not async-native (not needed for this workload); requires explicit worker count decision |

**Consequences:**
- ✅ Production-safe server process with proper signal handling (REQ-002)
- ✅ Configuration in `gunicorn.conf.py` is version-controlled and auditable
- ✅ Worker count scaling possible without code changes (add `-w N` to config file)

---

### ADR-004: APScheduler Removal Strategy — Complete Removal

**Context:** APScheduler is embedded in the Flask process. The system needs all scheduled job execution removed from the HTTP tier. Two approaches exist: complete removal or hybrid disabling.

**Decision:** APScheduler is removed entirely from the application. All four job types are re-implemented as Celery tasks. The Celery Beat schedule in `celeryconfig.py` replaces all APScheduler job registrations. No APScheduler import shall remain in any module (verified by static code search, per AC-003c).

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Keep APScheduler for local dev, Celery Beat for production** | Simpler local development without Redis | Two scheduler code paths to maintain; risk of production-like bugs not caught in dev; violates REQ-003 (no execution in HTTP process) |
| **A2: Keep APScheduler but configure it to run only in Gunicorn master process** | Avoids Celery Beat setup | Fragile; depends on Gunicorn worker model internals; breaks with `--preload` changes; still violates REQ-003 |
| **A3 (Chosen): Complete removal** | Clean; verifiable via static search (AC-003c); single execution model in all environments | Requires local development to run Redis + Celery worker; addressed by docker-compose dev configuration |

**Consequences:**
- ✅ Zero risk of in-process scheduled execution in any environment (REQ-003)
- ✅ Statically verifiable: `grep -r "APScheduler\|apscheduler" .` must return zero matches
- ⚠️ Local development requires Redis and a Celery worker; `docker-compose.yml` must include both in the dev profile

---

### ADR-005: Dead-Letter Queue Storage — Hybrid (Celery Mechanics + Application DB Record)

**Context:** REQ-006 requires exhausted tasks to be "moved to a dead-letter queue" and trigger an operations alert. The mechanism must make failed tasks recoverable by an operator.

**Decision:** Celery handles retry mechanics natively (max_retries=3, countdown=30). When a task exhausts retries, Celery invokes the task's `on_failure` callback, which calls COMP-011 (DLQ handler). COMP-011 writes a record to the application database `failed_tasks` table (full context: task name, args, error trace, timestamps) and dispatches an operations alert. The application DB table is the operator-visible DLQ; it is separate from Celery's internal result backend.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Celery result backend only (Redis)** | Zero additional schema; uses Celery's built-in failure state | Operator must use Celery monitoring tooling (Flower) to inspect; results expire per TTL; no structured alerting hook |
| **A2: Dedicated Celery "dead_letter" queue** | Native Celery mechanism; no custom code | Queue contents expire with Redis; no structured record for compliance/audit; alerting requires separate Celery signal wiring anyway |
| **A3 (Chosen): Hybrid (Celery retries + DB DLQ record on exhaustion)** | Operator-visible in existing application DB; structured record with full context; natural alerting hook; recoverable without Celery tooling | Requires one new DB table + migration; COMP-011 is a new component |

**Consequences:**
- ✅ Operators can inspect and resolve failed tasks via existing DB tooling (REQ-006)
- ✅ Full context (args, trace, timestamps) preserved for forensic analysis (EC-003)
- ⚠️ `failed_tasks` table adds a new migration; must be registered in COMP-020

---

### ADR-006: Startup Health Check Integration — Pre-Start Script

**Context:** REQ-014 requires the application to abort startup and emit a descriptive error if secrets are absent/undecryptable or the database is unreachable. The check must execute before any HTTP port is bound.

**Decision:** A dedicated `startup_checks.py` module (COMP-004) is invoked by `start.sh` (COMP-001) before Gunicorn is launched. If `startup_checks.py` exits with a non-zero code, `start.sh` propagates the non-zero exit and does not invoke Gunicorn. This executes once per container start, not per Gunicorn worker.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Inline in Flask `app.py` factory** | No new file; runs at app import time | Runs once per Gunicorn worker fork; harder to distinguish startup failure from runtime error; port may be partially bound before all workers fail |
| **A2: Kubernetes liveness/readiness probe** | Standard cloud-native pattern | Out of scope for this iteration; does not address the "abort before port binding" requirement; requires K8s environment |
| **A3 (Chosen): Dedicated pre-start script** | Runs exactly once before port binding; clean separation; non-zero exit prevents Gunicorn start; easily testable in isolation | One extra file to maintain; Gunicorn must not be launched until `startup_checks.py` exits 0 |

**Consequences:**
- ✅ Container exits with non-zero code and descriptive message within 10 seconds on any startup failure (REQ-014, AC-014a/b)
- ✅ No partially initialised server state
- ⚠️ `startup_checks.py` must import the application's secrets manager and DB layer without starting the full Flask app; import isolation must be verified

---

### ADR-007: CI Security Tooling Selection

**Context:** REQ-008 requires three security checks in CI: dependency CVE scan, Python SAST, and committed-secret detection. The tools must integrate with GitLab CI/CD.

**Decision:** 
- **Dependency CVE scan:** `pip-audit` — scans `requirements.txt` against PyPI Advisory Database and OSV. Pipeline-blocking on any CVE finding.
- **Python SAST:** `Bandit` — scans Python source code for common security issues. Configurable severity threshold (HIGH-level findings are blocking).
- **Secret detection:** GitLab's native `Secret Detection.gitlab-ci.yml` template — scans full git history for committed secrets using GitLab's built-in ruleset. Pipeline-blocking on any finding.

All three tools are version-pinned in `.gitlab-ci.yml` to prevent unexpected behaviour on tool updates.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Safety + Semgrep + git-secrets** | Semgrep has broader language support; Safety is widely used | Safety requires paid tier for full CVE database; Semgrep rules require configuration for Python; `git-secrets` requires separate installation |
| **A2: Snyk** | Comprehensive; developer-friendly dashboard; PR comments | Commercial licensing cost; external data transmission of dependency list; over-engineered for this scope |
| **A3 (Chosen): pip-audit + Bandit + GitLab template** | All open-source or GitLab-native; zero licensing cost; pip-audit covers PyPI Advisory Database; GitLab template is maintained by GitLab; Bandit is the Python SAST standard | pip-audit requires network access to advisory DB during CI run; Bandit produces false positives that require suppression configuration |

**Consequences:**
- ✅ Zero additional licensing cost
- ✅ GitLab secret detection template is maintained and updated by GitLab (REQ-008)
- ⚠️ Bandit false-positive suppression (`# nosec` annotations) must be governed by code review to prevent abuse; reviewer checklist must include validation of any `# nosec` addition

---

## Implementation Guidelines

### File Structure

All files to be created or modified, with purpose and owning component:

| File | Action | Component | Purpose |
|---|---|---|---|
| `start.sh` | Create | COMP-001 | Container entrypoint; calls startup checks then launches Gunicorn |
| `gunicorn.conf.py` | Create | COMP-002 | Gunicorn server parameters (workers=1, bind, timeout, log format) |
| `docker-compose.yml` | Modify | COMP-003 | Update `web` CMD; add `worker`, `beat`, `redis` services |
| `startup_checks.py` | Create | COMP-004 | Validates secrets decryptability and DB reachability before port binding |
| `celery_app.py` | Create | COMP-005 | Celery application instance factory; reads broker/backend from env vars |
| `celeryconfig.py` | Create | COMP-006 | Celery Beat schedule; maps job names to task references and intervals |
| `tasks/__init__.py` | Create | — | Package init; enables Celery autodiscovery |
| `tasks/email_tasks.py` | Create | COMP-007 | Email digest Celery task; retry policy; DLQ routing |
| `tasks/servicenow_tasks.py` | Create | COMP-008 | ServiceNow polling Celery task; retry policy; DLQ routing |
| `tasks/retry_tasks.py` | Create | COMP-009 | Task retry sweep Celery task; retry policy; DLQ routing |
| `tasks/ctask_tasks.py` | Create | COMP-010 | CTask assignment check Celery task; retry policy; DLQ routing |
| `tasks/dlq_handler.py` | Create | COMP-011 | DLQ record write + operations alert dispatch |
| `services/ctask_scheduler.py` | Modify | COMP-012 | Replace APScheduler backing with Celery inspect + task dispatch |
| `routes/scheduler.py` | Modify | COMP-013 | Preserve routes; update to call modified service; preserve response shapes |
| `services/audit_service.py` | Create | COMP-014 | Atomic handover + audit log transaction manager |
| `utils/validators.py` | Create | COMP-015 | Field-level form validation utility; returns structured error map |
| `utils/rbac_errors.py` | Create | COMP-016 | Permission-specific error message generator |
| `.gitlab-ci.yml` | Modify | COMP-017 | Add `security` stage with three jobs |
| `.gitignore` | Modify | COMP-018 | Add binary document extension patterns |
| `tests/config.py` | Modify | COMP-019 | Replace hardcoded credentials with env var reads + sentinel fallbacks |
| `migrations/README.md` | Create | COMP-020 | Migration catalogue with status and execution order |
| `migrations/versions/XXXXXX_add_failed_tasks.py` | Create | — | Alembic migration for `failed_tasks` table; registered in COMP-020 |

### Naming Conventions

- **Task functions:** Snake-case verb-noun format — `send_email_digest`, `poll_servicenow`, `check_ctask_assignments`. Matches existing route handler naming style.
- **Service methods:** Snake-case — `get_status()`, `force_check()` (preserve existing names exactly for backward compatibility).
- **Validator functions:** Named `validate_{form_name}_fields(data: dict) -> dict` — e.g., `validate_handover_fields`.
- **RBAC error resolver:** Named `resolve_rbac_error(user_role: str, required_role: str, action: str) -> str`.
- **Component IDs:** Prefix `COMP-` followed by three-digit zero-padded integer, as defined in this document.
- **Environment variables:** `SCREAMING_SNAKE_CASE` — `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`.

### Patterns to Use

- **Celery `bind=True` tasks:** All four task functions must use `self` reference for retry calls (`self.retry(exc=..., countdown=30)`). This is the standard Celery retry pattern.
- **SQLAlchemy session as context manager:** COMP-014 must use `db.session` as an explicit transaction context. The session must not be auto-committed; commit must be the final operation, and exceptions must trigger explicit rollback before re-raising.
- **Result-typed service returns:** COMP-012 service methods must return a structured dict (not raise exceptions) for non-fatal broker failures, to support the degraded-state response contract of ENDPOINT-001.
- **Blueprint `errorhandler` for 400/403:** COMP-013 and all routes that call COMP-015/016 must register local `errorhandler` decorators for `400` and `403` to ensure the structured error format is returned consistently.
- **Gunicorn `--config` flag:** `start.sh` must pass `--config gunicorn.conf.py` to Gunicorn, not inline all parameters on the command line. This keeps configuration version-controlled and auditable.

### Patterns to Avoid

- **`APScheduler` imports anywhere in the codebase** — must be completely removed. The static verification `grep -r "apscheduler" .` must return zero matches before merge.
- **Credentials in source code** — broker URL, result backend URL, and all test credentials must never appear as literals. Use environment variables exclusively.
- **Blocking I/O in `get_status()`** — the `celery.control.inspect()` call must always specify an explicit `timeout` parameter (≤ 2.0 seconds). Never use the default (which blocks indefinitely).
- **Shared SQLAlchemy session across tasks** — Celery tasks must obtain their own database session within the task function body. Sessions must not be shared between the HTTP tier and task workers.
- **Silent exception swallowing in audit operations** — COMP-014 must never catch exceptions without re-raising them after rollback. Catching and logging without re-raising would produce the silent partial-commit failure that REQ-015 prohibits.
- **`# nosec` annotations added without reviewer justification** — any Bandit suppression must be accompanied by a code comment explaining why the finding is a false positive, and must be explicitly validated in code review.

### New Dependencies

| Package | Version Pin | Purpose | ADR |
|---|---|---|---|
| `gunicorn` | Pinned (e.g., `==21.x.x`) | Production WSGI server (REQ-002) | ADR-003 |
| `celery[redis]` | Pinned (e.g., `==5.x.x`) | Distributed task queue with Redis transport (REQ-003) | ADR-001, ADR-002 |
| `redis` | Pinned | Redis Python client (broker + result backend) | ADR-002 |
| `pip-audit` | CI-only, pinned | Dependency CVE scanning (REQ-008) | ADR-007 |
| `bandit` | CI-only, pinned | Python SAST (REQ-008) | ADR-007 |

> All new runtime dependencies must be added to `requirements.txt`. CI-only tools (`pip-audit`, `bandit`) must be added to a separate `requirements-ci.txt` to avoid polluting the production dependency set.

---

## Testing Strategy

### Unit Tests

Each of the following units requires isolated unit tests with all external dependencies mocked:

| Unit | Test Scope | Key Scenarios |
|---|---|---|
| `startup_checks.py` (COMP-004) | Validation logic | Missing secret exits non-zero; decryption failure exits non-zero; DB unreachable exits non-zero; all checks pass exits zero; error message identifies failing check by name |
| `celery_app.py` (COMP-005) | Configuration loading | Broker URL read from env var; raises on missing env var; Flask app context applied correctly |
| Each task in `tasks/` (COMP-007–010) | Task function logic | Success path; transient failure triggers retry with 30s countdown; retry count increments correctly; `max_retries` exhaustion calls COMP-011 |
| `tasks/dlq_handler.py` (COMP-011) | DLQ write + alert | DB write contains all required fields; alert dispatch called once; DB failure does not suppress alert |
| `services/ctask_scheduler.py` (COMP-012) | All four operations | `get_status()` with broker available returns structured dict; `get_status()` with broker unavailable returns degraded dict within 5s; `force_check()` enqueues task within 1s; `start()`/`stop()` send correct Celery commands |
| `utils/validators.py` (COMP-015) | Validation rules | Empty field returns named error; null value returns named error; out-of-range value returns range error; valid inputs return empty error map |
| `utils/rbac_errors.py` (COMP-016) | Error message format | `user` attempting `team_admin` action returns message identifying `team_admin`; every supported role/action combination produces a non-generic message |
| `services/audit_service.py` (COMP-014) | Transaction atomicity | Both writes succeed → commit called; audit log write fails → rollback called, handover record not persisted; error re-raised after rollback |
| `tests/config.py` (COMP-019) | Credential sourcing | Env vars set → credentials match env var values; env vars unset, localhost target → sentinel values used; env vars unset, non-localhost target → raises ConfigurationError |

### Integration Tests

| Interaction | Test Scope |
|---|---|
| Celery task execution with live Redis | Task dispatched via `.delay()` executes in worker; result accessible via result backend; retry mechanics fire on injected failure |
| `get_status()` with live Celery workers | Returns active worker count and job state; returns degraded state when Redis stopped |
| `force_check()` end-to-end | Task appears in Celery worker queue within 1 second of dispatch |
| Handover submission transaction | Full DB integration: both records written on success; neither record written on injected audit log failure |
| CI security stage (`.gitlab-ci.yml`) | Pipeline passes with clean dependencies; pipeline fails with a known-CVE dependency injected into `requirements.txt` |

### E2E Scenarios

| Scenario | Steps | Expected Outcome |
|---|---|---|
| **Container startup — healthy** | Start container with all required env vars set and DB available | Container starts; port 5000 bound; Gunicorn reports 1 worker; logs show startup health check passed |
| **Container startup — missing secret** | Start container with a required secret env var unset | Container exits within 10s; exit code non-zero; log identifies missing secret by name; no port bound |
| **Multi-worker deduplication** | Start 2 gunicorn workers + Celery Beat; observe job execution logs for 2 trigger intervals | Exactly 1 execution record per interval per job type; no duplicates |
| **Form submission with invalid fields** | Submit handover form with 2 empty required fields | HTTP 400; response body contains field-specific errors for both fields by name; no 500 error |
| **Insufficient permissions** | `user`-role account attempts handover approval | HTTP 403; response body identifies `team_admin` as required role; message is not generic |
| **DLQ routing** | Inject a ServiceNow polling task that fails on all 3 retries | Task appears in `failed_tasks` table with all context fields populated; operations alert dispatched |

### Coverage Approach

- **P0 requirements (REQ-001–009, REQ-015):** Target ≥ 80% line coverage for new modules. All happy-path and defined error-path acceptance criteria must have corresponding test cases.
- **P1 requirements (REQ-010–014, REQ-016–017):** Target ≥ 70% line coverage. At minimum one positive and one negative test case per acceptance criterion.
- **Modified existing files (`services/ctask_scheduler.py`, `routes/scheduler.py`):** Existing tests must continue to pass without modification; no regression on existing scheduler behaviour.
- **CI enforcement:** Coverage thresholds are not enforced as pipeline gates in this iteration; coverage reports are generated and published as pipeline artefacts for baseline measurement.

---

## Security Considerations

| # | Concern | Mitigation | OWASP Category |
|---|---|---|---|
| **SEC-001** | Broker credentials (Redis URL with auth token) exposed in source or version-controlled config | `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` sourced exclusively from environment variables. These vars must not appear in `.env` files tracked by git. `.gitignore` must exclude `.env`. | A02: Cryptographic Failures / A05: Security Misconfiguration |
| **SEC-002** | Test credentials (superadmin, admin, user passwords) valid in non-localhost environments if hardcoded | `tests/config.py` (COMP-019) reads from env vars; fallback sentinel values are non-guessable, localhost-only strings. A guard aborts test execution if sentinel values are used against a non-localhost target. | A05: Security Misconfiguration |
| **SEC-003** | Committed secrets in git history | GitLab Secret Detection template in COMP-017 scans full git history on every pipeline run; any detected secret blocks merge. Historical secrets must be revoked before this gate is activated. | A02: Cryptographic Failures |
| **SEC-004** | Known CVEs in declared Python dependencies | `pip-audit` (COMP-017) scans `requirements.txt` on every CI run; pipeline fails on any CVE finding, blocking merge. | A06: Vulnerable and Outdated Components |
| **SEC-005** | Python source code contains common security anti-patterns (SQL injection, subprocess injection, hardcoded keys) | Bandit SAST (COMP-017) scans all Python source; HIGH-severity findings are blocking. Any `# nosec` suppression requires code reviewer explicit approval and inline justification comment. | A03: Injection / A02: Cryptographic Failures |
| **SEC-006** | Binary document files (PDF, DOCX, etc.) tracked in git may contain PII or sensitive operational data | COMP-018 adds extension patterns to `.gitignore`; existing tracked binary files must be removed from all reachable commits via `git filter-repo` before the cleanup commit is merged. | A05: Security Misconfiguration (PII handling) |
| **SEC-007** | Session token validation bypassed during scheduler refactoring | `validate_session()` middleware runs on every request (existing control). COMP-012 and COMP-013 do not touch the session or authentication middleware. The refactoring is internal-only; no auth code path is modified. | A07: Identification and Authentication Failures |
| **SEC-008** | RBAC enforcement weakened during scheduler route modifications | COMP-013 modifies only the internal call to COMP-012; all inline RBAC checks in `routes/scheduler.py` are preserved verbatim. A code review checklist item must explicitly confirm no RBAC check was removed. | A01: Broken Access Control |
| **SEC-009** | Celery task arguments may contain user-supplied data that is persisted to `failed_tasks` table | COMP-011 must sanitise or truncate task argument values before writing to `failed_tasks.task_args` (JSON column). Maximum field length constraints on `task_args` and `task_kwargs` prevent storage-based DoS. Input to Celery tasks must be validated upstream (COMP-015) before dispatch. | A03: Injection |
| **SEC-010** | Operations alert dispatch (from COMP-011) may leak task internals to untrusted channels | Alert payloads must contain only: task name, timestamp, failure count, and a reference ID (the `failed_tasks.id`). Full error traces and task arguments must not appear in alert payloads; they are accessible only via authenticated DB query. | A02: Cryptographic Failures / PII Handling |

---

## Error Handling Strategy

### Error Propagation Chain

```
External input (form submission)
  → COMP-015 (validation) → ValidationError (field map) → HTTP 400 (field-level errors)
  → COMP-016 (RBAC check) → PermissionError (role context) → HTTP 403 (specific message)
  → COMP-014 (audit transaction) → DatabaseError → rollback → HTTP 500 (retry message)
  → Application code → UnhandledException → Flask errorhandler → HTTP 500 (generic safe message)

Background task
  → Celery task execution → TransientError → retry (max 3, interval 30s)
  → Final failure → COMP-011 (DLQ handler) → DB write + alert
  → COMP-011 DB write failure → alert still dispatched; error logged to structured log
```

### User-Facing Error Messages vs. Internal Logging

| Error Class | User-Facing Message | Internal Log |
|---|---|---|
| Field validation failure | Specific field name + actionable correction (e.g., "Shift end time is required") | DEBUG: field name, received value |
| RBAC denial | Specific required role/privilege (e.g., "team_admin access is required to approve handovers") | INFO: user_id, attempted action, user role, required role |
| Audit transaction failure | "Submission failed: no data was saved. Please retry or contact support." (no technical detail) | ERROR: exception type, stack trace, user_id, handover context |
| Startup check failure | Human-readable description identifying the failing check and the configuration key (e.g., "SECRET_KEY_FOO is absent from the secrets store") | CRITICAL: full exception; written to stderr |
| DLQ exhaustion | Not user-facing (async operation) | ERROR: task_name, celery_task_id, failure_count, full traceback |
| Scheduler broker unavailable | Degraded-state indicator in `get_status()` response; explicit `broker_reachable: false` field | WARNING: inspect timeout duration, broker URL (redacted auth) |

**Rule:** No stack trace, database error message, or internal component name appears in any user-facing response. Internal errors are logged with structured fields (user_id, request_id, timestamp) at the appropriate severity level using the application's existing logging configuration.

### Retry Strategy for Transient Failures

- **Celery tasks (COMP-007–010):** `max_retries=3`, `countdown=30` (seconds). Applies to all transient errors from external services (ServiceNow timeout, SMTP connection error, DB transient error). Non-transient errors (e.g., `ValueError` from bad task arguments) must NOT trigger retries; the task must raise immediately to avoid wasting retry budget.
- **Startup health checks (COMP-004):** No retry. A single failure is deterministic and fatal at container startup. The container must exit and be restarted by the orchestrator (which has its own restart policy).
- **Scheduler `get_status()` (COMP-012):** No retry. The inspect call uses a 2.0-second timeout and returns the degraded state immediately on timeout. The web tier must not be blocked waiting for a retry.
- **Handover submission (COMP-014):** No retry at the service layer. The route handler returns an error to the user, who retries via a new form submission. Automatic retry of a failed DB transaction risks duplicate writes if the first transaction's commit status is uncertain.

### Graceful Degradation When Dependencies Are Unavailable

| Dependency | Unavailable Scenario | Degradation Behaviour |
|---|---|---|
| **Redis (task queue broker)** | Broker unreachable during HTTP request | `get_status()` returns degraded indicator; `force_check()` and `start()`/`stop()` return HTTP 503 with specific message. HTTP request processing continues unaffected. |
| **Redis (during task execution)** | Broker recovers; in-flight tasks continue to completion; new enqueue operations resume normally | No action required from HTTP tier. COMP-011 records the failure if a task could not re-enqueue for retry. |
| **Primary database (during startup)** | DB unreachable | COMP-004 exits non-zero; container does not start; no port bound (REQ-014). |
| **Primary database (at runtime)** | DB connection lost mid-request | SQLAlchemy raises `OperationalError`; Flask errorhandler returns HTTP 500 with a safe user message; structured error logged. COMP-014 rolls back the transaction. |
| **ServiceNow (external API)** | Timeout or 5xx error | Celery retry (up to 3 attempts, 30-second intervals). After exhaustion, task enters DLQ via COMP-011; operations alerted. |
| **Operations alert channel** | Alert dispatch fails | Failure is logged at ERROR level. The `failed_tasks` DB record is still written. Alert failure must not prevent DLQ record persistence. |