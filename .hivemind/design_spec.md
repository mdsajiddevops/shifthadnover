# Architecture Design Specification
## ShiftOps Archaeology & Hardening — CTCOAMSHM-7

---

## Meta

| Field | Value |
|-------|-------|
| **Ticket ID** | CTCOAMSHM-7 |
| **Project Name** | ShiftOps (Shifthandover) |
| **Creation Date** | 2026-05-02 |
| **Spec Reference** | Functional Specification: ShiftOps Archaeology & Hardening (In Review) |
| **Status** | Draft — Ready for Engineering Review |
| **Branch Scope** | Archaeology & Hardening (no new user-visible features) |
| **Architecture Author** | Generated from approved specification and interrogation summary |

---

## Problem Spec Reference

This design addresses the 13 requirements (REQ-001 through REQ-013) defined in the approved **Functional Specification: ShiftOps Archaeology & Hardening**. Requirements span four categories: infrastructure (scheduled task isolation, WSGI server replacement, container orchestration), security (credential hygiene, CI/CD scanning, input validation), process (migration documentation, branch protection, binary file exclusion), and operational resilience (startup validation, retry behaviour, graceful degradation). All requirements are additive or internal-only — no existing route contracts, database schemas, session formats, or RBAC definitions are modified. Refer to the approved specification for full requirement text, acceptance criteria, constraints, and glossary.

---

## Current Architecture

### Existing Components Relevant to This Hardening Branch

**Web Serving Tier**
- `app.py` — Flask application factory; registers all ~45–50 Blueprint modules; currently initialises APScheduler in-process and starts the application via `app.run()` (Flask development server / Werkzeug). This file is the primary modification target.
- `routes/` directory — ~45–50 Blueprint modules, each handling a domain area (auth, dashboard, handover, incidents, key points, change info, SSO, etc.). Route handlers contain inline RBAC checks and currently have inconsistent or absent input validation before persistence.
- `auth.py` / `routes/auth.py` — Local login path; Fernet-encrypted password store.
- `routes/sso_auth.py` / `routes/sso_config.py` — OAuth 2.0 / SAML SSO path.

**Background Task Tier (current — to be refactored)**
- `services/ctask_scheduler.py` — Exists today; dispatches scheduled jobs (email notification digests, ServiceNow polling, retry operations) using APScheduler running **inside** the Gunicorn/Flask process. This is the root cause of duplicate task execution on scale-out and is the primary functional refactoring target.
- APScheduler — In-process Python scheduler; will be removed from the web-serving process entirely.

**Data & Configuration Tier**
- `models/sso_config.py` — Encrypted OAuth configuration stored in the database; loaded at startup via `Config.init_from_database()`.
- `models/` — SQLAlchemy model definitions for all application entities.
- Flask-Migrate / Alembic — Versioned database migration toolchain; already integrated. Ad-hoc SQL scripts exist alongside versioned migrations with undocumented status.
- `session_tokens` table — Server-side session token store; validated on every request by `validate_session()` middleware. Unchanged by this branch.

**Test Infrastructure**
- `tests/config.py` — Resolves test credentials; currently contains hardcoded literal values for superadmin, admin, and user credentials. Primary credential hygiene target.

**CI/CD & Repository**
- `.gitlab-ci.yml` — GitLab pipeline definition; currently has no dedicated security scanning stage. To be extended.
- `.gitignore` — Does not currently exclude binary documentation file types. To be extended.
- Binary documentation files (`.pdf`, `.docx`, `.doc`, `.xlsx`, `.pptx`) — Tracked in the repository. To be removed and excluded.
- GitLab branch protection — Main branch currently permits direct pushes; no MR approval requirement is enforced. To be configured.

### Existing Patterns

| Pattern | Current State |
|---------|--------------|
| **Route style** | Server-side rendered HTML; Flask Blueprint per domain; limited inline JSON for in-page ops |
| **RBAC enforcement** | Inline within individual route handler functions; no shared decorator |
| **Session management** | Flask-Login + per-request `validate_session()` DB check; administrator-forced revocation via `session_tokens` table |
| **Error handling** | Inconsistent; partial validation in some routes, none in others; no shared validation utility |
| **Configuration loading** | `Config.init_from_database()` at startup; OAuth secrets via `SecretsManager` (Fernet AES); test credentials hardcoded |
| **Task scheduling** | APScheduler in-process alongside Gunicorn workers |
| **Container orchestration** | `docker-compose.yml`; web service currently uses `python app.py` as command |

### Integration Points Where This Design Connects to Existing Code

| Integration Point | Nature of Connection |
|-------------------|---------------------|
| `app.py` | Remove APScheduler init; add Celery app init; invoke startup validator |
| `services/ctask_scheduler.py` | Refactor task functions from APScheduler jobs to Celery tasks |
| `docker-compose.yml` | Add `redis`, `celery-worker`, `celery-beat` services; change web command |
| `routes/dashboard*.py` | Wrap Celery worker status queries via instrumentation adapter |
| All `routes/*.py` handling form POST | Integrate centralized validation utility before persistence |
| `tests/config.py` | Replace literal credentials with environment variable resolution |
| `.gitlab-ci.yml` | Insert security stage before build |
| `.gitignore` | Append binary documentation exclusion patterns |

---

## Architecture

### Pattern

**Process-Isolated Worker Architecture** layered on the existing Flask SSR monolith.

The web tier (Flask + Gunicorn) and background task tier (Celery worker + Celery Beat) are separated into distinct OS processes communicating exclusively through a Redis message broker. This is the minimal pattern change required to eliminate duplicate task execution on Gunicorn scale-out, preserve all existing route contracts and database schemas, and satisfy REQ-001 and REQ-009 without introducing a full distributed workflow orchestration platform (explicitly a non-goal).

All remaining hardening changes (startup validation, credential hygiene, WSGI server, input validation, pipeline security, repository hygiene, branch protection) are additive hardening measures applied to the monolith without altering its external pattern. The SSR monolith pattern itself is preserved.

**Why this pattern and not others:** The application's task volume and complexity do not warrant Airflow, Prefect, or a distributed workflow orchestrator. The risk being closed is architectural (APScheduler co-located with Gunicorn), not operational complexity. Celery + Redis provides the necessary broker-mediated deduplication guarantee with the lowest adoption footprint given the existing Python ecosystem.

---

### Components

---

#### COMP-001 — Production WSGI Entry Point Script
- **Type**: Shell script / process entry point
- **Responsibility**: Launch the Flask application under Gunicorn with production-grade settings, making the development server unreachable as a startup path.
- **File Path**: `start.sh` (repository root)
- **Dependencies**: None within the Python application; invoked by COMP-012 (docker-compose web service command)
- **Requirements Addressed**: REQ-003, AC-003a, AC-003b

**Interface Contract:**
- **Invocation**: `bash start.sh` (set as executable; called directly by container orchestration)
- **Gunicorn arguments to specify** (exact values are implementation; these are the required parameters):
  - `-w <N>` — number of worker processes (initially `1`; safe to increase after Redis monitoring confirmed per A-001)
  - `-b 0.0.0.0:5000` — bind address
  - `--timeout 120` — worker request timeout (≥ 120 seconds per REQ-003)
  - `--access-logfile -` — access log to stdout for container log capture
  - `app:app` — WSGI application target
- **Exit behaviour**: If Gunicorn fails to bind (e.g., port already in use), `start.sh` exits with the non-zero exit code propagated from Gunicorn. It must not attempt to fall back to `python app.py` or any other invocation.
- **What must NOT appear**: Any invocation of `python app.py`, `flask run`, or `app.run(debug=...)`.

---

#### COMP-002 — Application Startup Validator
- **Type**: Utility module
- **Responsibility**: Verify all required runtime configuration values are present and all critical external services are reachable before the Flask application enters the running state.
- **File Path**: `startup_checks.py` (repository root, adjacent to `app.py`)
- **Dependencies**: Python standard library (`os`, `sys`, `logging`); existing `Config` class in `app.py`; database connection configured by Flask-SQLAlchemy; Redis connection URL from environment
- **Requirements Addressed**: REQ-011, AC-011a, AC-011b; partially REQ-002 (no-fallback enforcement in non-localhost environments)

**Interface Contract:**

```
Function: run_startup_checks(app: Flask) -> None
  Called once during application factory initialization in app.py,
  after configuration loading, before route registration.

  Checks (in order):
    1. For each name in REQUIRED_ENV_VARS (list defined in this module):
       - If os.environ.get(name) is None or empty string:
         → log.critical("STARTUP FAILURE: Required environment variable '<name>' is not set.")
         → sys.exit(1)
    2. Database reachability: execute a trivial SQL probe (e.g., SELECT 1) within the app context.
       - On failure: log.critical("STARTUP FAILURE: Database unreachable — <error>")
         → sys.exit(1)
    3. Redis/broker reachability: attempt connection to CELERY_BROKER_URL.
       - On failure: log.critical("STARTUP FAILURE: Redis broker unreachable at <url> — <error>")
         → sys.exit(1)

  On all checks passing: returns normally; application initialization continues.
  On any check failing: process exits with code 1 before any route is registered.
```

