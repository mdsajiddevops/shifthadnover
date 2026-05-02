## Summary

This branch closes 8 medium-severity production-readiness gaps across infrastructure, security, process, and documentation in the ShiftOps Flask monolith (CTCOAMSHM-7). The work separates background task execution from the web process via a Celery + Redis worker architecture, replaces the Flask development server with Gunicorn, hardens credentials and CI/CD scanning, and adds centralised input validation — all as additive or internal-only changes with zero modifications to existing route contracts, schemas, or RBAC definitions. No new user-visible features are introduced.

---

## Key Requirements & Constraints

| ID | Priority | Description |
|----|----------|-------------|
| REQ-001 | P0 | Scheduled background tasks (digests, polling, retries) shall execute in a process isolated from the web-serving process; multiple concurrent Gunicorn workers must not produce duplicate executions. |
| REQ-002 | P0 | All test-suite authentication credentials shall be resolved from named environment variables; a localhost-only fallback to documented defaults is the sole permitted exception. |
| REQ-003 | P0 | All production HTTP traffic shall be served by a production-grade WSGI server with ≥120-second request timeout; the Flask development server shall never be the production entry point. |
| REQ-004 | P1 | The repository shall contain a human-readable document classifying every migration script as: applied to production, superseded (do not re-apply), or environment-specific; all future schema changes shall use the versioned migration toolchain exclusively. |
| REQ-005 | P0 | The CI/CD pipeline shall enforce a security stage before any build artifact is produced, comprising: (1) dependency CVE scan with machine-readable artifact, (2) Python SAST, and (3) full git-history secret scanning. |
| REQ-006 | P1 | The repository shall contain no tracked binary documentation files (PDF, DOCX, XLSX, PPTX, PPT); these patterns shall be permanently excluded via repository ignore configuration. |
| REQ-007 | P1 | Every merge request targeting the protected main branch shall require at least one peer-reviewer approval; authors shall be prohibited from self-approving. |
| REQ-008 | P0 | All user-submitted form input shall be validated on submission; any failure shall return a specific, field-identified, human-readable error message with no partial record persisted. |
| REQ-009 | P0 | Zero duplicate task executions shall be observed when the web-serving process is scaled to three or more concurrent workers, measured over a 24-hour observation window. |
| REQ-010 | P1 | Scheduled tasks encountering a transient external-service failure shall auto-retry up to 3 times with ≥30-second delay between attempts; retry count and final status shall be observable without manual log parsing. |
| REQ-011 | P0 | The application shall terminate immediately at startup with a logged, human-readable error when any required configuration value is absent or any critical external service is unreachable; no partial startup state is permitted. |
| REQ-012 | P1 | A failure of any non-critical background instrumentation service (e.g., worker status queries) shall not propagate to the web tier; core routes shall remain fully functional during an instrumentation outage. |
| REQ-013 | P0 | Authentication credentials shall never appear in source code, git history, CI/CD logs, or pipeline artifacts; the sole exception is an explicitly documented localhost-only developer fallback value. |

---

## Architecture Summary

The design adopts a **Process-Isolated Worker Architecture** layered on the existing Flask SSR monolith, requiring no changes to route contracts, schemas, session formats, or RBAC definitions.

**Key Design Decisions (ADRs):**

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | Process-isolated Celery worker + Redis broker | Eliminates APScheduler co-location with Gunicorn workers, the root cause of duplicate task execution on scale-out. Distributed-lock and cron-container alternatives were rejected as fragile or lacking retry/observability primitives. |
| ADR-002 | Celery with Redis as both broker and result backend | Satisfies REQ-009/REQ-010 retry semantics natively via `autoretry_for`, `max_retries`, and `default_retry_delay` parameters; `celery.control.inspect` delivers COMP-011 worker status with a single call; lower operational footprint than RabbitMQ at "thousands of requests/day" volume. |
| ADR-003 | Gunicorn via `start.sh` as sole production entry point | Pre-existing in project context; `--timeout 120` satisfies REQ-003 out-of-the-box; pre-fork worker model is production-proven; eliminates all `app.run()` / Werkzeug dev-server code paths. |
| ADR-004 | Environment variable injection with localhost-only fallback | Consistent with existing application secret management; eliminates credential literals from source; `is_localhost` detection defaults to `False` in ambiguous cases to prevent fallback activation in shared environments. |
| ADR-005 | GitLab SAST + Secret Detection templates + `pip-audit` | Platform-native templates (no external SaaS dependency); `pip-audit` uses OSV/PyPI Advisory DB (free, current); JSON artifact satisfies machine-readable report requirement; full git-history scan is default behaviour of the Secret Detection template. |
| ADR-006 | Centralised `utils/validation.py` utility module | Pure functions with zero Flask-context dependency; `validate_form()` validates all fields in one pass (no short-circuit); minimal scope — routes add a single call before persistence, no form schema redesign required. |

**Component Structure:**

| Component | File(s) | Responsibility |
|-----------|---------|---------------|
| COMP-001 | `start.sh` | Gunicorn production entry point; 120s timeout; no dev-server fallback |
| COMP-002 | `startup_checks.py` | Pre-flight env var + DB + Redis reachability checks; `sys.exit(1)` on failure |
| COMP-003 | `services/celery_app.py` | Celery application factory; Flask-Celery binding; broker/backend config |
| COMP-004 | `services/ctask_scheduler.py` (modified) | APScheduler jobs replaced with `@celery_app.task` decorators; retry policy; structured `TASK_*` log contract |
| COMP-005 | `celeryconfig.py` | Celery Beat periodic schedule; single authoritative trigger source |
| COMP-006 | `tests/config.py` (modified) | Env-var credential resolution; localhost fallback gate; `EnvironmentError` on absent vars in CI/prod |
| COMP-007 | `migrations/README.md` | Migration classification registry; superseded-script warnings; future migration policy |
| COMP-008 | `.gitlab-ci.yml` (modified) | `security` stage before `build`; `dependency-scan` + SAST + Secret Detection jobs |
| COMP-009 | `.gitignore` (modified) | Binary documentation file exclusion patterns; `git rm --cached` one-time cleanup |
| COMP-010 | `utils/validation.py` | Pure validation functions; typed `ValidationError` descriptor; `validate_form()` multi-field pass |
| COMP-011 | `services/worker_status.py` | Safe Celery worker status query; 1s timeout; never raises; returns `available=False` on any failure |
| COMP-012 | `docker-compose.yml` (modified) | Adds `redis`, `celery-worker`, `celery-beat` services; `web` command changed to `bash start.sh`; `celery-beat` constrained to `replicas: 1` |
| COMP-013 | GitLab project settings | Protected branch: no direct pushes; 1 required approval; self-approval disabled; approvals reset on new commits |

---

## Pre-Implementation Baseline

Run the following command before making any changes and save the output as the reference baseline. All tasks must eventually leave the test suite in a state that is equal to or better than this baseline.

```bash
pytest tests/ -v --tb=short 2>&1 | tee baseline_test_results.txt; echo "Exit code: $?"
```

---

## Task Breakdown

| Task ID | Title | Dependencies | Effort (days) | Component | Type |
|---------|-------|--------------|---------------|-----------|------|
| T-001 | Verify pre-implementation test baseline and record results | — | 0.25 | — | config |
| T-002 | Append binary documentation exclusion patterns to `.gitignore` | T-001 | 0.25 | COMP-009 | config |
| T-003 | Remove tracked binary documentation files from git tracking via `git rm --cached` | T-002 | 0.25 | COMP-009 | modify |
| T-004 | Author `migrations/README.md` migration classification document | T-001 | 0.5 | COMP-007 | new |
| T-005 | Configure GitLab branch protection (no direct push to main) and MR approval rules (1 peer required, self-approval disabled) | T-001 | 0.25 | COMP-013 | config |
| T-006 | Update `CONTRIBUTING.md` and `CLAUDE.md` with env var credential setup instructions and documented localhost fallback values | T-001 | 0.25 | COMP-006 | modify |
| T-007 | Add `celery[redis]` and `gunicorn` to `requirements.txt`; remove `APScheduler` if present as a standalone entry | T-001 | 0.25 | COMP-003, COMP-001 | modify |
| T-008 | Implement Celery application factory (`services/celery_app.py`) with broker/backend config, serialiser settings, and Flask app-context binding pattern | T-007 | 0.5 | COMP-003 | new |
| T-009 | Implement Celery Beat periodic schedule configuration (`celeryconfig.py`) with all existing task triggers migrated from APScheduler, `replicas: 1` constraint noted | T-008 | 0.5 | COMP-005 | new |
| T-010 | Refactor `services/ctask_scheduler.py`: replace all `@scheduler.scheduled_job` decorators with `@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, autoretry_for=(...))` decorators; add structured `TASK_STARTED / TASK_COMPLETED / TASK_RETRY / TASK_FAILED` log statements; ensure task return values contain only status metadata (no PII) | T-008, T-009 | 1.5 | COMP-004 | modify |
| T-011 | Implement production WSGI entry point script (`start.sh`) invoking Gunicorn with `-w 1`, `-b 0.0.0.0:5000`, `--timeout 120`, `--access-logfile -`, `app:app`; no dev-server fallback path | T-007 | 0.25 | COMP-001 | new |
| T-012 | Implement application startup validator (`startup_checks.py`) with ordered checks for required env vars, database reachability, and Redis/broker reachability; `sys.exit(1)` with `CRITICAL` log on any failure | T-008 | 0.5 | COMP-002 | new |
| T-013 | Modify `app.py`: remove APScheduler initialisation and `app.run()` call; add Celery-Flask factory binding; call `run_startup_checks(app)` after config loading and before route registration | T-008, T-012 | 0.5 | COMP-002, COMP-003 | modify |
| T-014 | Implement test credential resolver in `tests/config.py`: replace all credential literals with `os.environ.get()` resolution; implement `is_localhost` detection defaulting to `False` in ambiguous cases; raise `EnvironmentError` naming the missing variable when absent in non-localhost environments | T-006 | 0.5 | COMP-006 | modify |
| T-015 | Create `utils/__init__.py` package marker and implement `utils/validation.py` with `validate_required`, `validate_not_null`, `validate_range`, `validate_max_length`, `validate_form`, and `format_error_response` pure functions; define `ValidationError` typed descriptor | T-001 | 0.5 | COMP-010 | new |
| T-016 | Audit all form-handling POST route handlers across `routes/*.py`; integrate `validate_form()` call before any `db.session` operation in each; update route templates to render field-level error messages; ensure no partial records are persisted on validation failure | T-015, T-013 | 2.0 | COMP-010 | modify |
| T-017 | Implement worker status instrumentation adapter (`services/worker_status.py`): call `celery_app.control.inspect(timeout=1.0).active()`; catch all exceptions; log at `WARNING`; return `WorkerStatusResult(available=False)` on any failure without re-raising | T-008 | 0.25 | COMP-011 | new |
| T-018 | Integrate `get_worker_status()` into `routes/dashboard*.py` route handlers; pass `WorkerStatusResult` to template context; update dashboard templates to conditionally render worker stats or degraded indicator based on `available` flag | T-017, T-013 | 0.5 | COMP-011 | modify |
| T-019 | Update `docker-compose.yml`: change `web` service command from `python app.py` to `bash start.sh`; add `redis` service (pinned image); add `celery-worker` service; add `celery-beat` service with explicit `replicas: 1` and inline comment warning against scaling; add `env_file` / `environment:` blocks using `${VAR}` syntax across all services; add `depends_on` chains | T-011, T-008, T-009, T-010 | 0.5 | COMP-012 | modify |
| T-020 | Add `security` stage to `stages:` list before `build` in `.gitlab-ci.yml`; add `dependency-scan` job (pip-audit, JSON artifact, `allow_failure: false`); include `Security/SAST.gitlab-ci.yml` and `Security/Secret-Detection.gitlab-ci.yml` templates; override both template jobs to run in `security` stage | T-007 | 0.5 | COMP-008 | modify |
| T-021 | Write unit tests for `utils/validation.py` covering all boundary cases: empty/whitespace/null inputs, range boundaries, max-length boundary, multi-error non-short-circuit behaviour of `validate_form`, and `format_error_response` structure | T-015 | 0.5 | COMP-010 | test |
| T-022 | Write unit tests for `startup_checks.py` covering: missing env var → `SystemExit(1)` with log naming the variable; DB unreachable → `SystemExit(1)`; Redis unreachable → `SystemExit(1)`; all checks pass → normal return | T-012 | 0.25 | COMP-002 | test |
| T-023 | Write unit tests for `services/worker_status.py` covering: healthy inspect → `available=True` with correct counts; `ConnectionError` → `available=False` no exception raised; timeout → `available=False` no exception raised; `None` response → `available=False` | T-017 | 0.25 | COMP-011 | test |
| T-024 | Write unit tests for `tests/config.py` credential resolver covering: env var set → value returned; env var absent + `is_localhost=True` → documented fallback; env var absent + `is_localhost=False` → `EnvironmentError` naming the variable; `CI=true` env var → `is_localhost=False` | T-014 | 0.25 | COMP-006 | test |
| T-025 | Write integration tests for form-handling route validation using Flask test client: missing required field → error response with field name, no DB record created; valid input → success response, record persisted; multiple field failures → all errors returned in single response | T-016 | 1.0 | COMP-010 | test |
| T-026 | Write integration tests for dashboard graceful degradation: mock `get_worker_status` returning `available=False`; assert dashboard route returns HTTP 200; assert core template renders without error; assert only instrumentation widget reflects degraded state | T-018 | 0.5 | COMP-011 | test |
| T-027 | Write integration tests for Celery task dispatch and retry: mock external service to fail twice then succeed; assert `TASK_RETRY` log entries at correct attempt numbers; assert task reaches `SUCCESS` state; assert `TASK_FAILED` log and `FAILURE` state when all retries are exhausted | T-010, T-019 | 0.75 | COMP-004 | test |

## Implementation Steps


### T-001: Verify pre-implementation test baseline and record results (config) —
- **Purpose**: Capture a clean test-suite pass/fail baseline before any code changes, so regressions introduced by later tasks can be detected unambiguously.
- **File(s)**: No file changes. Record output to a local scratch file (e.g. `baseline_test_results.txt`) that is **not** committed.
- **Dependencies**: None
- **Key notes**:
  - Run the full test suite exactly as CI would: activate the project virtualenv, export any required env vars (use localhost fallback values documented in `CONTRIBUTING.md` / `CLAUDE.md`), then execute the test runner.
  - Record: total tests, passed, failed, errored, skipped, and any pre-existing failures with their test IDs.
  - Pre-existing failures must be listed explicitly so they are not confused with regressions in subsequent tasks.
  - Do **not** fix any failing tests at this stage.
- **Acceptance criteria**: Establishes the baseline required before REQ-002, REQ-005, REQ-008 work begins; no REQ directly, but gates all subsequent tasks.
- **Verify**:
  ```bash
  pytest --tb=short -q 2>&1 | tee baseline_test_results.txt
  echo "Exit code: $?"
  ```

---

### T-002: Append binary documentation exclusion patterns to `.gitignore` (config) COMP-009
- **Purpose**: Prevent binary documentation files from ever being committed to the repository.
- **File(s)**: `.gitignore`
- **Dependencies**: T-001
- **Key notes**:
  - Append the following block at the end of `.gitignore`; do **not** alter existing entries:
    ```gitignore
    # Binary documentation files (REQ-006)
    *.pdf
    *.doc
    *.docx
    *.xls
    *.xlsx
    *.ppt
    *.pptx
    ```
  - Each pattern must be on its own line with the comment header above the block so the intent is clear in code review.
  - Confirm no existing `.gitignore` section already contains these patterns (search before appending to avoid duplicates).
- **Acceptance criteria**: REQ-006 — no binary doc files tracked; patterns present in `.gitignore`.
- **Verify**:
  ```bash
  grep -E '\*\.(pdf|doc|docx|xls|xlsx|ppt|pptx)' .gitignore
  # Each of the 7 patterns must appear in output
  git check-ignore -v some_test.pdf  # must print the matching rule
  ```

---

### T-003: Remove tracked binary documentation files from git tracking via `git rm --cached` (modify) COMP-009
- **Purpose**: Untrack any binary documentation files that are currently indexed in git without deleting them from the working directory.
- **File(s)**: `.gitignore` (already updated in T-002); git index only — no source file changes.
- **Dependencies**: T-002
- **Key notes**:
  - Run the command against all matching extensions. Use `--cached` so local copies are preserved:
    ```bash
    git rm --cached -r --ignore-unmatch -- '*.pdf' '*.doc' '*.docx' '*.xls' '*.xlsx' '*.ppt' '*.pptx'
    ```
  - If any files are removed from the index, commit **only** the removal with message: `chore: untrack binary documentation files (REQ-006)`.
  - If no files match, no commit is necessary — document this in the MR description.
  - Do **not** use `git rm` without `--cached`; working-directory files must not be deleted.
  - After the commit, run `git ls-files | grep -E '\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$'` to confirm zero tracked matches.
- **Acceptance criteria**: REQ-006 — no tracked binary doc files remain in the repository index.
- **Verify**:
  ```bash
  git ls-files | grep -E '\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$'
  # Must produce zero output
  ```

---

### T-004: Author `migrations/README.md` migration classification document (new) COMP-007
- **Purpose**: Provide a single authoritative registry that classifies every existing migration script so that DB state is unambiguous and future changes are governed by Alembic.
- **File(s)**: `migrations/README.md` (new file)
- **Dependencies**: T-001
- **Key notes**:
  - List **every** `.sql`, `.py`, or other migration file found under `migrations/` in a Markdown table with columns: `Filename | Status | Description | Applied-By | Notes`.
  - Valid `Status` values (exactly these strings): `APPLIED`, `SUPERSEDED`, `ENV-SPECIFIC`.
    - `APPLIED` — script has been run against production and must not be re-executed.
    - `SUPERSEDED` — replaced by a later migration; running it would cause errors or data loss.
    - `ENV-SPECIFIC` — only relevant to a specific environment (e.g. seeding local dev data); never run in production.
  - Include a **Policy** section stating: *"All future schema changes must be implemented as Alembic migrations. Ad-hoc SQL scripts are prohibited."*
  - Include a **How to run** section with the standard `flask db upgrade` / `alembic upgrade head` command.
  - Use a date column (`Classified-On`) set to today's date (2026-05-02) for every entry.
  - Do not invent statuses for unknown scripts — flag them `ENV-SPECIFIC` with a `Needs-review` note rather than guessing.
- **Acceptance criteria**: REQ-004 — `migrations/README.md` exists; every migration file is classified; policy statement present.
- **Verify**:
  ```bash
  # Confirm file exists and contains required table columns
  grep -E 'APPLIED|SUPERSEDED|ENV-SPECIFIC' migrations/README.md
  # List migration files vs README entries — counts must match
  ls migrations/*.sql migrations/*.py 2>/dev/null | wc -l
  grep -c '|' migrations/README.md
  ```

---