**REQUIRED_ENV_VARS registry** (minimum set; implementation must enumerate all):
- `SECRET_KEY`
- `DATABASE_URL` (or component env vars: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

**Note:** Test-specific variables (`TEST_SUPERADMIN_PASSWORD`, etc.) are NOT checked here; they are checked by COMP-006 within the test runner context.

---

#### COMP-003 — Celery Application Factory
- **Type**: Service module
- **Responsibility**: Instantiate, configure, and expose the single shared Celery application object used by all task definitions and the worker process.
- **File Path**: `services/celery_app.py`
- **Dependencies**: `celery` library; `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` environment variables; COMP-005 (imports beat schedule)
- **Requirements Addressed**: REQ-001, REQ-009

**Interface Contract:**

```
Module-level export:
  celery_app: Celery  — the configured Celery application instance

Configuration properties to be set on celery_app:
  broker_url                  ← os.environ["CELERY_BROKER_URL"]
  result_backend              ← os.environ["CELERY_RESULT_BACKEND"]
  task_serializer             = "json"
  result_serializer           = "json"
  accept_content              = ["json"]
  timezone                    = "UTC"
  enable_utc                  = True
  task_acks_late              = False   (at-most-once guarantee; see ADR-002)
  beat_schedule               ← imported from COMP-005
  worker_hijack_root_logger   = False   (preserve Flask/application logger configuration)

Flask integration:
  celery_app.conf.update(app.config) is called from the Flask app factory in app.py
  after the Flask app is created, binding the Celery instance to the Flask app context.
  This follows the "Flask-Celery integration without flask-celery extension" pattern.
```

---

#### COMP-004 — Background Task Definitions
- **Type**: Service module (modified from existing `services/ctask_scheduler.py`)
- **Responsibility**: Define all background task functions as Celery task objects with retry policy, task routing, and execution logging.
- **File Path**: `services/ctask_scheduler.py` (modified in-place)
- **Dependencies**: COMP-003 (`celery_app`); existing business logic for email digests, ServiceNow polling; external service clients
- **Requirements Addressed**: REQ-001, REQ-009, REQ-010, AC-010a, AC-010b

**What Changes vs. What Stays the Same:**
- **Removed**: APScheduler `@scheduler.scheduled_job(...)` decorators and any APScheduler `BackgroundScheduler` initialization.
- **Preserved**: The underlying task business logic (email construction, ServiceNow API calls, retry-eligible operations). Task function signatures may change to match Celery conventions but outcomes are identical.
- **Added**: Celery `@celery_app.task(...)` decorators with retry configuration.

**Interface Contract — Task Decorator Specification:**

Every task function in this module must be decorated with the following parameters (minimum):

```
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,        # seconds; satisfies REQ-010 ≥30s delay
    autoretry_for=(ExternalServiceError, ConnectionError, Timeout),
    retry_backoff=False,           # flat 30-second delay, not exponential
    acks_late=False,               # at-most-once; consistent with COMP-003
    name="shiftops.<task_name>"    # explicit task name prevents import-path collisions
)
def <task_name>(self, *args, **kwargs) -> dict:
    ...
    # Return contract:
    # { "status": "success", "task": "<task_name>", "completed_at": "<ISO8601>" }
    # On terminal failure (retries exhausted): exception propagates; Celery records FAILURE state.
```

**Task Execution Log Contract:**
Each task must emit a structured log entry on completion and on each retry attempt:
- `log.info("TASK_STARTED task=<name> task_id=<celery_task_id> attempt=<N>")`
- `log.info("TASK_COMPLETED task=<name> task_id=<celery_task_id> attempt=<N>")`
- `log.warning("TASK_RETRY task=<name> task_id=<celery_task_id> attempt=<N> reason=<str>")`
- `log.error("TASK_FAILED task=<name> task_id=<celery_task_id> attempts_exhausted=3 error=<str>")`

This log contract satisfies REQ-010's observability requirement ("observable without manual log parsing") by enabling log aggregation queries on the `TASK_` prefix.

**Audit-Critical Task Designation:**
Tasks that invoke handover submission or incident logging must never silently fail. If such a task raises a non-retryable exception (e.g., database integrity error after retries exhausted), it must log `TASK_FAILED` at `ERROR` level and re-raise the exception to ensure Celery records a `FAILURE` state in the result backend. No `try/except: pass` blocks are permitted in audit-critical tasks.

---

#### COMP-005 — Celery Beat Periodic Schedule Configuration
- **Type**: Configuration module
- **Responsibility**: Define the periodic task trigger schedule consumed by the Celery Beat process, mapping task names to their cron/interval expressions.
- **File Path**: `celeryconfig.py` (repository root)
- **Dependencies**: COMP-004 (task names must match); standard `celery.schedules` primitives
- **Requirements Addressed**: REQ-001, REQ-009

**Interface Contract:**

```
Module-level export:
  beat_schedule: dict[str, dict]  — Celery beat schedule mapping

Shape:
  {
    "<schedule_entry_name>": {
      "task": "shiftops.<task_name>",     # must match COMP-004 task name
      "schedule": crontab(...) | timedelta(...),
      "args": (...),                       # optional positional args
      "kwargs": {...},                     # optional keyword args
      "options": { "expires": <seconds> } # task expiry to prevent stale execution
    },
    ...
  }

Constraint: This file defines exactly ONE authoritative source of truth for all scheduled
triggers. The Celery Beat process runs from EXACTLY ONE container instance (no scaling of
the beat service). See COMP-012 for enforcement.
```

---

#### COMP-006 — Test Credential Resolver
- **Type**: Configuration module (modified from existing `tests/config.py`)
- **Responsibility**: Resolve test suite authentication credentials from named environment variables, enforcing a hard failure when variables are absent in non-localhost environments.
- **File Path**: `tests/config.py` (modified in-place)
- **Dependencies**: Python standard library (`os`, `socket`); no Flask app context required
- **Requirements Addressed**: REQ-002, REQ-013, AC-002a, AC-002b

**What Changes vs. What Stays the Same:**
- **Removed**: All credential literal strings (e.g., `"admin123"`, `"password"`, etc.).
- **Preserved**: The exported credential name constants (`TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`) that existing test modules import.
- **Added**: Environment variable resolution logic with localhost-only fallback gate.

**Interface Contract:**

```
Required environment variable names (exact strings):
  TEST_SUPERADMIN_PASSWORD    → credentials for superadmin-level test operations
  TEST_ADMIN_PASSWORD         → credentials for account_admin-level test operations
  TEST_USER_PASSWORD          → credentials for user-level test operations

Resolution logic (described, not coded):

  is_localhost: bool ← (socket.gethostname() resolves to loopback) OR
                       (os.environ.get("CI") is not set) OR
                       (os.environ.get("ENVIRONMENT") not in {"staging", "production", "ci"})

  For each of the three variables:
    value = os.environ.get("<VAR_NAME>")
    if value is None or value == "":
      if is_localhost:
        value = <DOCUMENTED_FALLBACK_VALUE>
        # Fallback value must be documented in CLAUDE.md and CONTRIBUTING.md
        # Fallback value must NOT be the same as any production credential
      else:
        raise EnvironmentError(
          "Test credential '<VAR_NAME>' is not set. "
          "Set this environment variable before running the test suite. "
          "See CONTRIBUTING.md for setup instructions."
        )

Module-level exports after resolution:
  TEST_SUPERADMIN_PASSWORD: str
  TEST_ADMIN_PASSWORD: str
  TEST_USER_PASSWORD: str
```

**Localhost Detection Note:** The `is_localhost` check must be conservative — it must default to `False` (non-localhost behaviour, i.e., raise error) in any ambiguous case, rather than defaulting to `True`. The only safe fallback condition is confirmed loopback hostname AND absence of CI environment markers.

---

#### COMP-007 — Migration Registry Document
- **Type**: Documentation artifact
- **Responsibility**: Provide a human-readable classification of every database migration script in the repository, enabling operators to determine safe application order without consulting any external system.
- **File Path**: `migrations/README.md`
- **Dependencies**: None (static document; references migration script filenames in the `migrations/` directory)
- **Requirements Addressed**: REQ-004, AC-004a, AC-004b

**Document Structure Contract:**

The document must contain four sections, in order:

1. **Overview** — States the migration toolchain (Flask-Migrate / Alembic), the single rule ("all future schema changes via `flask db migrate` exclusively"), and the date of last audit.

2. **Migration Classification Table** — A table with columns: `Script Filename`, `Classification`, `Applied to Production?`, `Notes`. Every migration script file present in `migrations/versions/` and every ad-hoc `.sql` file in `migrations/` (or equivalent directory) must appear in this table with exactly one of three classifications:
   - `APPLIED — production` — has been run against the production database; safe to skip on fresh installs only if included in the Alembic version chain.
   - `SUPERSEDED — do not re-apply` — replaced by a versioned Alembic migration; must never be executed manually against any environment.
   - `ENVIRONMENT-SPECIFIC` — applies only to a named non-production environment (name must be stated in Notes).

3. **Superseded Script Detail** — For every script classified as `SUPERSEDED`, a subsection that: (a) names the superseding versioned migration by filename and Alembic revision ID, (b) states an explicit operator warning ("Do not execute this script. Applying it after the versioned migration will cause schema inconsistency."), and (c) describes what the script originally did and why it was superseded.

4. **Future Migration Policy** — A single authoritative paragraph stating that no ad-hoc SQL scripts shall be introduced; all future schema changes must be introduced as Alembic migrations via `flask db migrate` and reviewed in a merge request before execution.

---

#### COMP-008 — CI/CD Security Stage Configuration
- **Type**: Pipeline configuration (modified)
- **Responsibility**: Declare and enforce a security scanning stage in the GitLab CI/CD pipeline that completes and passes before any build artifact is produced.
- **File Path**: `.gitlab-ci.yml` (modified in-place)
- **Dependencies**: GitLab Runner; GitLab-provided SAST and Secret Detection CI/CD templates; `pip-audit` tool available in the pipeline runner environment; `requirements.txt` present in repository root
- **Requirements Addressed**: REQ-005, REQ-013, AC-005a, AC-005b, AC-005c

**What Changes vs. What Stays the Same:**
- **Preserved**: All existing stages and jobs.
- **Added**: A new `security` stage that runs before `build`. The `build` stage must be listed after `security` in the top-level `stages` array.

**Stage and Job Contract:**

```yaml
# Stage ordering (within the top-level stages: list)
stages:
  - security    # NEW — must precede build
  - build
  - <...existing stages...>

# Job 1: Dependency vulnerability scan
dependency-scan:
  stage: security
  script:
    - pip install pip-audit
    - pip-audit --requirement requirements.txt --format json --output pip-audit-report.json
    # pip-audit exits non-zero on any CVE finding; this causes the job to fail.
  artifacts:
    when: always           # Save report even on failure for triage
    paths:
      - pip-audit-report.json
    reports:
      # No native GitLab report type for pip-audit; saved as generic artifact
  allow_failure: false     # Failing this job blocks the pipeline

# Job 2: Python SAST
# Uses the GitLab-managed SAST template (Bandit-based for Python)
include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml
# Both templates produce jobs in the "test" stage by default;
# override their stage to "security" using job-level stage: overrides
# or per GitLab documentation for stage override of included templates.

sast:
  stage: security

secret_detection:
  stage: security
  # GitLab Secret Detection scans full git history by default.
  # No additional configuration required beyond template inclusion.
```

**Failure semantics:**
- `dependency-scan` failing: pipeline stops; build stage does not execute; `pip-audit-report.json` is saved as artifact for remediation.
- `sast` failing: pipeline stops; build stage does not execute.
- `secret_detection` failing: pipeline stops; build stage does not execute; finding includes file reference per GitLab Secret Detection report format.

---

#### COMP-009 — Repository Binary Documentation Exclusion Configuration
- **Type**: VCS configuration (modified)
- **Responsibility**: Prevent binary documentation files from being staged or committed to the repository.
- **File Path**: `.gitignore` (modified in-place)
- **Dependencies**: None
- **Requirements Addressed**: REQ-006, AC-006a, AC-006b

**What Changes:**
- **Added** (appended as a clearly labelled section): The following patterns:

```
# Binary documentation files — maintained in Confluence, not in source control
*.pdf
*.doc
*.docx
*.xls
*.xlsx
*.ppt
*.pptx
```

- **Not modified**: All existing `.gitignore` entries.

**Pre-commit action required (one-time, outside CI):** All currently tracked binary documentation files must be removed from git tracking using `git rm --cached <file>` before merging this change, and the removal committed as part of this branch. The `.gitignore` entry alone does not retroactively un-track already-tracked files.

---

#### COMP-010 — Input Validation Utility
- **Type**: Utility module (new)
- **Responsibility**: Provide reusable, field-level input validation functions that return structured error descriptions for use by Flask route handlers before any data is persisted.
- **File Path**: `utils/validation.py`
- **Dependencies**: Python standard library only; no Flask context required (functions are pure)
- **Requirements Addressed**: REQ-008, AC-008a, AC-008b, AC-008c

**Interface Contract:**

```
Type alias:
  ValidationError: TypedDict with keys:
    field: str       — the name of the field that failed validation
    message: str     — human-readable description of the constraint violation
                       (e.g., "Shift date is required and must not be empty."
                             "Duration must be a positive integer between 1 and 1440.")

Function signatures (described; types are Python type hints):

  validate_required(value: Any, field_name: str) -> ValidationError | None
    Returns ValidationError if value is None, empty string, or whitespace-only.
    Returns None if valid.

  validate_not_null(value: Any, field_name: str) -> ValidationError | None
    Returns ValidationError if value is None.

  validate_range(
    value: int | float,
    field_name: str,
    min_val: int | float,
    max_val: int | float
  ) -> ValidationError | None
    Returns ValidationError if value < min_val or value > max_val.
    Message must state: "<field_name> must be between <min_val> and <max_val>. Received: <value>."

  validate_max_length(value: str, field_name: str, max_length: int) -> ValidationError | None
    Returns ValidationError if len(value) > max_length.

  validate_form(validators: list[Callable[[], ValidationError | None]]) -> list[ValidationError]
    Executes all validator callables in order.
    Returns a list of all ValidationErrors (may be empty = valid).
    Does NOT short-circuit on first failure — all fields are validated in one pass.

  format_error_response(errors: list[ValidationError]) -> dict
    Returns: { "errors": [{ "field": "...", "message": "..." }, ...] }
    Used by routes to construct the error payload.
```

**Usage contract for route handlers (pattern):**

Every form-handling POST route must:
1. Call `validate_form([...])` on the submitted data before any database operation.
2. If `errors` list is non-empty: return the error response immediately without writing to the database (no partial records).
3. If `errors` is empty: proceed with persistence.

The route handler determines which validators to assemble based on the form's field definitions. The validation utility is not responsible for knowing which fields exist on which form — that coupling remains in the route handler.

---

#### COMP-011 — Worker Status Instrumentation Adapter
- **Type**: Service module (new)
- **Responsibility**: Safely query Celery worker process status and return a structured result that represents the degraded state gracefully when the Celery broker or workers are unreachable.
- **File Path**: `services/worker_status.py`
- **Dependencies**: COMP-003 (`celery_app`); standard `celery.app.control` interface
- **Requirements Addressed**: REQ-012, AC-012a, AC-012b

**Interface Contract:**

```
Type definitions:

  WorkerStatusResult: TypedDict with keys:
    available: bool        — True if at least one worker responded within the timeout
    worker_count: int      — number of active workers (0 if unavailable)
    active_tasks: int      — total active tasks across all workers (0 if unavailable)
    error: str | None      — human-readable error description if unavailable; None if available

Function signature:

  get_worker_status(timeout_seconds: float = 1.0) -> WorkerStatusResult
    Calls celery_app.control.inspect(timeout=timeout_seconds).active()
    On success: returns WorkerStatusResult with available=True and populated counts.
    On any exception (ConnectionError, TimeoutError, any Exception):
      → catches the exception
      → logs at WARNING level: "WORKER_STATUS_CHECK_FAILED: <exception>"
      → returns WorkerStatusResult(available=False, worker_count=0, active_tasks=0,
          error="Worker status unavailable: <short_reason>")
    Does NOT re-raise the exception. Does NOT return an HTTP error response.
    The timeout must be short (default 1.0 second) to avoid blocking web request handling.
```

**Integration with dashboard routes:**

Dashboard route handlers in `routes/dashboard*.py` must call `get_worker_status()` and render the result into the template context as a `worker_status` variable. The template must conditionally render the instrumentation widget: display stats when `worker_status.available` is `True`; display a degraded indicator (e.g., "Worker status unavailable") when `False`. The route handler must not propagate exceptions from `get_worker_status()` — the function contract guarantees no exceptions escape.

---

#### COMP-012 — Container Orchestration Service Definitions
- **Type**: Infrastructure configuration (modified)
- **Responsibility**: Define the complete set of containerized services (web, celery-worker, celery-beat, redis) with correct dependencies, startup order, and scaling constraints.
- **File Path**: `docker-compose.yml` (modified in-place)
- **Dependencies**: COMP-001 (web command), COMP-003 (Celery app import path), COMP-004 (task module), COMP-005 (beat schedule)
- **Requirements Addressed**: REQ-001, REQ-003, REQ-009

**What Changes vs. What Stays the Same:**

*Modified:*
- `web` service `command`: changed from `python app.py` → `bash start.sh`
- `web` service `depends_on`: add `redis` (broker must be available before web starts)
- All services: environment variable injection via `env_file: .env` or explicit `environment:` block referencing `${VAR_NAME}` syntax (no literal credential values in this file)

*Added:*

```
Service: redis
  image: redis:<pinned_version>
  restart: unless-stopped
  ports: (internal only; not exposed to host in production)
  volumes: (optional persistence volume for broker durability)

Service: celery-worker
  build: . (same image as web)
  command: celery -A services.celery_app.celery_app worker --loglevel=info
  depends_on: [web, redis]   # web ensures Flask app context is importable; redis is the broker
  restart: unless-stopped
  deploy:
    replicas: 1              # scale as needed; safe to scale > 1 (no duplicate task risk)

Service: celery-beat
  build: . (same image as web)
  command: celery -A services.celery_app.celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler
  depends_on: [redis]
  restart: unless-stopped
  deploy:
    replicas: 1              # MUST remain 1; scaling beat causes duplicate trigger dispatch
    # This constraint is explicitly documented in the compose file as a comment.
```

**Critical Constraint on `celery-beat` scaling:** The `celery-beat` service must never be scaled beyond a single instance. Duplicate Beat instances each independently dispatch task triggers to the broker, which produces duplicate executions violating REQ-009. This constraint must be documented as an inline comment in `docker-compose.yml` adjacent to the `celery-beat` service definition and noted in the deployment runbook (see Open Items).

---

#### COMP-013 — GitLab Branch Protection and MR Approval Configuration
- **Type**: Platform configuration (GitLab project settings — no file path in repository)
- **Responsibility**: Enforce at-minimum-one peer-reviewer approval on merge requests targeting the main branch, prohibiting self-approval and direct pushes.
- **File Path**: GitLab project → Settings → Repository → Protected Branches; Settings → Merge Requests → Approvals (no repository file)
- **Dependencies**: None within the codebase; requires GitLab Maintainer or Owner role to configure
- **Requirements Addressed**: REQ-007, AC-007a, AC-007b, AC-007c

**Configuration Contract:**

Protected Branch settings for `main` (or `master`):
- Allowed to push: No one (block all direct pushes, including Maintainers)
- Allowed to merge: Maintainers (via merge request only)
- Code owner approval required: Disabled (insufficient team size to configure CODEOWNERS)

Merge Request Approval settings:
- Required approvals: `1`
- Allow MR authors to approve their own MRs: **Disabled**
- Require new approvals when new commits are pushed: Enabled (prevents approval-then-force-push pattern)
- Remove all approvals when new commits are pushed: Enabled

---

### Data Flows

**Data Flow 1 — HTTP Request Serving (Production)**
```
Inbound HTTP request
  → COMP-001 (start.sh / Gunicorn, ≥1 worker processes)
  → Flask WSGI application (app.py)
  → validate_session() middleware (session_tokens table — unchanged)
  → Flask Blueprint route handler (routes/*.py)
  → [if POST with form data] → COMP-010 (validate_form())
      → [validation error] → error response rendered (no DB write)
      → [validation pass] → SQLAlchemy model persistence → success response
  → [if dashboard route] → COMP-011 (get_worker_status())
      → [worker available] → status data in template context
      → [worker unavailable] → degraded state in template context
  → Rendered HTML / JSON response
  ← HTTP 200 (or redirect)
```

**Data Flow 2 — Scheduled Background Task Execution (Happy Path)**
```
Wall-clock trigger time reached
  → COMP-005 (Celery Beat schedule) — single Beat process
  → Redis message broker (task message enqueued exactly once)
  → COMP-004 (Celery worker picks up message — exactly one worker consumes the message)
  → Task function executes:
      → External service call (e.g., ServiceNow API, email SMTP)
      → log.info("TASK_COMPLETED ...")
      → Result written to Redis result backend
  → Redis result backend records TASK_COMPLETED state
```

**Data Flow 3 — Scheduled Task with Transient Failure and Retry**
```
Celery task function encounters ExternalServiceError on attempt 1
  → COMP-004: log.warning("TASK_RETRY task=<name> attempt=1 reason=<error>")
  → Celery schedules retry after 30 seconds (default_retry_delay=30)
  → [30-second delay]
  → Attempt 2 executes:
      → [Success] → log.info("TASK_COMPLETED ... attempt=2") → DONE
      → [Failure] → retry → [30-second delay] → Attempt 3
      → [Success] → log.info("TASK_COMPLETED ... attempt=3") → DONE
      → [Failure] → retry → [30-second delay] → Attempt 4
      → [Failure] → retries exhausted → log.error("TASK_FAILED ... attempts_exhausted=3")
        → exception propagates → Celery records FAILURE state in result backend
```

**Data Flow 4 — Application Startup**
```
Container start
  → COMP-001 (start.sh) invokes Gunicorn
  → Gunicorn forks worker process(es)
  → Each worker imports app.py → Flask app factory runs
  → COMP-002 (run_startup_checks(app)) called:
      → Check required env vars
          → [missing] → log.critical("STARTUP FAILURE: ...") → sys.exit(1) → Gunicorn exits non-zero
      → Check DB reachability
          → [unreachable] → log.critical("STARTUP FAILURE: ...") → sys.exit(1)
      → Check Redis reachability
          → [unreachable] → log.critical("STARTUP FAILURE: ...") → sys.exit(1)
      → [all pass] → returns normally
  → Route registration continues
  → Gunicorn begins accepting requests
```

**Data Flow 5 — Test Suite Credential Resolution**
```
Test runner invoked (pytest)
  → tests/config.py (COMP-006) imported
  → is_localhost check:
      → [CI environment detected] → is_localhost = False
      → [loopback hostname, no CI markers] → is_localhost = True
  → For each credential variable:
      → os.environ.get("<VAR_NAME>")
      → [value present] → use value
      → [absent, is_localhost=True] → use documented fallback
      → [absent, is_localhost=False] → raise EnvironmentError (test suite fails immediately)
  → TEST_SUPERADMIN_PASSWORD, TEST_ADMIN_PASSWORD, TEST_USER_PASSWORD exported
  → Test modules import credentials from tests/config.py
```

**Data Flow 6 — CI/CD Pipeline Security Gate**
```
Developer pushes commit to any branch
  → GitLab pipeline triggered
  → COMP-008 (security stage) — runs before build:
      → Job 1: pip-audit
          → [CVE found] → exit non-zero → artifact saved → pipeline blocked
          → [clean] → artifact saved → job passes
      → Job 2: GitLab SAST (Bandit)
          → [finding] → job fails → pipeline blocked
          → [clean] → job passes
      → Job 3: GitLab Secret Detection (full history)
          → [secret found] → job fails → pipeline blocked
          → [clean] → job passes
      → [all three pass] → build stage proceeds
```

**Data Flow 7 — Merge Request to Main Branch**
```
Developer opens MR targeting main
  → COMP-013 (GitLab branch protection) evaluated:
      → Direct push attempt → rejected immediately (push rules)
  → Author attempts self-approval → rejected (self-approval disabled)
  → No peer approval → merge button disabled / merge attempt rejected
  → Peer reviewer approves (≥1, not author) → approval count = 1 (threshold met)
  → Author initiates merge → permitted → branch merged
```

**Data Flow 8 — Worker Unavailable During Scheduled Trigger**
```
Celery Beat dispatches task message → Redis broker
  → Celery worker service is down
  → Task message persists in Redis queue (not consumed)
  → Web tier continues serving HTTP requests normally (no impact)
  → COMP-011 returns WorkerStatusResult(available=False) for dashboard instrumentation
  → Dashboard renders degraded indicator; core routes return HTTP 200
  → Celery worker container restarts (Docker restart: unless-stopped)
  → Worker reconnects to Redis → consumes queued task message
  → Task executed exactly once (message consumed → acknowledged → executed)
```

---

## API Contracts

This application is an SSR monolith; no new HTTP endpoints are introduced. The following contracts define modifications to existing endpoint behaviour and the internal service method interfaces exposed by new components.

---

### Modified Behaviour: All Form Submission Endpoints (POST)

**Applies to:** All `POST` route handlers in `routes/` that accept user-submitted form data and write to the database. The URL paths, HTTP methods, and authentication requirements of these routes are **unchanged**.

**Current behaviour (pre-hardening):** Route handlers proceed directly to database operations on form submission; validation is absent or inconsistent; partial records may be created on malformed input.

**Modified behaviour (post-hardening):** Every form-handling POST route validates all submitted fields using COMP-010 before any database operation.

**Request (unchanged):** `application/x-www-form-urlencoded` or `multipart/form-data` — identical to current.

**Success Response (unchanged):** 302 redirect to result page, or 200 with rendered HTML, per existing route behaviour.

**Error Response (new — validation failure):**

For routes that currently return rendered HTML:
```
HTTP Status: 200 (re-render the form with errors inline — standard SSR pattern)
Content-Type: text/html
Body: Re-rendered form template with error context injected:
  - template variable: errors: list[ValidationError]
    [{ "field": "<field_name>", "message": "<human-readable constraint message>" }, ...]
  - template variable: form_data: dict — the submitted values, preserved for UX
  - Each form field with an error must render the associated error message adjacent to the field.
  - No partial record is created in the database.
```

For routes that currently return JSON (in-page operations):
```
HTTP Status: 422 Unprocessable Entity
Content-Type: application/json
Body: {
  "errors": [
    { "field": "<field_name>", "message": "<human-readable constraint message>" },
    ...
  ]
}
```

**Error Cases and Handling:**

| Error Condition | HTTP Status | Response |
|----------------|-------------|----------|
| Required field empty or null | 200 (HTML) / 422 (JSON) | Error message: `"<Field Label> is required and must not be empty."` |
| Value out of permitted range | 200 (HTML) / 422 (JSON) | Error message: `"<Field Label> must be between <min> and <max>. Received: <value>."` |
| Value exceeds max length | 200 (HTML) / 422 (JSON) | Error message: `"<Field Label> must not exceed <N> characters."` |
| Multiple validation failures | 200 (HTML) / 422 (JSON) | All errors returned in a single response; all fields validated before returning |
| Database error after passing validation | 500 / rendered error page | Internal error logged; user sees generic "An error occurred" message; no partial record (transaction rolled back) |

**Auth requirements:** Unchanged. `validate_session()` middleware enforces authentication before any route handler is reached.

---

### Internal Service Interface: `get_worker_status()` (COMP-011)

This is not an HTTP endpoint. It is a Python function called within dashboard route handlers. Defined fully under COMP-011. Repeated here for completeness:

- **Caller:** `routes/dashboard*.py` route handlers
- **Guarantee:** Never raises an exception (all exceptions caught internally)
- **Returns:** `WorkerStatusResult` — always a valid Python dict-like object
- **Timeout:** 1.0 second (configurable; must remain low to avoid blocking web requests)
- **On success:** `available=True`, populated counts
- **On any failure:** `available=False`, `error="<short reason>"`, counts=0

---

### Internal Service Interface: `run_startup_checks()` (COMP-002)

- **Caller:** `app.py` Flask application factory
- **Called once** per process startup; never called during request handling
- **Returns:** `None` on success
- **On failure:** Calls `sys.exit(1)` — process terminates; never returns
- **Side effects on failure:** Writes to the process log at `CRITICAL` level before exiting

---

## Data Models

### No New Database Tables or Schema Changes

This branch introduces zero modifications to the MySQL database schema. All changes are internal to the application process layer. The following notes document the data models introduced at the infrastructure level (Redis) and the record contract for task execution logging.

---

### Redis Data Structures (Celery Broker and Result Backend)

These structures are managed entirely by the Celery framework; ShiftOps application code does not directly read or write to them. They are documented here for operational awareness.

| Structure | Key Pattern | Purpose | TTL |
|-----------|-------------|---------|-----|
| Task message | `celery` (default queue) | Persists pending task messages between Beat dispatch and worker pickup | Consumed on pickup |
| Task result | `celery-task-meta-<task_id>` | Stores task execution outcome (SUCCESS / FAILURE / RETRY) | Configurable via `result_expires`; recommended 24h |
| Beat schedule state | `celerybeat-schedule` | Tracks last-run timestamps for periodic tasks (PersistentScheduler) | Persistent |

**Note on `result_expires`:** Must be set to at least 24 hours in COMP-003 configuration to satisfy the 24-hour observability window in AC-009a.

---

### Task Execution Log Schema (Application-Level)

Task execution state is observable through two mechanisms:
1. **Structured application logs** — emitted by COMP-004 with the `TASK_` prefix (see COMP-004 interface contract). Queryable in any log aggregation system.
2. **Celery result backend** — Redis records of `SUCCESS` / `FAILURE` state per `task_id`.

No new database table is created for task execution logging. If structured log querying proves insufficient in a future branch, a `task_execution_log` table can be introduced via Alembic migration (per REQ-004's future migration policy).

---

### Existing Models — No Changes

| Model / Table | Change |
|--------------|--------|
| `session_tokens` | **Unchanged** — per-request validation mechanism preserved |
| All handover, incident, keypoint, change_info models | **Unchanged** — schema modifications explicitly excluded from this branch |
| `sso_config` | **Unchanged** — OAuth credential loading via `SecretsManager` preserved |
| All other existing tables | **Unchanged** |

---

### Migration Documentation Record (COMP-007)

Not a database model; described fully under COMP-007. The `migrations/README.md` document is the data artifact for REQ-004. The authoritative classification of each migration script exists only in this document — there is no programmatic enforcement of migration status.

---

## Decisions (ADRs)

---

### ADR-001 — Architecture Pattern: Process-Isolated Worker

**Title:** Process-Isolated Background Task Worker via Message Broker

**Context:**
APScheduler currently runs scheduled tasks (email digests, ServiceNow polling, retry operations) inside the Gunicorn/Flask process. When Gunicorn is scaled to multiple workers (e.g., for load), each worker runs its own APScheduler instance. This causes every scheduled task to fire N times (once per Gunicorn worker) per trigger event — violating REQ-001 and REQ-009. The application cannot be safely scaled beyond a single Gunicorn worker under this architecture.

**Decision:**
Adopt the **Process-Isolated Worker** pattern: move all scheduled and queued task execution to a dedicated worker process communicating with the web tier exclusively through a Redis message broker. The web tier (Gunicorn) dispatches tasks to the broker; the worker process dequeues and executes them. Trigger scheduling is delegated to a separate Celery Beat process.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **Distributed lock around APScheduler** (acquire a Redis/DB lock before each task execution; skip if lock held) | No new process; minimal infrastructure change | Fragile — lock acquisition/release must be implemented correctly in every task; risk of lock starvation, missed releases on crash; does not remove APScheduler from web process; complexity grows with each new task; not the community-standard approach | 
| **Do nothing / document single-worker constraint** | Zero engineering cost; constraint is currently tolerated | Does not satisfy REQ-001 or REQ-009; prevents safe scale-out permanently; escalates risk of missed or duplicate notifications as task volume grows |
| **Dedicated cron container running Python scripts** | Simple; no new library dependency | No deduplication guarantee (if cron container scales); no retry mechanism; no result backend; difficult to observe task state; does not integrate with Flask app context |

**Consequences:**

*Positive:*
- Gunicorn can be safely scaled to any number of workers with zero duplicate task executions.
- Task state (SUCCESS / FAILURE / RETRY) is observable via result backend without log parsing.
- Retry logic is centralised and framework-managed.

*Negative trade-offs:*
- Redis becomes a required infrastructure dependency; its unavailability blocks task execution (tasks queue, not silently drop).
- `docker-compose.yml` now manages four services (web, celery-worker, celery-beat, redis) instead of one; operational complexity increases modestly.
- Celery Beat must not be scaled beyond one instance (enforced by compose constraint and documentation).

*Risks and mitigations:*
- **Risk**: Redis outage causes task backlog. **Mitigation**: Redis uptime monitoring and alerting must be in place before Gunicorn is scaled beyond 1 worker (per A-001 and Open Item 3).
- **Risk**: Beat service accidentally scaled to >1. **Mitigation**: Explicit `replicas: 1` in compose and inline comment; noted in deployment runbook.

---

### ADR-002 — Background Task Library: Celery with Redis

**Title:** Celery as Distributed Task Queue with Redis as Broker and Result Backend

**Context:**
The process-isolated worker pattern (ADR-001) requires a message broker to decouple task dispatch from execution, a scheduler to trigger periodic tasks, and a result backend for observability. The choice of library determines API surface, retry semantics, and the broker technology.

**Decision:**
Use **Celery** with **Redis** as both broker and result backend. Celery is already referenced in the project's glossary and interrogation summary as the chosen implementation. Redis is lightweight, operationally simple to run in Docker, and satisfies the broker durability requirements at the current task volume.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **RQ (Redis Queue)** | Simpler API; lighter weight; Redis-native | No built-in periodic scheduler (requires `rq-scheduler`, a separate process with less community support than Celery Beat); fewer retry primitives; smaller ecosystem; would require more custom code for retry observability |
| **Dramatiq + APScheduler (separate process)** | Simpler task definitions; type-safe; APScheduler in a standalone process avoids duplication | APScheduler is part of the problem being solved (unfamiliarity with APScheduler's scaling behaviour was the original bug); introducing it back in a different form increases risk; Dramatiq has a smaller ecosystem than Celery |
| **Celery with RabbitMQ as broker** | More robust message durability; better dead-letter queue support | Higher operational complexity (RabbitMQ requires more configuration and resource); Redis already satisfies durability at current task volume and is simpler to operate in Docker; over-engineered for "thousands of requests per day" workload |

**Consequences:**

*Positive:*
- `max_retries`, `default_retry_delay`, `autoretry_for` parameters satisfy REQ-010 with no custom retry logic.
- `celery.control.inspect` provides worker status for COMP-011 with a single call.
- Mature ecosystem; extensive documentation.
- `acks_late=False` (default) provides at-most-once guarantee per trigger dispatch.

*Negative trade-offs:*
- Celery is a non-trivial dependency; it adds indirection between task definition and execution that must be understood by all engineers working on the codebase.
- Redis result backend TTL must be configured to avoid unbounded memory growth.

*Risks and mitigations:*
- **Risk**: `acks_late=False` means a task is lost if the worker crashes mid-execution (message already acknowledged). **Mitigation**: This is the correct trade-off given REQ-009 (no duplicates > no loss); lost tasks will be re-triggered on the next scheduled interval. For audit-critical tasks with longer execution windows, the task must write an in-progress marker to the database before calling external services so that a crash is detectable.

---

### ADR-003 — WSGI Server: Gunicorn

**Title:** Gunicorn as the Production WSGI Server

**Context:**
The application currently starts via `python app.py`, which invokes `app.run()` — the Flask/Werkzeug development server. The development server is single-threaded, not suitable for concurrent requests, not designed for production traffic, and emits a startup warning that it should not be used in production. REQ-003 requires a production-grade WSGI server with ≥120-second request timeout.

**Decision:**
Use **Gunicorn** as the production WSGI server, invoked from `start.sh` with a 120-second worker timeout. Gunicorn is pre-existing in the project context (referenced in glossary) and is the de facto standard for synchronous Flask applications.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **uWSGI** | Higher performance ceiling; more configuration options; supports async protocols | Significantly more complex configuration; Emperor mode and vassal configuration are non-trivial; harder to debug; unnecessary complexity for "thousands of requests per day" load |
| **Waitress** | Pure-Python; no C extension dependency; Windows-compatible | Lower throughput ceiling; smaller community; less operator familiarity in Linux/Docker deployments; fewer production deployment examples in Flask ecosystem |
| **Do nothing (keep Werkzeug)** | Zero engineering effort | Violates REQ-003; security risk (development server exposes debug information); no worker timeout control; single-threaded; not suitable for production |

**Consequences:**

*Positive:*
- `--timeout 120` satisfies REQ-003's ≥120-second requirement out of the box.
- Pre-fork worker model is well-understood and production-proven.
- `--access-logfile -` routes access logs to stdout, compatible with container log aggregation.

*Negative trade-offs:*
- Synchronous workers; blocking I/O in route handlers (e.g., long-running DB queries) ties up a worker. Not a concern at "thousands of requests per day" volume with standard indexing.

*Risks and mitigations:*
- **Risk**: Developer accidentally runs `python app.py` instead of `bash start.sh`. **Mitigation**: COMP-001 is the sole documented entry point in README.md, CONTRIBUTING.md, and docker-compose.yml. The `start.sh` script must not be made executable conditionally — it is always the production entry point.

---

### ADR-004 — Credential Management: Environment Variables with Localhost-Only Fallback

**Title:** Runtime Credential Injection via Environment Variables

**Context:**
Test credentials (`TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`) are currently hardcoded as string literals in `tests/config.py`. This violates REQ-002 and REQ-013, exposes credentials to anyone with repository read access, and causes secret detection scanners to fail. REQ-013 prohibits credentials from appearing in source code, git history, CI logs, or pipeline artifacts.

**Decision:**
Resolve all test credentials from named environment variables at runtime (COMP-006). Permit a documented localhost-only fallback to non-production default values for individual developer convenience. Enforce hard failure (exception) when variables are absent in any non-localhost environment. Existing application secrets (database URL, Flask secret key, OAuth credentials) remain managed via environment variable injection from the deployment platform — this is the existing pattern and is not changed by this branch.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **HashiCorp Vault or AWS Secrets Manager** | Industry-standard secret lifecycle management; secret rotation; access audit logs | Significant scope expansion; requires new infrastructure; overkill for the current threat model and team size; explicitly a non-goal in the approved specification |
| **Encrypted `.env` file committed to repository** | Credentials not in plain text in source; developer convenience | Encryption key itself must be managed somewhere; encrypted blob still in git history; adds complexity without meaningfully closing the gap; not compatible with standard secret detection tooling |
| **Do nothing (keep hardcoded literals)** | Zero engineering effort | Violates REQ-002 and REQ-013; credentials leak via git clone; secret detection blocks CI pipeline permanently; constitutes a security exposure |

**Consequences:**

*Positive:*
- No credential literals in any file tracked by git after this change.
- Consistent with how all other application secrets are already managed (environment variable injection).
- Secret detection CI stage will pass (zero findings for credential literals).

*Negative trade-offs:*
- Developers must populate environment variables locally before running tests; one-time setup friction. Mitigated by clear documentation in CONTRIBUTING.md.
- If `.env` files with fallback values are accidentally committed, the fallback protection is undermined. Mitigated by `.gitignore` entry for `.env` files (should already be present; verify and add if missing).

*Risks and mitigations:*
- **Risk**: `is_localhost` detection logic produces a false positive in a shared environment, allowing the fallback to activate silently. **Mitigation**: The detection logic defaults to `False` (non-localhost) in ambiguous cases; CI environments must set `CI=true` (GitLab does this automatically); the fallback values must be non-functional in any shared environment (i.e., they do not correspond to any real account).

---

### ADR-005 — Security Scanning: GitLab Native Templates + pip-audit

**Title:** CI/CD Security Scanning via GitLab SAST and Secret Detection Templates Plus pip-audit

**Context:**
REQ-005 requires three security scanning capabilities: (1) dependency vulnerability scanning that fails on CVE and produces a machine-readable artifact, (2) Python SAST, and (3) git-history secret scanning. These must run before any build artifact is produced. The CI/CD platform is GitLab.

**Decision:**
Use GitLab's built-in `Security/SAST.gitlab-ci.yml` template (Bandit-based for Python) for SAST, GitLab's `Security/Secret-Detection.gitlab-ci.yml` template for secret scanning, and `pip-audit` (invoked as a pipeline shell command) for dependency vulnerability scanning. All three run as jobs in a dedicated `security` stage defined before `build`.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **Safety (pypa/safety) instead of pip-audit** | Well-known; PyPI vulnerability database integration | Requires a commercial license for up-to-date database access; free tier is stale; pip-audit uses OSV and PyPI Advisory DB which are freely maintained and current |
| **Snyk as a standalone scanning platform** | Comprehensive; developer-friendly UI; license scanning | Requires Snyk account and token management; external SaaS dependency; adds cost and operational dependency; GitLab native templates cover the stated requirements without external dependencies |
| **Bandit invoked directly (without GitLab template)** | Full control over Bandit configuration and version | GitLab SAST template manages Bandit versioning, report format, and GitLab Security Dashboard integration; no benefit to manual invocation for the current threat model |
| **Do nothing** | Zero effort | Violates REQ-005 and REQ-013; known-CVE dependencies can be deployed; committed secrets are not detected; pipeline produces no security signal |

**Consequences:**

*Positive:*
- GitLab templates are maintained by GitLab; no custom tooling to maintain.
- GitLab Secret Detection scans the full git history by default — satisfying REQ-005's history-scanning requirement without additional configuration.
- `pip-audit` produces a JSON artifact that satisfies the "machine-readable scan report as a pipeline artifact" requirement.

*Negative trade-offs:*
- GitLab SAST and Secret Detection templates are updated by GitLab; a template update could change scanner behaviour or findings without a code change.
- `pip-audit` produces false positives for CVEs in transitive dependencies. **Mitigation**: Accept the friction; CVEs in transitive dependencies should also be remediated (upgrade to a parent version that resolves the transitive dep). If the rate of false positives becomes unacceptable, a `.pip-audit-ignore` file can be introduced in a future branch.

---

### ADR-006 — Input Validation Strategy: Centralized Utility Module

**Title:** Shared Input Validation Utility for All Form-Handling Route Handlers

**Context:**
REQ-008 requires that all user-submitted input is validated before any data is persisted, and that validation failures produce specific, field-identified error messages. The existing ~45–50 route handlers have inconsistent or absent validation — some partially validate, most do not. There is no shared validation abstraction. The choice of validation strategy determines the consistency and maintainability of REQ-008 coverage.

**Decision:**
Introduce a centralized `utils/validation.py` utility module (COMP-010) providing a small set of pure validation functions that return typed error descriptors. Route handlers assemble validator calls using this utility before any database operation. This is a utility module, not a framework — it does not introspect form schemas or auto-discover fields.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **WTForms integration** | Declarative form schemas; built-in CSRF protection; Flask-WTF integration | Requires replacing or wrapping all 45–50 existing form handlers with WTForms Form classes — a large refactor that exceeds the scope of this hardening branch and risks introducing regressions across the entire route surface |
| **Pydantic / Flask-Pydantic** | Type-safe validation; automatic coercion; rich error model | Same refactor scope problem as WTForms; introduces a Pydantic dependency; incompatible with the "no breaking changes" compatibility constraint for this branch |
| **Inline validation per route (no shared utility)** | No new abstraction; minimal change | Does not enforce a consistent validation pattern; error message format will diverge across routes; code review cannot systematically verify REQ-008 compliance; does not satisfy the specification's requirement for testable, observable validation behavior |

**Consequences:**

*Positive:*
- Every route handler uses the same error descriptor format — consistent UX across the application.
- `validate_form()` validates all fields before returning errors — users see all errors at once, not one at a time.
- Pure functions are straightforward to unit-test with no Flask app context required.
- Minimal scope — no existing route handler structure is redesigned; only a validation call is added before the persistence block.

*Negative trade-offs:*
- Route handlers must be individually modified to add validation calls. With ~45–50 routes, this is significant but bounded work. Mitigation: The scope is limited to routes that handle form POSTs (not all 45–50 routes handle POSTs with persistent data).
- The utility does not enforce that routes *use* it — a new route can be added without calling `validate_form()`. **Mitigation**: Code review checklist must include verification that all form-handling POST routes call `validate_form()`. This is the same governance gap as the existing RBAC inline enforcement pattern, and is accepted as a known trade-off for this branch scope.

---

## Implementation Guidelines

### File Structure

Every file to be created or modified, with its purpose and component ID:

**New Files:**

| File Path | Purpose | Component |
|-----------|---------|-----------|
| `start.sh` | Production Gunicorn entry point with 120s timeout | COMP-001 |
| `startup_checks.py` | Pre-flight validation of all required config; terminates process on failure | COMP-002 |
| `services/celery_app.py` | Celery application factory; exports `celery_app` instance | COMP-003 |
| `celeryconfig.py` | Celery Beat periodic schedule; defines all task triggers | COMP-005 |
| `services/worker_status.py` | Safe Celery worker status query; never raises; returns degraded state on failure | COMP-011 |
| `utils/validation.py` | Input validation utility functions and error descriptor type | COMP-010 |
| `utils/__init__.py` | Package marker for `utils/` directory (if not already present) | COMP-010 |
| `migrations/README.md` | Migration classification registry; superseded script warnings | COMP-007 |

**Modified Files:**

| File Path | What Changes | What Stays the Same | Component |
|-----------|-------------|---------------------|-----------|
| `start.sh` | Created new | N/A | COMP-001 |
| `app.py` | Remove APScheduler initialization and `app.run()` call; add `from services.celery_app import celery_app` and Celery-Flask binding; call `run_startup_checks(app)` from factory | All Blueprint registrations; all middleware registrations; `Config.init_from_database()`; session handling; all other factory logic | COMP-002, COMP-003 |
| `services/ctask_scheduler.py` | Replace `@scheduler.scheduled_job` decorators with `@celery_app.task(...)` decorators and retry configuration; add structured log statements | All underlying task business logic (email construction, API calls, retry-eligible operations) | COMP-004 |
| `tests/config.py` | Replace credential literals with environment variable resolution and localhost fallback gate | Exported variable names (`TEST_SUPERADMIN_PASSWORD`, etc.); import patterns used by test modules | COMP-006 |
| `.gitlab-ci.yml` | Add `security` stage to `stages:` list before `build`; add `dependency-scan` job; add `include:` for SAST and Secret Detection templates; override template jobs to run in `security` stage | All existing stages, jobs, and pipeline structure | COMP-008 |
| `.gitignore` | Append binary documentation exclusion patterns as a labelled section | All existing ignore entries | COMP-009 |
| `docker-compose.yml` | Change `web` service command to `bash start.sh`; add `redis`, `celery-worker`, `celery-beat` services; add `env_file` or `environment:` blocks using `${VAR}` syntax | All other service definitions; volume mounts; network configuration | COMP-012 |
| `routes/dashboard*.py` | Import and call `get_worker_status()` from COMP-011; pass result to template context | Route paths; authentication checks; all other template context variables | COMP-011 |
| All form-handling `routes/*.py` | Import `validate_form`, `format_error_response` from COMP-010; add validation block before persistence | Route paths; HTTP methods; auth checks; RBAC logic; success response paths; all non-form routes | COMP-010 |
| `CONTRIBUTING.md` | Add section: "Running the Test Suite — Environment Variable Setup"; document `TEST_*` env var names; document localhost fallback values | All existing content | COMP-006 |
| `CLAUDE.md` (if present) | Update credential examples to show env var pattern, not literals | All other content | COMP-006 |

---

### Naming Conventions

Consistent with existing project patterns observed in the context library:

| Category | Convention | Example |
|----------|-----------|---------|
| **Python modules** | `snake_case` | `worker_status.py`, `celery_app.py` |
| **Python functions** | `snake_case` | `get_worker_status()`, `validate_required()` |
| **Python constants / env var names** | `UPPER_SNAKE_CASE` | `TEST_SUPERADMIN_PASSWORD`, `CELERY_BROKER_URL` |
| **Celery task names** | `shiftops.<task_name>` (explicit string) | `"shiftops.email_digest"` |
| **Log event prefixes** | `TASK_`, `STARTUP_`, `WORKER_STATUS_` | `TASK_COMPLETED`, `STARTUP FAILURE` |
| **Component IDs in code comments** | Reference by COMP-NNN where a design decision is non-obvious | `# COMP-002: startup validation` |
| **Blueprint module filenames** | Existing `routes/<domain>.py` pattern | Unchanged |
| **Docker service names** | `kebab-case` | `celery-worker`, `celery-beat` |

---

### Patterns to Use

| Pattern | Rationale |
|---------|-----------|
| **Flask application factory** | Existing pattern in `app.py`; Celery-Flask binding must use this pattern to ensure tasks execute within the Flask app context (access to SQLAlchemy, config, etc.) |
| **Celery `bind=True` on all tasks** | Gives the task access to `self.retry()` and `self.request.retries` for retry counting and logging |
| **`autoretry_for` over manual `self.retry()` calls** | Reduces boilerplate; ensures retry policy is applied consistently even when exceptions are unexpected; cleaner task code |
| **`validate_form()` call before any `db.session` operation** | Enforces the invariant that no partial records are created; must be the first statement in the POST-handling block |
| **`try/except` with explicit exception types in COMP-011** | Only catch known failure modes; log the exception; return degraded state — never silently swallow `Exception` without logging |
| **`sys.exit(1)` in startup checks** | Hard process termination ensures no partially-initialized state; Gunicorn respects non-zero exit and does not continue |
| **Structured log statements with key=value pairs** | Enables log aggregation queries without regex; consistent with `TASK_COMPLETED task=<name> task_id=<id>` pattern |

---

### Patterns to Avoid

| Anti-Pattern | Explanation |
|-------------|-------------|
| **`app.run()` anywhere in production code paths** | Invokes Werkzeug dev server; must only exist inside `if __name__ == '__main__': app.run(debug=True)` guard for local development, if at all; `start.sh` is the sole production entry point |
| **APScheduler `BackgroundScheduler` in any module imported by the web process** | The root cause of the duplicate task execution bug; must not be re-introduced in any form within `app.py` or any module imported at Flask startup |
| **Hardcoded credential literals in any file** | Violates REQ-013; will be detected by secret detection CI stage and block the pipeline |
| **`except Exception: pass` or `except Exception: continue`** | Silent exception swallowing makes failures unobservable; violates REQ-010's observability requirement; the only permitted silent swallow is in COMP-011 where the exception is logged at WARNING before returning the degraded result |
| **Direct `os.environ["VAR"]` in task or model modules** | Environment access must be centralised to COMP-002 (startup) and COMP-006 (test config); task modules receive values through the Flask config or Celery app configuration |
| **Multiple `celery-beat` container instances** | Each Beat instance dispatches independent triggers; two Beat instances produce duplicate task messages; replicas must be constrained to 1 |
| **Database writes before `validate_form()` completes** | Creates partial records; violates REQ-008 acceptance criteria; the validation call must precede all `db.session.add()` and `db.session.commit()` calls |
| **`celery.control.inspect()` without a timeout** | Without a timeout, the inspect call blocks indefinitely if the broker is unreachable; COMP-011 must always pass `timeout=<seconds>` |

---

### New Dependencies

| Library | Version Constraint | Purpose | ADR Reference |
|---------|--------------------|---------|--------------|
| `celery` | `>=5.3,<6.0` (pin minor; avoid Celery 6 API changes) | Distributed task queue; Beat scheduler | ADR-002 |
| `redis` (Python client) | `>=5.0,<6.0` (matches celery[redis] extras) | Redis broker and result backend client for Celery | ADR-002 |
| `gunicorn` | `>=21.0,<23.0` | Production WSGI server | ADR-003 |
| `pip-audit` | Latest stable (installed in CI runner; not in `requirements.txt`) | Dependency vulnerability scanning in CI pipeline | ADR-005 |

**Notes:**
- `celery[redis]` should be added to `requirements.txt` as the extras-enabled form to pull in the Redis transport client.
- `gunicorn` should be added to `requirements.txt` if not already present.
- `pip-audit` is a CI tool, not a runtime dependency; it must not appear in `requirements.txt` (doing so would cause it to be scanned by itself, creating circular logic).
- All version pins must be re-evaluated against the `pip-audit` scan on first pipeline run. Any pinned version with a known CVE must be upgraded before the branch is merged.

---

## Testing Strategy

### Unit Tests

All new utility modules must have standalone unit tests that require no Flask application context or external services.

| Component | Test Target | Test Scenarios |
|-----------|-------------|----------------|
| **COMP-010** `utils/validation.py` | `validate_required()` | Empty string → error; whitespace-only string → error; `None` → error; valid string → `None` |
| **COMP-010** `utils/validation.py` | `validate_not_null()` | `None` → error; `0` / `""` / `False` → `None` (not null); valid value → `None` |
| **COMP-010** `utils/validation.py` | `validate_range()` | Value at min boundary → `None`; value at max boundary → `None`; value below min → error with message containing min/max/received; value above max → error |
| **COMP-010** `utils/validation.py` | `validate_form()` | Single passing validator → empty list; single failing validator → list of one error; multiple validators, one failing → list of one error; multiple validators, all failing → list of all errors (no short-circuit) |
| **COMP-010** `utils/validation.py` | `format_error_response()` | Empty list → `{"errors": []}`; one error → correct structure; multiple errors → all present |
| **COMP-006** `tests/config.py` | `is_localhost` detection | `CI=true` env var set → non-localhost; no CI env vars, loopback hostname → localhost |
| **COMP-006** `tests/config.py` | Credential resolution | Env var set → value returned; env var absent + localhost → fallback returned; env var absent + non-localhost → `EnvironmentError` raised |
| **COMP-002** `startup_checks.py` | `run_startup_checks()` | Missing required env var → `sys.exit(1)` called with logged message naming the var; DB unreachable → `sys.exit(1)` with logged message; Redis unreachable → `sys.exit(1)` with logged message; all checks pass → returns normally |
| **COMP-011** `services/worker_status.py` | `get_worker_status()` | Inspect returns worker data → `available=True` with correct counts; inspect raises `ConnectionError` → `available=False`, `error` field non-None, no exception raised; inspect times out → same degraded result; inspect returns None → `available=False` |

**Test file locations** (following existing project structure):
- `tests/test_validation.py` — COMP-010 tests
- `tests/test_startup_checks.py` — COMP-002 tests
- `tests/test_worker_status.py` — COMP-011 tests
- COMP-006 tests embedded in `tests/test_config.py` or the existing test configuration test file

---

### Integration Tests

| Scenario | What is Tested | Test Approach |
|----------|---------------|---------------|
| **Form submission validation — empty required field** | Full POST request to a form-handling route with a missing required field returns an error response; no database record created | Flask test client; assert response contains error message for the field; assert DB count unchanged |
| **Form submission validation — valid input** | Full POST request with valid data persists the record | Flask test client; assert success response; assert DB record created |
| **Dashboard with worker status unavailable** | Dashboard route returns HTTP 200 when Celery broker is unreachable | Flask test client; mock `services.worker_status.get_worker_status` to return `available=False`; assert response.status_code == 200 |
| **Celery task dispatch** | A task dispatched via `celery_app.send_task()` is received and executed by a worker | Requires a running Redis and Celery worker (Docker); assert task result is SUCCESS; assert structured log entry `TASK_COMPLETED` appears |
| **Celery task retry on transient failure** | A task that raises a retryable exception on first attempt retries and eventually succeeds | Mock external service to fail twice then succeed; assert task result is SUCCESS; assert `TASK_RETRY` log entries appear with correct attempt numbers |
| **Celery deduplication with 3 web workers** | With 3 Gunicorn workers and 1 Beat/1 Celery worker, a scheduled trigger fires exactly once | Requires Docker; trigger one scheduled task; assert exactly one `TASK_COMPLETED` log entry in a 24-hour window |
| **Startup validator — missing env var** | Application fails to start when a required env var is absent | Invoke `run_startup_checks()` with a patched environment missing one variable; assert `SystemExit` raised with code 1 |

---

### E2E Scenarios

| ID | Scenario | Steps | Expected Outcome |
|----|----------|-------|-----------------|
| E2E-001 | Email digest with 3 workers | Start docker-compose with `celery-worker replicas=1`, `web replicas=3`; trigger email digest task; wait 60s | Exactly one email sent; exactly one `TASK_COMPLETED` log entry |
| E2E-002 | CI pipeline blocks on CVE | Add a dependency with a known CVE to `requirements.txt`; push branch; observe pipeline | `dependency-scan` job fails; `pip-audit-report.json` artifact saved; build stage not reached |
| E2E-003 | CI pipeline blocks on committed secret | Commit a file containing a mock credential literal (not a real secret) to a branch; push; observe pipeline | `secret_detection` job fails; build stage not reached; finding reported with file reference |
| E2E-004 | MR self-approval blocked | Author opens MR; author attempts to approve own MR | Approval rejected; approval count remains 0; merge blocked |
| E2E-005 | MR peer approval permits merge | Author opens MR; peer reviewer approves; author merges | Merge completes; branch protection satisfied |
| E2E-006 | Task retries on ServiceNow unavailability | Simulate ServiceNow endpoint returning 503; trigger relevant scheduled task; observe | Task retries up to 3 times at ≥30-second intervals; final `TASK_FAILED` log entry with `attempts_exhausted=3` |
| E2E-007 | Dashboard degrades gracefully | Stop Redis (celery broker); navigate to dashboard | Core dashboard returns HTTP 200; worker status widget shows degraded state; no error propagated to user |
| E2E-008 | Application startup fails on missing env var | Start container with `SECRET_KEY` env var unset | Process exits with code 1; log contains `STARTUP FAILURE: Required environment variable 'SECRET_KEY' is not set.` |

---

### Coverage Approach

| Component | Target Coverage | Rationale |
|-----------|----------------|-----------|
| `utils/validation.py` | ≥95% line coverage | Pure functions; critical correctness boundary; no external dependencies make coverage easy to achieve |
| `startup_checks.py` | ≥90% line coverage | Startup failures have significant operational impact; every check branch must be verified |
| `services/worker_status.py` | ≥90% line coverage | Graceful degradation logic is safety-critical; the "never raise" contract must be verified for all exception types |
| `tests/config.py` | ≥85% line coverage | Security-sensitive; fallback logic must be tested |
| `services/ctask_scheduler.py` (modified) | ≥70% line coverage | Business logic is unchanged; focus on retry decorator paths and log statement coverage |
| `services/celery_app.py` | Integration-tested; unit coverage not required | Configuration module; correctness verified by integration tests |
| `.gitlab-ci.yml`, `.gitignore`, `migrations/README.md`, `start.sh` | Not unit-testable | Correctness verified by E2E scenarios and manual review |

**Overall approach:** This hardening branch does not require full-application coverage uplift. Focus unit testing resources on the three new utility modules (COMP-002, COMP-010, COMP-011) and COMP-006, which contain logic that has clear correctness requirements, security implications, and no existing test coverage. Existing route handler coverage is out of scope except for the specific integration tests verifying form validation behaviour.

---

## Security Considerations

### 1. Credential Leakage in Source Code and Git History

- **Concern**: Test credentials and application secrets committed as literal strings in source files are permanently accessible to anyone with git clone access, including future repository mirrors.
- **Mitigation**: COMP-006 removes all literal credential values from `tests/config.py`. COMP-008 adds GitLab Secret Detection (full history scan) that blocks the pipeline on any credential literal in any commit. The localhost-only fallback values documented in CONTRIBUTING.md must be clearly marked as non-functional in shared environments and must not match any real account credential.
- **OWASP Category**: A07:2021 — Identification and Authentication Failures; A09:2021 — Security Logging and Monitoring Failures (credential exposure is undetected without scanning).

### 2. Dependency Vulnerabilities (CVEs)

- **Concern**: Third-party Python packages in `requirements.txt` may have published CVEs that expose the application to known exploits. Without scanning, vulnerable packages can be deployed silently.
- **Mitigation**: COMP-008 adds `pip-audit` to the `security` stage; the stage fails and blocks build artifact production on any CVE finding. Machine-readable `pip-audit-report.json` artifact is saved for remediation tracking. All new dependencies introduced by this branch (`celery`, `redis`, `gunicorn`) must be scanned before the branch is merged.
- **OWASP Category**: A06:2021 — Vulnerable and Outdated Components.

### 3. Static Application Security Analysis

- **Concern**: Python source code may contain security anti-patterns (SQL injection via string concatenation, use of `eval()`, unsafe deserialization, hardcoded secrets missed by pattern matching) that are not caught by CVE scanning.
- **Mitigation**: COMP-008 includes GitLab SAST (Bandit-based) running in the `security` stage before build. All findings at HIGH severity are blocking. Bandit configuration defaults are accepted per A-003 (sufficient coverage for current threat model).
- **OWASP Category**: A03:2021 — Injection; general SAST coverage.

### 4. User Input Validation (Injection Prevention)

- **Concern**: Unvalidated user input submitted to form handlers can be used for SQL injection, XSS, or data integrity attacks. The existing inline RBAC pattern creates a risk that form-handling routes accept malformed or oversized input without validation.
- **Mitigation**: COMP-010 provides centralized input validation enforced before any database operation. All form-handling POST routes must call `validate_form()` before any SQLAlchemy write. SQLAlchemy's parameterized query model already prevents SQL injection from ORM-level operations; COMP-010 addresses data integrity and application-level constraint violations.
- **OWASP Category**: A03:2021 — Injection; A04:2021 — Insecure Design (business logic validation).

### 5. Authentication Token Management

- **Concern**: Session tokens must remain valid and enforceable; changes to the task infrastructure must not affect the per-request `validate_session()` middleware.
- **Mitigation**: The session token validation mechanism (`validate_session()` middleware, `session_tokens` table, administrator-forced revocation) is explicitly unchanged by this branch (compatibility constraint). COMP-002 validates database reachability at startup — if the database is unreachable, the session validation mechanism cannot function and the application must not start. No Celery task reads or writes session token records.
- **OWASP Category**: A07:2021 — Identification and Authentication Failures.

### 6. PII Handling in Task Execution

- **Concern**: Email digest tasks and ServiceNow polling tasks process user data (shift records, incident data, email addresses) as part of their business logic. This PII must not appear in task execution logs or the Celery result backend.
- **Mitigation**: The structured log contract for COMP-004 defines log messages using only task name, task ID, attempt count, and error class — never user data or record content. The Celery result backend stores task return values; task functions must return only status metadata (not record contents) in their return dict. PII that must be referenced within a task should be passed as database record IDs, not as serialized user data in task arguments (which are stored in Redis).
- **OWASP Category**: A02:2021 — Cryptographic Failures (data exposure); GDPR / privacy considerations.

### 7. CI/CD Pipeline Security

- **Concern**: Pipeline logs and pipeline artifacts could expose credentials if environment variable values are accidentally echoed or if pip-audit includes them in its report.
- **Mitigation**: Test credentials are injected as masked CI/CD variables (GitLab's masked variable feature suppresses their value in pipeline logs). `pip-audit-report.json` contains only package names, versions, and CVE IDs — no credentials. The `dependency-scan` job must not print `pip install` output verbosely (use `--quiet` flag or redirect to `/dev/null`).
- **OWASP Category**: A09:2021 — Security Logging and Monitoring Failures.

### 8. Authorization — Route-Level Gaps (Existing Risk, Not Introduced by This Branch)

- **Concern**: The existing pattern of inline RBAC (no shared `@require_role` decorator) creates a risk that new routes added by this branch (none) or future branches could be added without authorization checks.
- **Mitigation**: This branch adds zero new routes, so no new authorization gaps are introduced. COMP-010 (validation utility) is not an authorization control. The existing RBAC gap is documented in the approved specification as a known risk and is not in scope for this branch. Code review checklist for future branches must explicitly check for `@require_role` absence.
- **OWASP Category**: A01:2021 — Broken Access Control.

---

## Error Handling Strategy

### Error Classification and Strategy Mapping

| Error Category | Strategy | Implementation |
|----------------|----------|---------------|
| Missing required env var / DB unreachable at startup | **Abort (Strategy A)** | `sys.exit(1)` in COMP-002; logged at CRITICAL before exit; no partial startup |
| Transient external service failure in background task | **Retry (Strategy C)** | Celery `autoretry_for`, `max_retries=3`, `default_retry_delay=30` in COMP-004; logged at WARNING per attempt |
| Exhausted retries in background task | **Terminal Failure** | Exception propagates; Celery records FAILURE in result backend; logged at ERROR with `TASK_FAILED` prefix |
| Celery worker / broker unreachable during dashboard request | **Graceful Degrade (Strategy D)** | COMP-011 catches all exceptions; returns `available=False`; dashboard renders degraded UI; core routes unaffected |
| User input validation failure on form submission | **Reject with Message** | COMP-010 `validate_form()` returns errors; route handler returns error response without DB write; no retry |
| Database error after validation passes (unexpected) | **Surface as 500** | SQLAlchemy exception propagates to Flask error handler; transaction rolled back; user sees generic error message; full exception logged internally |
| Audit-critical operation failure (handover submission) | **Retry then Abort** | If invoked as Celery task: retry (Strategy C); if invoked synchronously in a route: exception raised → transaction rolled back → 500 response → full exception logged; never silent |

### Error Propagation Chain

```
User Form Submission (POST):
  Route handler → COMP-010 validate_form()
    → [errors present] → return error response immediately (no DB write, no propagation)
    → [valid] → SQLAlchemy operation
        → [DB exception] → SQLAlchemy rolls back transaction
                         → exception propagates to Flask error handler
                         → Flask renders 500 (or error template)
                         → exception logged at ERROR with full traceback
                         → user sees "An error occurred" message

Background Task Execution:
  Celery Beat → Redis → Celery worker → Task function
    → [ExternalServiceError] → logged at WARNING (TASK_RETRY)
                              → retry after 30s (up to 3 times)
                              → [eventual success] → logged at INFO (TASK_COMPLETED)
                              → [retries exhausted] → logged at ERROR (TASK_FAILED)
                                                    → FAILURE state in result backend
                                                    → no further automatic retry
                                                    → web tier unaffected

Dashboard Request:
  Route handler → COMP-011 get_worker_status()
    → [broker/worker available] → WorkerStatusResult(available=True) → normal UI
    → [any exception] → caught internally → logged at WARNING
                      → WorkerStatusResult(available=False) → degraded UI widget
                      → route continues → HTTP 200 returned

Application Startup:
  COMP-002 run_startup_checks()
    → [any required config absent] → CRITICAL log → sys.exit(1) → process terminates
    → [all checks pass] → returns normally → application starts
```

### User-Facing Error Messages vs. Internal Logging

| Error Type | User-Facing Message | Internal Log |
|-----------|-------------------|-------------|
| Validation failure | Specific: `"<Field Name> is required and must not be empty."` | Not logged (expected business event) |
| Out-of-range value | Specific: `"<Field Name> must be between X and Y. Received: Z."` | Not logged |
| Worker status unavailable | Degraded UI indicator only; no error text shown to user | `WARNING: WORKER_STATUS_CHECK_FAILED: <exception>` |
| Database error during request | Generic: `"An error occurred. Please try again."` | `ERROR: <full exception with traceback>` |
| Startup configuration failure | Not shown to users (process exits before accepting traffic) | `CRITICAL: STARTUP FAILURE: Required environment variable '<NAME>' is not set.` |
| Task transient failure (retry) | Not shown to users | `WARNING: TASK_RETRY task=<name> task_id=<id> attempt=<N> reason=<error>` |
| Task terminal failure | Not shown to users | `ERROR: TASK_FAILED task=<name> task_id=<id> attempts_exhausted=3 error=<str>` |

### Retry Strategy

| Trigger | Max Retries | Delay | Backoff | Terminal State |
|---------|------------|-------|---------|----------------|
| Transient external service error in Celery task | 3 | 30 seconds (minimum, flat) | None (no exponential backoff — flat interval satisfies REQ-010; exponential backoff is a future optimization) | FAILURE recorded in result backend; `TASK_FAILED` log entry |
| Database reconnection (SQLAlchemy connection pool) | Managed by SQLAlchemy pool; not application-level | N/A | N/A | Connection error propagates to caller |

### Graceful Degradation Contract

When the Celery broker or worker status endpoint is unavailable:
- `routes/dashboard*.py` continues to serve requests normally.
- COMP-011 `get_worker_status()` returns `WorkerStatusResult(available=False)` within the configured timeout (default 1 second).
- The `1.0` second timeout ensures that a broker outage does not add more than 1 second of latency to dashboard page loads.
- Only the worker status UI widget reflects the degraded state. All other dashboard functionality (shift data, incident stats, KPIs) is unaffected.
- This behaviour is measurable: during a simulated broker outage, `GET /dashboard` must return HTTP 200 with a response time within normal parameters (not delayed by the 1-second timeout beyond the acceptable web response budget). The 1-second timeout is the designed upper bound for degradation latency.

---

*End of Architecture Design Specification — CTCOAMSHM-7*