### T-005: Configure GitLab branch protection and MR approval rules (config) COMP-013
- **Purpose**: Enforce peer code review on `main` — no direct pushes, at least one non-author approval required, self-approval disabled.
- **File(s)**: GitLab project settings (UI / API — no repository file changes).
- **Dependencies**: T-001
- **Key notes**:
  - **Protected branch** (`Settings → Repository → Protected Branches`):
    - Branch: `main`
    - Allowed to merge: `Developers + Maintainers`
    - Allowed to push: `No one` (disables direct push for all roles including Maintainers)
    - Allowed to force-push: **disabled**
  - **Approval rules** (`Settings → Merge Requests → Approval Rules`):
    - Add rule: name `Peer Review`, approvals required: `1`, eligible approvers: `All Members` (or a dedicated reviewer group).
    - **Prevent approval by author**: **enabled**.
    - **Prevent approval by MR committers**: **enabled** (if available in the GitLab tier).
    - **Reset approvals on new commits**: **enabled**.
  - Document the configuration applied (GitLab tier, exact settings, date) in a comment on the implementation MR for audit purposes.
  - If GitLab API is used instead of the UI, use the `POST /projects/:id/protected_branches` and `POST /projects/:id/approval_rules` endpoints with appropriate tokens — store the token in a CI variable, never in the MR diff.
- **Acceptance criteria**: REQ-007 — MR to `main` requires ≥1 peer approval; self-approval prohibited; direct push to `main` blocked.
- **Verify**:
  ```bash
  # Via GitLab API (replace PROJECT_ID and TOKEN)
  curl --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    "https://<gitlab-host>/api/v4/projects/<PROJECT_ID>/protected_branches/main" \
    | python3 -m json.tool
  # Confirm: push_access_levels is empty or has access_level=0
  # Confirm: merge_access_levels contains Developer/Maintainer
  ```

---

### T-006: Update `CONTRIBUTING.md` and `CLAUDE.md` with env var credential setup (modify) COMP-006
- **Purpose**: Document the required environment variables, how to set them for local development, and the explicit localhost-only fallback values, so engineers never need to hard-code credentials.
- **File(s)**: `CONTRIBUTING.md`, `CLAUDE.md`
- **Dependencies**: T-001
- **Key notes**:
  - Add a **"Credential Setup"** section to both files. Content must include:
    1. A table listing every env var the application and test suite require (e.g. `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `REDIS_URL`, `SECRET_KEY` — enumerate all from the codebase).
    2. The documented localhost fallback value for each var (e.g. `DB_HOST=localhost`, `DB_PORT=3306`, `REDIS_URL=redis://localhost:6379/0`). These are the **only** values that may ever be committed to source.
    3. A `.env.example` snippet showing the export syntax.
    4. An explicit warning: *"Never commit actual credentials. In any non-localhost environment the test suite will raise `EnvironmentError` if a required variable is absent."*
  - `CONTRIBUTING.md` should additionally include a step-by-step *"Local environment setup"* numbered list.
  - `CLAUDE.md` should include a brief *"Environment variables"* paragraph cross-referencing `CONTRIBUTING.md`.
  - Do **not** create a committed `.env` file — only `.env.example` with placeholder/fallback values.
- **Acceptance criteria**: REQ-002, REQ-013 — credentials never in source; localhost fallback values documented.
- **Verify**:
  ```bash
  grep -n 'DB_PASSWORD\|SECRET_KEY\|REDIS_URL' CONTRIBUTING.md CLAUDE.md
  # Must show documented entries, not real credential values
  git diff HEAD -- CONTRIBUTING.md CLAUDE.md  # review for no real secrets
  ```

---

### T-007: Add `celery[redis]` and `gunicorn` to `requirements.txt`; remove standalone `APScheduler` (modify) COMP-003, COMP-001
- **Purpose**: Introduce the production task-queue and WSGI server dependencies; remove the scheduler dependency being replaced.
- **File(s)**: `requirements.txt`
- **Dependencies**: T-001
- **Key notes**:
  - Add exactly these lines (pinned to latest stable at time of implementation; use `pip index versions` to confirm):
    ```
    celery[redis]>=5.3,<6.0
    gunicorn>=21.2,<23.0
    ```
  - Search for `APScheduler` (case-insensitive) in `requirements.txt`. If found as a standalone entry (not a transitive comment), **remove** that line. If `APScheduler` appears in other files (e.g. `requirements-dev.txt`), leave those untouched — only `requirements.txt` is in scope here.
  - Do **not** pin to exact patch versions at this stage — range pinning allows security patches without MR churn.
  - After editing, run `pip install -r requirements.txt` in the virtualenv and confirm no dependency conflicts.
  - The `celery[redis]` extra installs `redis` (the Python client) — do not add `redis` separately.
- **Acceptance criteria**: REQ-001 (Celery available), REQ-003 (Gunicorn available); APScheduler removed from primary dependencies.
- **Verify**:
  ```bash
  pip install -r requirements.txt
  python -c "import celery, redis, gunicorn; print('OK')"
  grep -i apscheduler requirements.txt  # must produce no output
  ```

---

### T-008: Implement Celery application factory (`services/celery_app.py`) (new) COMP-003
- **Purpose**: Create the single, importable `celery_app` instance that all task definitions and the beat schedule will reference; bind it to the Flask application context.
- **File(s)**: `services/celery_app.py` (new file)
- **Dependencies**: T-007
- **Key notes**:
  - Read `REDIS_URL` from `os.environ` (no default — absence is caught by `startup_checks.py` in T-012).
  - Instantiate: `celery_app = Celery('app', broker=REDIS_URL, backend=REDIS_URL)`.
  - Apply configuration via `celery_app.config_from_object('celeryconfig')` — this references the file created in T-009.
  - Set serialiser settings explicitly to prevent security issues:
    ```python
    celery_app.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        result_expires=86400,  # 24 hours in seconds (REQ — TTL ≥24h)
        timezone='UTC',
        enable_utc=True,
    )
    ```
  - Implement a `init_celery(app)` function that binds the Flask app context so tasks can call `db.session` safely:
    ```python
    def init_celery(flask_app):
        class ContextTask(celery_app.Task):
            def __call__(self, *args, **kwargs):
                with flask_app.app_context():
                    return super().__call__(*args, **kwargs)
        celery_app.Task = ContextTask
        return celery_app
    ```
  - Export only `celery_app` and `init_celery` at module level.
  - Do **not** import any Flask route modules or db models here — keep this factory side-effect-free.
- **Acceptance criteria**: REQ-001 — Celery factory importable; REQ-009 — single instance guarantees no duplicate task registration.
- **Verify**:
  ```bash
  python -c "from services.celery_app import celery_app, init_celery; print(celery_app.conf.task_serializer)"
  # Must print: json
  python -c "from services.celery_app import celery_app; print(celery_app.backend)"
  # Must print the Redis backend URL
  ```

---

### T-009: Implement Celery Beat periodic schedule configuration (`celeryconfig.py`) (new) COMP-005
- **Purpose**: Define all periodic task triggers in one place, replacing APScheduler's schedule; enforce the single-beat-instance constraint via documentation and compose config.
- **File(s)**: `celeryconfig.py` (new file, project root)
- **Dependencies**: T-008
- **Key notes**:
  - Inspect `services/ctask_scheduler.py` and enumerate every `@scheduler.scheduled_job` trigger (interval, cron expression, etc.) before writing this file.
  - Translate each APScheduler trigger to a `beat_schedule` entry:
    ```python
    beat_schedule = {
        '<original-job-id>': {
            'task': 'services.ctask_scheduler.<function_name>',
            'schedule': crontab(...) | timedelta(seconds=...),
            'options': {'expires': <seconds>},  # prevent stale task pile-up
        },
        # ... one entry per APScheduler job
    }
    ```
  - Use `crontab` from `celery.schedules` for cron-style triggers; use `timedelta` or integer seconds for interval triggers.
  - Add a top-level comment block:
    ```python
    # WARNING: celery-beat MUST run as a single instance (replicas=1).
    # Running multiple beat instances causes duplicate task scheduling (violates REQ-001, REQ-009).
    # See docker-compose.yml celery-beat service for the deploy.replicas=1 constraint.
    ```
  - Set `beat_schedule_filename = '/tmp/celerybeat-schedule'` to avoid writing the schedule database to the project root.
  - Do **not** define task function bodies here — only schedule metadata.
- **Acceptance criteria**: REQ-001 — tasks isolated to worker process; REQ-009 — single beat instance documented and enforced; all existing APScheduler jobs migrated.
- **Verify**:
  ```bash
  python -c "import celeryconfig; print(list(celeryconfig.beat_schedule.keys()))"
  # Must print all migrated job names — count must match original APScheduler job count
  python -c "from celery.schedules import crontab; import celeryconfig"  # must not raise
  ```

---

### T-010: Refactor `services/ctask_scheduler.py`: APScheduler → Celery tasks (modify) COMP-004
- **Purpose**: Replace every APScheduler job definition with a Celery task decorated with retry policy and structured logging; ensure task return values contain no PII.
- **File(s)**: `services/ctask_scheduler.py`
- **Dependencies**: T-008, T-009
- **Key notes**:
  - **Imports**: Remove all APScheduler imports (`flask_apscheduler`, `APScheduler`, etc.); add `from services.celery_app import celery_app`.
  - **Decorator replacement**: For each `@scheduler.scheduled_job(...)` function, replace with:
    ```python
    @celery_app.task(
        bind=True,
        max_retries=3,
        default_retry_delay=30,
        autoretry_for=(Exception,),
        acks_late=True,
        reject_on_worker_lost=True,
    )
    def <function_name>(self, ...):
    ```
  - `acks_late=True` + `reject_on_worker_lost=True` together implement at-most-once semantics on worker crash (REQ-009).
  - **Structured log statements** — add exactly these four log calls using Python's `logging` module (not `print`):
    - On entry: `logger.info("TASK_STARTED task_id=%s task_name=%s", self.request.id, self.name)`
    - On success before return: `logger.info("TASK_COMPLETED task_id=%s task_name=%s", self.request.id, self.name)`
    - On retry (in `except` block before `self.retry()`): `logger.warning("TASK_RETRY task_id=%s attempt=%d/%d error=%s", self.request.id, self.request.retries + 1, self.max_retries, str(exc))`
    - On terminal failure (after `max_retries` exhausted): `logger.error("TASK_FAILED task_id=%s task_name=%s error=%s", self.request.id, self.name, str(exc))`
  - **Return values**: Each task must return a dict containing only non-PII metadata, e.g. `{"status": "ok", "records_processed": n}`. No user data, emails, names, or IDs that map to individuals.
  - **Scheduler initialisation**: Remove any `scheduler = APScheduler()` instantiation and `scheduler.init_app(app)` / `scheduler.start()` calls.
  - Retain all existing business logic inside each task body unchanged — only the decorator, logging, and return value are modified.
  - Add module-level `logger = logging.getLogger(__name__)`.
- **Acceptance criteria**: REQ-001 — tasks run in worker process; REQ-010 — retry ≤3× at ≥30s; REQ-013 — no PII in return values or logs.
- **Verify**:
  ```bash
  grep -n 'APScheduler\|flask_apscheduler\|scheduler\.scheduled_job' services/ctask_scheduler.py
  # Must produce zero output
  grep -n 'TASK_STARTED\|TASK_COMPLETED\|TASK_RETRY\|TASK_FAILED' services/ctask_scheduler.py
  # Must show at least one match per log level per task
  python -c "from services.ctask_scheduler import *"  # must not raise
  ```

### T-011: Implement production WSGI entry point script (`start.sh`) (new) COMP-001

- **Purpose**: Replace the `python app.py` dev-server invocation with a production-grade Gunicorn launcher. This is the sole entrypoint for the `web` service in all non-local environments.
- **File(s)**: `start.sh`
- **Dependencies**: T-007 (`gunicorn` must be present in `requirements.txt`)
- **Key notes**:
  - File must be executable (`chmod +x start.sh`); commit with execute bit (`git update-index --chmod=+x start.sh`).
  - Use exactly `-w 1` (single worker; horizontal scale handled at the container/replica level, not the process level).
  - Bind to `0.0.0.0:5000` to be reachable inside Docker networks.
  - Set `--timeout 120` to satisfy REQ-003.
  - Pass `--access-logfile -` so access logs go to stdout and are captured by the container runtime.
  - The WSGI callable is `app:app` (module `app`, Flask instance named `app`).
  - **Do not** include any `python app.py` fallback, dev-mode flag, or conditional branch. The script must have exactly one code path.
  - Add `set -euo pipefail` at the top so any pre-Gunicorn command failure causes an immediate non-zero exit.
  - Example final form:
    ```bash
    #!/usr/bin/env bash
    set -euo pipefail
    exec gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - app:app
    ```
  - Use `exec` so Gunicorn replaces the shell process and receives signals (SIGTERM) directly from the container runtime.
- **Acceptance criteria**: REQ-003 (production traffic via WSGI, `--timeout ≥120s`, dev server never used).
- **Verify**:
  ```bash
  bash -n start.sh                        # syntax check
  grep -E 'gunicorn.*-w 1.*--timeout 120' start.sh   # assert required flags present
  grep -v 'app\.run\|flask run' start.sh  # assert no dev-server path
  ```

---

### T-012: Implement application startup validator (`startup_checks.py`) (new) COMP-002

- **Purpose**: Provide an ordered, fail-fast validation gate that is called at application boot. Any missing required env var, unreachable database, or unreachable Redis broker causes `sys.exit(1)` with a `CRITICAL`-level log message that names the specific missing resource.
- **File(s)**: `startup_checks.py` (project root)
- **Dependencies**: T-008 (`services/celery_app.py` must exist so its broker URL constant is importable for Redis check)
- **Key notes**:
  - Import `logging`, `os`, `sys`. Use `logging.getLogger(__name__)` — do **not** use `print`.
  - Define a single public function `run_startup_checks(app)` that accepts the Flask app instance.
  - **Check 1 — Required env vars** (run first, before any network calls):
    - Define `REQUIRED_ENV_VARS` as a list of strings, e.g. `["DATABASE_URL", "REDIS_URL", "SECRET_KEY"]`. Adjust to match actual env var names used in the project.
    - Iterate the list; for each missing var log `CRITICAL: Required environment variable '{var}' is not set` and call `sys.exit(1)` immediately (fail on first missing var — do not accumulate).
  - **Check 2 — Database reachability**:
    - Inside `with app.app_context()`: execute `db.session.execute(text("SELECT 1"))`.
    - Wrap in `try/except Exception as e`; on failure log `CRITICAL: Database unreachable: {e}` and `sys.exit(1)`.
  - **Check 3 — Redis/broker reachability**:
    - Use `redis.Redis.from_url(os.environ["REDIS_URL"]).ping()` (import `redis`).
    - Wrap in `try/except Exception as e`; on failure log `CRITICAL: Redis broker unreachable: {e}` and `sys.exit(1)`.
  - Each check must be in strict order: env vars → DB → Redis. A failure in any check must prevent subsequent checks from running.
  - Do **not** log credential values; log only the variable name or a sanitised URL (strip password component if logging URLs).
- **Acceptance criteria**: REQ-011 (missing config/unreachable DB → immediate `sys.exit(1)` with named-var error log); verified by T-022.
- **Verify**:
  ```bash
  python -c "import startup_checks; print('import OK')"
  # Run unit tests added in T-022:
  pytest tests/test_startup_checks.py -v
  ```

---

### T-013: Modify `app.py`: remove APScheduler, bind Celery-Flask factory, call startup checks (modify) COMP-002, COMP-003

- **Purpose**: Surgically remove the APScheduler bootstrapping and `app.run()` dev-server call; wire in the Celery-Flask factory binding; and insert the startup validator call in the correct position in the application lifecycle.
- **File(s)**: `app.py`
- **Dependencies**: T-008 (`services/celery_app.py`), T-012 (`startup_checks.py`)
- **Key notes**:
  - **Remove**:
    - Any `from apscheduler...` imports.
    - Scheduler instantiation (`scheduler = BackgroundScheduler(...)` or similar).
    - `scheduler.start()` / `scheduler.shutdown()` calls and associated `atexit` hooks.
    - `app.run(...)` at the bottom of the file (Gunicorn is now the runner).
  - **Add — Celery binding**: After the Flask `app` object is created and configured, import `celery_app` from `services.celery_app` and call the factory's Flask-context binding method (e.g. `celery_app.conf.update(app.config)` plus `TaskBase.__call__` override, following the pattern established in T-008). The `celery_app` object should remain importable from `app.py` for worker process startup.
  - **Add — startup checks**: Call `run_startup_checks(app)` **after** `app.config` is fully loaded and **before** route/blueprint registration. This ensures checks fail before any route handler can accept traffic.
  - **Order of operations in `app.py`**:
    1. Create Flask `app` and load config.
    2. Call `run_startup_checks(app)`.
    3. Initialise extensions (`db`, etc.).
    4. Register blueprints / routes.
    5. _(no `app.run()`)_
  - Ensure the module-level `app` name remains `app` so `app:app` in `start.sh` resolves correctly.
  - If APScheduler was listed as an installed extension on `app` (e.g. `scheduler.init_app(app)`), remove that line.
- **Acceptance criteria**: REQ-001 (background tasks isolated from web process); REQ-003 (no dev server); REQ-011 (startup checks called).
- **Verify**:
  ```bash
  python -c "from app import app; print('Flask app loads OK')"
  grep -v 'app\.run\|apscheduler\|BackgroundScheduler' app.py
  pytest tests/ -x -q    # full suite must remain green
  ```

---

### T-014: Implement test credential resolver in `tests/config.py` (modify) COMP-006

- **Purpose**: Eliminate all hard-coded credential literals from the test configuration. Replace them with `os.environ.get()` resolution, implement `is_localhost` detection, provide documented fallback values only when running locally, and raise a descriptive `EnvironmentError` in shared/CI environments where a required variable is absent.
- **File(s)**: `tests/config.py`
- **Dependencies**: T-006 (`CONTRIBUTING.md` / `CLAUDE.md` must document which env vars are required and their localhost fallback values, so this file can reference the canonical list)
- **Key notes**:
  - **`is_localhost` detection logic** (must default to `False` in ambiguous cases):
    ```python
    import os, socket
    def _is_localhost() -> bool:
        if os.environ.get("CI"):          return False
        if os.environ.get("GITLAB_CI"):   return False
        hostname = socket.gethostname()
        return hostname in ("localhost", "127.0.0.1") or hostname.endswith(".local")
    IS_LOCALHOST = _is_localhost()
    ```
  - **Credential resolver function**:
    ```python
    def get_credential(var_name: str, localhost_fallback: str) -> str:
        value = os.environ.get(var_name)
        if value is not None:
            return value
        if IS_LOCALHOST:
            return localhost_fallback
        raise EnvironmentError(
            f"Required test credential '{var_name}' is not set. "
            f"Set it as an environment variable before running tests in non-localhost environments."
        )
    ```
  - Replace **every** existing credential literal (database URLs, passwords, API keys, tokens) in `tests/config.py` with a `get_credential(VAR_NAME, fallback)` call. The fallback values must match those documented in `CONTRIBUTING.md` (T-006).
  - Do **not** leave any string literals that contain passwords, tokens, or connection strings outside of `get_credential` calls.
  - `EnvironmentError` message must name the specific variable (verified by T-024).
  - Add a module-level comment block listing all required env vars for quick reference.
- **Acceptance criteria**: REQ-002 (credentials from env vars; localhost fallback only; hard fail in shared envs); REQ-013 (credentials never in source); verified by T-024.
- **Verify**:
  ```bash
  # Assert no literals that look like passwords remain:
  grep -rE '(password|passwd|secret|token)\s*=\s*["\'][^$\{]' tests/config.py && echo "FAIL: literals found" || echo "OK"
  pytest tests/test_config.py -v
  ```

---

### T-015: Create `utils/` package and implement `utils/validation.py` (new) COMP-010

- **Purpose**: Provide a reusable, pure-function validation library used by all form-handling routes. Centralises validation logic so route handlers stay thin and errors are uniform.
- **File(s)**: `utils/__init__.py`, `utils/validation.py`
- **Dependencies**: T-001 (baseline confirmed; no other task dependency)
- **Key notes**:
  - `utils/__init__.py`: empty file (package marker only).
  - `utils/validation.py` must define:
    - **`ValidationError` (TypedDict)**:
      ```python
      from typing import TypedDict
      class ValidationError(TypedDict):
          field: str
          message: str
      ```
    - **`validate_required(value, field_name) -> ValidationError | None`**: Returns error if `value` is `None`, empty string, or whitespace-only string (`str.strip() == ""`).
    - **`validate_not_null(value, field_name) -> ValidationError | None`**: Returns error if `value` is `None` (does **not** reject empty string — distinct from `validate_required`).
    - **`validate_range(value, field_name, min_val, max_val) -> ValidationError | None`**: Returns error if numeric `value` is outside `[min_val, max_val]` (inclusive). Handles non-numeric input as a validation error, not an exception.
    - **`validate_max_length(value, field_name, max_length) -> ValidationError | None`**: Returns error if `len(str(value)) > max_length`.
    - **`validate_form(rules: list[tuple[Callable, ...]]) -> list[ValidationError]`**: Accepts a list of `(validator_fn, *args)` tuples; calls each; collects **all** errors (does not short-circuit); returns the full list.
    - **`format_error_response(errors: list[ValidationError]) -> dict`**: Returns `{"errors": errors}`.
  - All functions must be **pure** (no side effects, no imports of Flask/DB/Celery).
  - `validate_form` must be non-short-circuiting: even if the first rule fails, all subsequent rules are evaluated and all errors collected.
  - Error messages must be human-readable and include the field name, e.g. `"'email' is required"`, `"'age' must be between 0 and 120"`.
- **Acceptance criteria**: REQ-008 (all form input validated; failure returns field-specific error); verified by T-021.
- **Verify**:
  ```bash
  python -c "from utils.validation import validate_form, format_error_response, ValidationError; print('import OK')"
  pytest tests/test_validation.py -v
  ```

---

### T-016: Audit and integrate `validate_form()` across all form-handling POST route handlers (modify) COMP-010

- **Purpose**: Ensure every form submission is validated before any database write occurs. Validation failures return field-specific error messages without persisting partial records.
- **File(s)**: `routes/*.py` (all files containing `POST` handlers that read form data), and their corresponding Jinja2 templates in `templates/`
- **Dependencies**: T-015 (`utils/validation.py`), T-013 (`app.py` must be stable before routes are exercised)
- **Key notes**:
  - **Audit step**: Run `grep -rn "request.form\|request.json" routes/` to enumerate every handler that processes user-submitted data. Document each one before editing.
  - **Integration pattern for HTML routes**:
    ```python
    from utils.validation import validate_form, validate_required, validate_max_length, format_error_response

    @bp.route("/resource", methods=["POST"])
    def create_resource():
        errors = validate_form([
            (validate_required, request.form.get("field_a"), "field_a"),
            (validate_max_length, request.form.get("field_b"), "field_b", 255),
        ])
        if errors:
            return render_template("resource_form.html", errors=errors, form=request.form), 200
        # db.session operations only reached here
        ...
    ```
  - **Integration pattern for JSON routes**: Return `jsonify(format_error_response(errors)), 422` on validation failure.
  - **No partial DB writes**: Ensure all `db.session.add()` / `db.session.commit()` calls are inside the `if not errors:` branch.
  - **Template updates**: For every affected HTML template, add a Jinja2 block that renders field-level errors. Recommended pattern:
    ```html
    {% for error in errors if error.field == 'field_a' %}
      <span class="field-error">{{ error.message }}</span>
    {% endfor %}
    ```
    Also re-populate form field `value` attributes from `form` context variable so the user does not lose their input on validation failure.
  - Preserve all existing success-path behaviour (redirect codes, redirect targets, response shapes) unchanged.
  - If a route already performs manual validation, replace it with `validate_form()` calls so logic is not duplicated.
- **Acceptance criteria**: REQ-008 (all form input validated; failure returns field-specific error message; no partial records persisted); verified by T-025.
- **Verify**:
  ```bash
  # Assert no db.session call can be reached without prior validation in modified routes:
  pytest tests/test_form_routes.py -v
  # Spot-check: submit empty form to each modified route via test client and assert no DB record is created.
  ```

---

### T-017: Implement worker status instrumentation adapter (`services/worker_status.py`) (new) COMP-011

- **Purpose**: Provide a safe, non-raising wrapper around Celery's inspect API. The adapter isolates any Celery connectivity failure from the web tier, returning a structured result object regardless of outcome.
- **File(s)**: `services/worker_status.py`
- **Dependencies**: T-008 (`services/celery_app.py` must export `celery_app`)
- **Key notes**:
  - Define `WorkerStatusResult` as a `TypedDict`:
    ```python
    from typing import TypedDict
    class WorkerStatusResult(TypedDict):
        available: bool
        worker_count: int
        active_tasks: int
        error: str | None
    ```
  - Implement `get_worker_status() -> WorkerStatusResult`:
    ```python
    import logging
    from services.celery_app import celery_app

    logger = logging.getLogger(__name__)

    def get_worker_status() -> WorkerStatusResult:
        try:
            inspect = celery_app.control.inspect(timeout=1.0)
            active = inspect.active()
            if active is None:
                raise RuntimeError("inspect.active() returned None — no workers reachable")
            worker_count = len(active)
            active_tasks = sum(len(tasks) for tasks in active.values())
            return WorkerStatusResult(available=True, worker_count=worker_count, active_tasks=active_tasks, error=None)
        except Exception as e:
            logger.warning("Worker status check failed: %s", e)
            return WorkerStatusResult(available=False, worker_count=0, active_tasks=0, error=str(e))
    ```
  - `timeout=1.0` is mandatory — the inspect call must not block the web request for more than 1 second.
  - The function must **never raise** regardless of the exception type (`ConnectionError`, `TimeoutError`, generic `Exception`). All exceptions are caught and converted to `available=False`.
  - Log at `WARNING` level — do not log at `ERROR` (worker unavailability is degraded, not a crash).
  - Do not log exception stack traces (use `logger.warning(..., e)` not `logger.exception`).
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200); verified by T-023.
- **Verify**:
  ```bash
  python -c "from services.worker_status import get_worker_status, WorkerStatusResult; print('import OK')"
  pytest tests/test_worker_status.py -v
  ```

---

### T-018: Integrate `get_worker_status()` into dashboard routes and templates (modify) COMP-011

- **Purpose**: Surface real-time Celery worker stats on the dashboard when available, and render a graceful degraded indicator when the worker status check fails — without breaking the page in either case.
- **File(s)**: `routes/dashboard*.py` (whichever file(s) contain the dashboard route handlers), `templates/dashboard*.html` (or equivalent template name)
- **Dependencies**: T-017 (`services/worker_status.py`), T-013 (`app.py` stable)
- **Key notes**:
  - In each dashboard route handler, import and call `get_worker_status()`:
    ```python
    from services.worker_status import get_worker_status

    @bp.route("/dashboard")
    def dashboard():
        worker_status = get_worker_status()
        return render_template("dashboard.html", worker_status=worker_status, ...)
    ```
  - `get_worker_status()` must be called **after** all other context is assembled, so a slow inspect does not delay critical page data.
  - Pass `worker_status` as a named variable in the template context; do not spread its fields as individual variables (keeps template binding explicit).
  - **Template changes**:
    - The worker stats widget must be wrapped in a conditional:
      ```html
      {% if worker_status.available %}
        <div class="worker-stats">
          Workers: {{ worker_status.worker_count }} |
          Active tasks: {{ worker_status.active_tasks }}
        </div>
      {% else %}
        <div class="worker-stats worker-stats--degraded">
          Worker instrumentation unavailable
        </div>
      {% endif %}
      ```
    - All other dashboard sections must render unconditionally — the `worker_status.available` flag must only gate the worker stats widget.
  - The route must return HTTP 200 regardless of `worker_status.available` value.
  - Do not add any `try/except` in the route handler — `get_worker_status()` already guarantees no exception propagation.
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200); verified by T-026.
- **Verify**:
  ```bash
  pytest tests/test_dashboard_degraded.py -v
  # Also manually: with no Celery worker running, load /dashboard — page must render HTTP 200 with degraded indicator.
  ```

---

### T-019: Update `docker-compose.yml` to add Redis, Celery worker, and Celery Beat services (modify) COMP-012

- **Purpose**: Extend the container orchestration definition to support the full production topology: Flask/Gunicorn web, Redis broker/backend, Celery worker, and Celery Beat scheduler — with correct dependency chains and environment variable injection.
- **File(s)**: `docker-compose.yml`
- **Dependencies**: T-011 (`start.sh`), T-008 (`services/celery_app.py`), T-009 (`celeryconfig.py`), T-010 (`services/ctask_scheduler.py`)
- **Key notes**:
  - **`web` service**: Change `command` from `python app.py` to `bash start.sh`. Add `depends_on: [redis]`.
  - **`redis` service** (new):
    ```yaml
    redis:
      image: redis:7.2-alpine   # pin to a specific minor version
      restart: unless-stopped
      ports:
        - "6379:6379"           # expose only for local dev; remove in production override
    ```
  - **`celery-worker` service** (new):
    ```yaml
    celery-worker:
      build: .
      command: celery -A services.celery_app worker --loglevel=info
      env_file: .env
      environment:
        - REDIS_URL=${REDIS_URL}
        - DATABASE_URL=${DATABASE_URL}
      depends_on:
        - redis
        - web        # ensures app context / migrations are ready
      restart: unless-stopped
    ```
  - **`celery-beat` service** (new):
    ```yaml
    celery-beat:
      build: .
      command: celery -A services.celery_app beat --loglevel=info --scheduler celery.beat.PersistentScheduler
      env_file: .env
      environment:
        - REDIS_URL=${REDIS_URL}
        - DATABASE_URL=${DATABASE_URL}
      depends_on:
        - redis
      restart: unless-stopped
      deploy:
        replicas: 1   # WARNING: do NOT scale above 1 — multiple beat instances cause duplicate task scheduling (REQ-009)
    ```
  - **`env_file` / `environment`**: All services that need credentials must use `env_file: .env` **and** explicit `environment:` entries using `${VAR}` syntax. Never hard-code values.
  - Ensure `.env` is in `.gitignore` (handled by T-002/T-003 scope indirectly; verify here).
  - Add the `replicas: 1` inline comment verbatim as shown above — it is a deliberate documentation constraint, not just a value.
  - Validate the final file with `docker-compose config` (no errors).
- **Acceptance criteria**: REQ-001 (tasks isolated from web; no duplicate execution on scale-out); REQ-003 (web service uses Gunicorn); REQ-009 (at-most-once via single Beat replica); REQ-013 (no credentials in source).
- **Verify**:
  ```bash
  docker-compose config       # validates YAML and variable substitution
  docker-compose up --dry-run 2>&1 | grep -E "redis|celery-worker|celery-beat|web"
  grep -v '\${' docker-compose.yml | grep -E '(password|secret|token)' && echo "FAIL: literal creds" || echo "OK"
  ```

---

### T-020: Add `security` stage to `.gitlab-ci.yml` with pip-audit, SAST, and Secret Detection (modify) COMP-008

- **Purpose**: Introduce a blocking `security` CI stage that runs before `build`, comprising three jobs: a CVE dependency scan (pip-audit), GitLab SAST, and GitLab Secret Detection. All three must pass for the pipeline to proceed.
- **File(s)**: `.gitlab-ci.yml`
- **Dependencies**: T-007 (`requirements.txt` stable so pip-audit scans the correct dependency set)
- **Key notes**:
  - **Stage ordering**: Insert `security` as the first entry in the `stages:` list, before `build` (and before `test` if present):
    ```yaml
    stages:
      - security
      - build
      - test
      - deploy
    ```
  - **Include GitLab security templates** (add to top-level `include:` block):
    ```yaml
    include:
      - template: Security/SAST.gitlab-ci.yml
      - template: Security/Secret-Detection.gitlab-ci.yml
    ```
  - **`dependency-scan` job** (pip-audit):
    ```yaml
    dependency-scan:
      stage: security
      image: python:3.11-slim
      before_script:
        - pip install pip-audit
      script:
        - pip-audit -r requirements.txt --format json --output pip-audit-report.json
      artifacts:
        paths:
          - pip-audit-report.json
        when: always          # preserve report even on failure
        expire_in: 30 days
      allow_failure: false    # blocks pipeline on any CVE finding
    ```
  - **Override SAST and Secret Detection template jobs** to run in the `security` stage (GitLab templates default to their own stage names which may differ):
    ```yaml
    sast:
      stage: security

    secret_detection:
      stage: security
    ```
  - `allow_failure: false` on `dependency-scan` is explicit — do not omit it. SAST and Secret Detection template jobs default to `allow_failure: false`; verify this is not overridden.
  - Do not add credentials, tokens, or any secrets to `.gitlab-ci.yml` — all env vars for job execution must come from GitLab CI/CD Variables (project settings), not inline values.
  - Validate YAML syntax before committing.
- **Acceptance criteria**: REQ-005 (CI `security` stage: CVE scan with artifact + SAST + git-history secret scan; blocks build); REQ-013 (credentials never in CI config).
- **Verify**:
  ```bash
  # Local YAML lint:
  python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo "YAML OK"
  # Structural assertions:
  grep -n 'stage: security' .gitlab-ci.yml
  grep -n 'allow_failure: false' .gitlab-ci.yml
  grep -n 'pip-audit-report.json' .gitlab-ci.yml
  grep -n 'Security/SAST' .gitlab-ci.yml
  grep -n 'Security/Secret-Detection' .gitlab-ci.yml
  ```

### T-021: Write unit tests for `utils/validation.py` (new) COMP-010

- **Purpose**: Verify all pure validation functions handle boundary conditions correctly, including multi-error non-short-circuit behaviour and correct `format_error_response` structure.
- **File(s)**: `tests/unit/test_validation.py`
- **Dependencies**: T-015 (utils/validation.py must exist)
- **Key notes**:
  - Import `validate_required`, `validate_not_null`, `validate_range`, `validate_max_length`, `validate_form`, `format_error_response`, and `ValidationError` from `utils.validation`.
  - `validate_required`: test empty string `""`, whitespace-only `"   "`, `None`, and a valid non-empty string. Expect `ValidationError` with correct `field` and `message` for failures; `None` (or no error) for success.
  - `validate_not_null`: test `None` input → error; `0`, `False`, `""` (non-None falsy) → no error (not null); valid object → no error.
  - `validate_range`: test value equal to `min` boundary (inclusive pass), value equal to `max` boundary (inclusive pass), value one below `min` → error, value one above `max` → error, value strictly inside range → pass.
  - `validate_max_length`: test string of exactly `max_length` chars → pass; string of `max_length + 1` → error; empty string → pass; `None` handling per implementation contract.
  - `validate_form`: pass a dict of field→value pairs where **multiple** fields are invalid simultaneously. Assert that **all** errors are returned in one call (no short-circuiting after first failure). Also assert that a fully valid input dict returns an empty errors list.
  - `format_error_response`: assert returned dict contains key `"errors"` whose value is a list; each element is a dict with keys `"field"` and `"message"`; assert no extra top-level keys are present.
  - No mocking required; all functions are pure.
  - Use `pytest.mark.parametrize` for boundary cases to keep the test file DRY.
- **Acceptance criteria**: REQ-008 (form input validation returns field-specific errors)
- **Verify**: `pytest tests/unit/test_validation.py -v`

---

### T-022: Write unit tests for `startup_checks.py` (new) COMP-002

- **Purpose**: Confirm that `run_startup_checks()` exits with code 1 and logs the right CRITICAL message for each failure scenario, and returns normally when all checks pass.
- **File(s)**: `tests/unit/test_startup_checks.py`
- **Dependencies**: T-012 (startup_checks.py must exist)
- **Key notes**:
  - Import `run_startup_checks` from `startup_checks`; use `pytest.raises(SystemExit)` to assert `sys.exit(1)` is called.
  - **Missing env var test**: Use `monkeypatch.delenv` to remove a required env var. Assert `SystemExit` with code `1`. Use `caplog` (level `CRITICAL`) to assert the log message names the specific missing variable (e.g., `"DATABASE_URL"` appears in the log output). Repeat for at least two distinct required variables to confirm variable naming is not hardcoded.
  - **DB unreachable test**: Patch the DB connectivity call (e.g., `sqlalchemy.engine.Engine.connect` or equivalent) to raise `OperationalError`. Assert `SystemExit(1)` and a CRITICAL log entry mentioning database reachability.
  - **Redis unreachable test**: Patch the Redis ping call (e.g., `redis.Redis.ping`) to raise `ConnectionError`. Assert `SystemExit(1)` and a CRITICAL log entry mentioning Redis/broker.
  - **All checks pass test**: Patch env vars to supply all required values; patch DB and Redis calls to return successfully. Assert `run_startup_checks()` returns without raising and no CRITICAL log is emitted.
  - Use a minimal Flask app fixture (`app.app_context()`) if `run_startup_checks` requires an app context.
  - Never rely on real network or DB connections; all external calls must be patched via `unittest.mock.patch` or `pytest-mock`.
- **Acceptance criteria**: REQ-011 (missing config/unreachable DB → `sys.exit(1)` with named-var error log)
- **Verify**: `pytest tests/unit/test_startup_checks.py -v`

---

### T-023: Write unit tests for `services/worker_status.py` (new) COMP-011

- **Purpose**: Confirm that `get_worker_status()` correctly maps Celery inspect output to `WorkerStatusResult` and **never raises** on any failure path.
- **File(s)**: `tests/unit/test_worker_status.py`
- **Dependencies**: T-017 (services/worker_status.py must exist)
- **Key notes**:
  - Import `get_worker_status` from `services.worker_status` and `WorkerStatusResult` for type assertions.
  - **Healthy inspect test**: Patch `celery_app.control.inspect().active()` to return a dict with two worker keys each containing a list of active task dicts (e.g., `{"worker1@host": [{"id": "abc"}, {"id": "def"}], "worker2@host": [{"id": "ghi"}]}`). Assert `result.available == True`, `result.worker_count == 2`, `result.active_tasks == 3`, `result.error is None`.
  - **`ConnectionError` test**: Patch `inspect().active()` to raise `ConnectionError`. Assert the function returns without raising; assert `result.available == False`. Also assert a WARNING-level log entry is emitted (use `caplog`).
  - **Timeout test**: Patch `inspect().active()` to raise `TimeoutError` (or the Celery equivalent). Same assertions as ConnectionError case.
  - **`None` response test**: Patch `inspect().active()` to return `None` (broker offline, no workers registered). Assert `result.available == False`, `result.worker_count == 0`, `result.active_tasks == 0`.
  - In all failure cases, assert no exception propagates out of `get_worker_status()` (wrap call in `try/except Exception` inside the test if needed, but prefer asserting no raise via normal return).
  - Patch at the `services.worker_status.celery_app` import reference, not the global Celery object, to avoid test pollution.
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200)
- **Verify**: `pytest tests/unit/test_worker_status.py -v`

---

### T-024: Write unit tests for `tests/config.py` credential resolver (new) COMP-006

- **Purpose**: Confirm that the credential resolver returns values from env vars, uses documented fallbacks only on localhost, and raises `EnvironmentError` naming the missing variable in all other environments.
- **File(s)**: `tests/unit/test_tests_config.py`
- **Dependencies**: T-014 (tests/config.py must be refactored)
- **Key notes**:
  - Import the resolver function(s) and `is_localhost` detection logic from `tests.config`. If `is_localhost` is a module-level computed bool, import it directly and override via `monkeypatch`.
  - **Env var set → value returned**: Use `monkeypatch.setenv("MY_CREDENTIAL", "secret")`. Call resolver for that credential. Assert returned value equals `"secret"`. Applies regardless of `is_localhost`.
  - **Env var absent + `is_localhost=True` → fallback**: Use `monkeypatch.delenv` to remove the variable; force `is_localhost` to `True` (patch module attribute). Assert the documented fallback value (e.g., `"localhost"`, `"5432"`) is returned without raising.
  - **Env var absent + `is_localhost=False` → `EnvironmentError`**: Remove the variable; force `is_localhost` to `False`. Assert `EnvironmentError` is raised and the exception message contains the exact variable name (e.g., `"DB_PASSWORD"` in `str(exc.value)`).
  - **`CI=true` → `is_localhost=False`**: Use `monkeypatch.setenv("CI", "true")`. Re-import or re-evaluate `is_localhost`. Assert it resolves to `False`. Then remove a required credential and assert `EnvironmentError` is raised (confirming CI hard-fail path).
  - Parameterise across at least 3 different credential variable names to guard against any variable being hardcoded as a special case.
  - These tests must themselves pass in CI without any real credentials; use `monkeypatch` exclusively.
- **Acceptance criteria**: REQ-002 (test credentials from env vars; localhost fallback only; hard fail in shared envs), REQ-013 (credentials never in source or CI logs)
- **Verify**: `pytest tests/unit/test_tests_config.py -v`

---

### T-025: Write integration tests for form-handling route validation (new) COMP-010

- **Purpose**: Confirm via Flask test client that validated POST routes reject invalid input with field-specific errors and no DB writes, and accept valid input with correct persistence.
- **File(s)**: `tests/integration/test_form_validation.py`
- **Dependencies**: T-016 (route handlers must integrate `validate_form()`), T-014 (test credential resolver)
- **Key notes**:
  - Use a `pytest` fixture that creates a Flask test client with `TESTING=True` and an in-memory or test-isolated DB session (patch `db.session` or use a rollback fixture to prevent state leakage between tests).
  - Identify at least **two** distinct form-handling POST routes (e.g., `/incidents/create`, `/handovers/create`) to test. Cover at least one HTML-response route and one JSON-response route if both exist.
  - **Missing required field → error, no DB write**:
    - POST with one required field omitted.
    - **HTML route**: assert HTTP 200; assert response body contains the field name and an error message string; assert no new DB record exists (query count before/after).
    - **JSON route**: assert HTTP 422; assert response JSON contains `{"errors": [{...}]}` with `"field"` matching the omitted field name.
  - **Valid input → success, record persisted**:
    - POST with all required fields populated with valid values.
    - Assert HTTP 302 (redirect) or HTTP 200 as appropriate for the route.
    - Assert exactly one new record exists in the relevant table.
  - **Multiple field failures → all errors in single response**:
    - POST with at least two required fields omitted or invalid simultaneously.
    - Assert all field errors are present in the response (not just the first); assert count of errors in response matches number of invalid fields.
  - Patch any external service calls (e.g., SSO lookups, email dispatch) that may be triggered within route handlers to avoid real I/O.
  - Do **not** commit DB writes during tests; use `db.session.rollback()` in teardown or use a transaction-scoped fixture.
- **Acceptance criteria**: REQ-008 (form input validated; failure returns field-specific error; no partial DB writes)
- **Verify**: `pytest tests/integration/test_form_validation.py -v`

---

### T-026: Write integration tests for dashboard graceful degradation (new) COMP-011

- **Purpose**: Confirm that the dashboard route returns HTTP 200 with full core rendering when `get_worker_status` reports unavailable, and that only the instrumentation widget reflects the degraded state.
- **File(s)**: `tests/integration/test_dashboard_degradation.py`
- **Dependencies**: T-018 (dashboard route integrates `get_worker_status`), T-014 (test credential resolver)
- **Key notes**:
  - Use a Flask test client fixture with `TESTING=True`; patch `services.worker_status.get_worker_status` (at the import site used in the dashboard route module) using `unittest.mock.patch` or `pytest-mock`.
  - **Degraded state test**:
    - Mock `get_worker_status` to return `WorkerStatusResult(available=False, worker_count=0, active_tasks=0, error="Connection refused")`.
    - GET the dashboard route (e.g., `/dashboard` or `/`).
    - Assert HTTP status code is `200`.
    - Assert the response body contains the expected core dashboard HTML landmarks (e.g., a known static heading or nav element that is always present).
    - Assert the response body contains the degraded/unavailable indicator for the worker stats widget (e.g., a specific CSS class, text string like `"Workers unavailable"`, or data-attribute defined in the template).
    - Assert the response body does **not** contain worker count or active task numbers (to confirm stats are hidden/replaced, not just appended).
  - **Available state test** (positive control):
    - Mock `get_worker_status` to return `WorkerStatusResult(available=True, worker_count=2, active_tasks=5, error=None)`.
    - Assert HTTP 200.
    - Assert response body contains `"2"` workers and `"5"` active tasks rendered within the instrumentation widget.
  - Patch any DB queries within the dashboard route that require real data (use `MagicMock` or fixture DB state as appropriate).
  - Do not test template rendering independently; test through the full route stack to catch any context-passing bugs.
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200)
- **Verify**: `pytest tests/integration/test_dashboard_degradation.py -v`

---

### T-027: Write integration tests for Celery task dispatch and retry (new) COMP-004

- **Purpose**: Confirm that Celery tasks emit correct structured log entries at each retry attempt, reach `SUCCESS` on eventual success, and reach `FAILURE` with a `TASK_FAILED` log when all retries are exhausted.
- **File(s)**: `tests/integration/test_celery_tasks.py`
- **Dependencies**: T-010 (tasks use `@celery_app.task` with retry policy), T-019 (docker-compose defines worker/beat services)
- **Key notes**:
  - Use Celery's `CELERY_TASK_ALWAYS_EAGER = True` and `CELERY_TASK_EAGER_PROPAGATES = False` in the test configuration so tasks execute synchronously in-process without a real broker; this avoids requiring a running Redis in unit/integration CI.
  - Alternatively, if the project uses `pytest-celery` or a Redis test fixture, document that requirement clearly in a `pytest.ini` or fixture docstring.
  - **Retry then succeed test**:
    - Patch the external service called by a representative task (e.g., the first task defined in `ctask_scheduler.py`) using `side_effect=[Exception("fail"), Exception("fail"), "success_value"]` (fail twice, succeed on third attempt).
    - Call the task directly via `.apply()` or `.delay()` depending on eager mode.
    - Use `caplog` at `INFO` level. Assert `TASK_RETRY` log entries appear exactly twice, each containing the correct attempt number (1 and 2).
    - Assert `TASK_STARTED` log appears once at the beginning.
    - Assert `TASK_COMPLETED` log appears once after the third attempt.
    - Assert the final task state is `SUCCESS`.
  - **All retries exhausted → FAILURE test**:
    - Patch the external service to always raise (e.g., `side_effect=Exception("permanent failure")`), ensuring it fails more times than `max_retries=3`.
    - Assert `TASK_RETRY` log appears exactly 3 times.
    - Assert `TASK_FAILED` log appears once after the final retry is exhausted.
    - Assert the task result state is `FAILURE`.
    - Assert no exception propagates out of the `.apply()` call (task failure must be terminal, not unhandled).
  - **Log content assertions**: Each `TASK_RETRY` log entry must include the attempt number; each `TASK_FAILED` entry must include the exception class or message. Assert these substrings are present in the captured log records.
  - **No PII in return values**: Inspect the task result `.result` dict on SUCCESS state; assert it contains only status metadata keys (e.g., `"status"`, `"task_id"`, `"duration_ms"`) and contains no fields named after PII attributes (e.g., `"email"`, `"username"`, `"token"`). Enumerate the known return keys from T-010's implementation.
  - If eager mode is used, add a module-level comment explaining why no broker is needed and how to run against a real broker for smoke testing.
- **Acceptance criteria**: REQ-001 (tasks isolated from web process), REQ-009 (at-most-once execution), REQ-010 (transient failures retry ≤3× at ≥30s intervals; terminal state observable)
- **Verify**: `pytest tests/integration/test_celery_tasks.py -v`

## Execution Waves

| Wave | Tasks | Dependencies Satisfied | Verify Command |
|------|-------|----------------------|----------------|
| **0** | T-001 | — | `pytest --tb=short > baseline.txt; echo "Exit: $?"` |
| **1** | T-002, T-004, T-005, T-006, T-007, T-015 | T-001 | `git check-ignore -v *.pdf; pip install -r requirements.txt --dry-run; python -c "import utils.validation"` |
| **2** | T-003, T-008, T-011, T-014, T-020, T-021 | T-001–T-007, T-015 | `git ls-files --error-unmatch "*.pdf" 2>&1 \| grep "error"; python -c "from services.celery_app import celery_app"; bash -n start.sh; pytest tests/test_validation.py` |
| **3** | T-009, T-012, T-017, T-024 | T-002–T-008, T-011, T-014, T-020, T-021 | `python -c "import celeryconfig"; python -c "from startup_checks import run_startup_checks"; python -c "from services.worker_status import get_worker_status"; pytest tests/test_config.py tests/test_startup_checks.py tests/test_worker_status.py` |
| **4** | T-010, T-013, T-022, T-023 | All Wave 0–3 tasks | `grep -R "scheduler.scheduled_job" services/ctask_scheduler.py; [ $? -ne 0 ] && echo "APScheduler removed"; python -c "from app import app"; pytest tests/test_startup_checks.py tests/test_worker_status.py` |
| **5** | T-016, T-018, T-019 | All Wave 0–4 tasks | `docker compose config --quiet; grep "validate_form" routes/*.py \| wc -l; grep "worker_status" routes/dashboard*.py` |
| **6** | T-025, T-026, T-027 | All Wave 0–5 tasks | `pytest tests/ -v --tb=short; diff <(grep "^FAILED\|^ERROR" baseline.txt) <(pytest --tb=line -q 2>&1 \| grep "^FAILED\|^ERROR")` |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **APScheduler not fully removed from `app.py`** — residual initialisation runs alongside Celery Beat, causing duplicate scheduled task execution (violates REQ-001, REQ-009) | P0 — data corruption / double processing | Medium | T-013 explicitly removes APScheduler init; T-010 replaces all decorators; post-wave-4 grep asserts zero occurrences of `scheduler.scheduled_job` and `APScheduler` imports |
| **Celery Beat scaled to `replicas > 1`** — docker-compose or orchestrator override strips the `replicas: 1` guard, causing every periodic task to fire N times | P0 — duplicate execution | Low-Medium | Inline `# DO NOT SCALE BEYOND 1 — duplicate beat execution` comment in `docker-compose.yml`; T-009 notes constraint; address in runbook |
| **Redis unavailable at container start** — `depends_on` in Compose does not wait for Redis readiness, startup validator exits before broker is live | High — service won't start | Medium | T-012 startup check catches Redis unreachability; add `healthcheck` + `depends_on: condition: service_healthy` in T-019; document retry-wait wrapper in `start.sh` if needed |
| **CI env vars absent in non-CI local runs** — `is_localhost` detection logic ambiguous; wrong branch taken silently passes or hard-fails unexpectedly | Medium — flaky tests or credential leak | Medium | T-014 defaults `is_localhost` to `False` when ambiguous; `CI=true` always forces `is_localhost=False`; T-024 covers all four branches including the `CI` env var case |
| **Binary files remain in git history after `git rm --cached`** — PDFs/docs untracked going forward but still accessible via `git log` (partial REQ-006 compliance) | Low-Medium — history exposure | High (inherent) | Explicitly out-of-scope for this plan; document in `migrations/README.md` that history purge (BFG / `git filter-repo`) is a separate, coordinated task requiring force-push and team re-clone |
| **GitLab SAST/Secret-Detection template job stage override breaks template inheritance** — override syntax error silently disables security jobs | P0 — CI security stage never runs | Medium | Test `.gitlab-ci.yml` with `gitlab-ci-lint` in T-020; validate pipeline visually in a feature branch before merging; `allow_failure: false` on `dependency-scan` ensures build blocks |
| **`startup_checks.py` tightens environment requirements** — existing dev environments without Redis set up will fail to start the web container after T-013 lands | Medium — developer productivity | High | T-006 documents localhost fallback values in `CONTRIBUTING.md`; T-002/T-006 are Wave 1, giving developers early visibility before T-013 lands in Wave 4 |
| **Form validation changes break existing passing tests** — route handlers now return 422 / re-rendered form on previously-accepted inputs | Medium — regression | Medium | T-001 baseline recorded; T-025 integration tests use Flask test client; Wave 6 diff against baseline catches regressions before merge |
| **Worker status `inspect(timeout=1.0)` adds latency to every dashboard request** | Low-Medium — UX degradation | Medium | Timeout hard-capped at 1.0 s in T-017; T-026 asserts HTTP 200 even when `available=False`; consider async fire-and-forget if p99 latency increases are observed post-deploy |
| **Credentials committed before T-020 security stage is active** — secret detection only fires after the CI stage is wired | P0 — credential exposure | Low | T-005 (branch protection) is Wave 1 — no direct push to `main` from day one; T-020 targets the CI pipeline, not the protection gate |

---

## Non-Functional Hardening

- [x] **API boundary — input validation on all new/modified endpoints:** `validate_form()` called before any `db.session` operation in every POST handler (T-016); HTML routes return re-rendered form with field errors; JSON routes return HTTP 422 `{"errors":[…]}`
- [x] **Service layer — null/empty handling for all new operations:** `validate_required` / `validate_not_null` cover empty-string and `None` inputs (T-015, T-021); `get_worker_status()` catches all exceptions and returns `available=False` without re-raising (T-017, T-023)
- [x] **Data access — query performance, indexes:** No schema changes; no new queries introduced; validation failure short-circuits before any `db.session` write, preventing partial record accumulation
- [x] **Error handling — structured error responses:** `format_error_response()` produces consistent `{field, message}` shape (T-015); Celery tasks emit `TASK_STARTED / TASK_COMPLETED / TASK_RETRY / TASK_FAILED` structured log events (T-010); startup validator logs `CRITICAL` with the named missing variable before `sys.exit(1)` (T-012)
- [x] **Logging — structured events, no PII:** Task return values contain only status metadata (T-010 spec); worker status result fields are counts and flags only — no task payload content (T-017); test credential resolver raises `EnvironmentError` naming the variable, not the value
- [x] **Security — auth checks, PII handling:** Credentials resolved exclusively from env vars (T-006, T-014); `tests/config.py` hard-fails in non-localhost environments (T-014, T-024); CI secret detection blocks build (T-020); branch protection prevents unreviewed merges to `main` (T-005)
- [x] **Tests — unit + integration:** Unit tests for all new pure functions (T-021, T-022, T-023, T-024); integration tests for form validation with Flask test client (T-025), dashboard degradation (T-026), and Celery retry lifecycle (T-027); pre/post baseline diff required at Wave 0 and Wave 6

---

## Post-Implementation Checklist

- [ ] All Wave 0 baseline tests still pass (diff `baseline.txt` against final `pytest` run — zero new `FAILED`/`ERROR` lines)
- [ ] All new unit tests pass: `tests/test_validation.py`, `tests/test_startup_checks.py`, `tests/test_worker_status.py`, `tests/test_config.py`
- [ ] All new integration tests pass: `tests/test_form_routes.py`, `tests/test_dashboard.py`, `tests/test_celery_tasks.py`
- [ ] No `APScheduler` references remain in `app.py` or `services/ctask_scheduler.py` (`grep -R "APScheduler\|scheduler\.scheduled_job" . --include="*.py"` returns empty)
- [ ] No binary doc files tracked by git (`git ls-files | grep -E "\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$"` returns empty)
- [ ] `start.sh` is the sole web process entrypoint; no `app.run()` present in production code paths
- [ ] `CONTRIBUTING.md` and `CLAUDE.md` contain env var setup instructions with documented localhost defaults
- [ ] `migrations/README.md` classifies every migration script with APPLIED / SUPERSEDED / ENV-SPECIFIC
- [ ] `docker compose config` validates without error; `celery-beat` has `replicas: 1` and scaling warning comment
- [ ] `.gitlab-ci.yml` lints cleanly (`gitlab-ci-lint`); `security` stage appears before `build`; `dependency-scan` has `allow_failure: false`
- [ ] GitLab branch protection active: no direct push to `main`; ≥1 peer approval required; self-approval disabled — verified in project Settings → Repository → Protected branches
- [ ] All task return values verified to contain no PII (code review sign-off on T-010)
- [ ] Worker status timeout confirmed ≤1.0 s; dashboard p95 response time within acceptable bounds post-deploy

---

## Milestones

| Milestone | Completion Criteria | Target Wave |
|-----------|--------------------|-|
| **M1 — Foundation Locked** | Baseline recorded; `.gitignore` updated; `requirements.txt` updated with Celery/Gunicorn; `utils/validation.py` implemented; branch protection active; `CONTRIBUTING.md` updated | End of Wave 2 |
| **M2 — Celery Infrastructure Complete** | `celery_app.py`, `celeryconfig.py`, `startup_checks.py`, `worker_status.py` implemented and unit-tested; `start.sh` present; CI security stage wired | End of Wave 3 |
| **M3 — Application Wired** | `app.py` free of APScheduler and `app.run()`; all background tasks migrated with retry decorators and structured logs; `docker-compose.yml` includes all four services | End of Wave 4 |
| **M4 — Features Integrated** | Form validation active across all POST handlers; dashboard renders graceful degradation; Docker Compose stack starts end-to-end with `docker compose up` | End of Wave 5 |
| **M5 — Verified & Shippable** | All integration tests green; baseline diff shows zero regressions; post-implementation checklist fully signed off; MR peer-reviewed and approved via GitLab | End of Wave 6 |