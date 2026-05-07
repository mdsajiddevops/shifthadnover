# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This App Does

Multi-team shift handover management web app for NOC/operations teams. Core flows: create/draft/submit handover forms, track incidents and key points, manage shift rosters, check-in/check-out, send email notifications, and generate reports. Supports ServiceNow integration, SSO, and real-time collaborative editing of handover drafts.

## Running the App

**With Docker / Podman (standard):**
```bash
docker-compose up --build
# or on macOS with Podman:
podman-compose up --build
# App at http://localhost:5000, MySQL on 3306
```

> Local dev note: `docker-compose.yml` has `command: python app.py` which overrides the Dockerfile CMD (`start.sh`). This intentionally skips Alembic migrations on local start. The prod compose file does not have this override — `start.sh` runs migrations there.

**Without Docker (local dev with SQLite):**
```bash
pip install -r requirements.txt
export LOCAL_DEVELOPMENT=true
export DATABASE_URL=sqlite:///local_shifthandover.db
python3 app.py
```

**Production (GCP VM):**
```bash
docker-compose -f docker-compose.prod.yml up -d
# See docs/PROD_DEPLOYMENT_GUIDE.md for full step-by-step prod deployment checklist
```

## Database Migrations

Schema is managed via Flask-Migrate (in `migrations/`), but `start.sh` calls Alembic's Python API directly (`command.upgrade(cfg, 'head')`) on container start — so any migration must work under both entry points.

```bash
# Generate a new migration
flask db migrate -m "description"

# Apply migrations
flask db upgrade
```

`alembic.ini` has a placeholder DB URL (`user:password@db`) — the real URL is injected at runtime by `start.sh`.

Ad-hoc SQL migration scripts live in `scripts/migrations/` (moved from root during cleanup). These are run directly via `mysql` or `docker exec` — they are not Alembic migrations.

**Prod-specific:** The prod DB has no `alembic_version` table by default. After running manual ALTER TABLE statements, insert the head revision manually so `start.sh` doesn't re-run migrations:
```sql
CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);
INSERT IGNORE INTO alembic_version VALUES ('fix_scheduling_role_nullable');
```

## Running Tests

**Unit tests** (no running app required):
```bash
pytest tests/test_startup_checks.py tests/test_celery_app.py tests/test_dlq_handler.py \
       tests/test_celery_tasks.py tests/test_ctask_scheduler.py \
       tests/test_validators.py tests/test_rbac_errors.py \
       tests/test_audit_service.py tests/test_tests_config.py -v
```

**HTTP integration tests** (require a running app instance — Docker or local dev):
```bash
# 1. Custom sanity suite (28 tests, admin)
python3 tests/run_tests.py --url http://localhost:5000 --user superadmin --password $TEST_SUPERADMIN_PASSWORD --verbose

# 2. pytest suite (37 tests)
pytest tests/test_application.py -v

# 3. Standalone scripts (each accepts --url/--user/--password)
python3 tests/test_user_activities.py        # 37 tests, any user
python3 tests/test_admin_activities.py       # 31 tests, admin only
python3 tests/test_handover_workflow.py      # 26 tests, full draft → submit → verify flow
python3 tests/test_change_info.py            # change-info dedup + reports
```

**Known test credentials (local dev with prod DB import):**
- `superadmin` / `admin123` — super admin
- `noc_admin` / `Admin@123` — account admin (test user, created locally)
- `alice` / `User@123` — regular user (test user, created locally)

**Session token note:** Flask stores one `session_token` per User row. A second login for the same user invalidates the first session. Always use distinct users when two concurrent sessions are needed in tests.

Test config (base URL, default creds, timeouts) lives in `tests/config.py`.

**Test credentials:** always set env vars before targeting non-localhost:
```bash
export TEST_SUPERADMIN_PASSWORD=<password>
export TEST_ADMIN_PASSWORD=<password>
export TEST_USER_PASSWORD=<password>
export TEST_BASE_URL=http://localhost:5000   # optional
```
Omitting these against a non-localhost `TEST_BASE_URL` raises `ConfigurationError` (prevents sentinel credentials reaching remote systems).

## Architecture

### Layered Blueprint Structure

- `routes/` (~45 Blueprints) — HTTP handling only; one Blueprint per domain area
- `services/` (~20 modules) — all business logic, background tasks, external integrations
- `models/` — SQLAlchemy ORM models + DB-stored config singletons
- `templates/` — Jinja2 server-side rendering; `base.html` is the master layout
- `static/` — CSS, JS, sample files

`app.py` is the Flask app factory: initializes extensions, registers all Blueprints, sets up session validation middleware, and template globals.

### Multi-Tenancy Model

`Account` → `Team` → `User` hierarchy. Users can belong to multiple teams via `UserTeamMembership`. The active context (account + team) is carried in Flask session as `selected_account_id` / `selected_team_id`. Helpers `set_selection()` and `set_team_filter()` manage these.

### Role-Based Access

Four roles: `super_admin` > `account_admin` > `team_admin` > `user`. Enforced inline in routes (not via decorators). `super_admin` bypasses most team/account filters.

### Secrets Resolution (Three-Tier)

`config.py` `SecureConfigManager` resolves in priority order:
1. `/run/secrets/<name>` — Docker secrets (production)
2. `./secrets/<name>` — local files (development; see `secrets/` dir for required files)
3. `os.environ.get(NAME.upper())` — environment variables

Runtime config (SMTP, ServiceNow credentials, OAuth, shift timings) is stored **encrypted in the DB** via `SecretsManager` (Fernet), loaded at startup via `Config.init_from_database()`.

Required secret files for local dev: `flask_secret_key`, `database_url`, `sso_encryption_key`, `secrets_master_key`, `mysql_password`, `smtp_username`, `smtp_password`.

### Collaborative Editing

SSE-based (Server-Sent Events) — no Redis or WebSockets. Models in `models/collaboration.py`: `HandoverSession`, `SectionLock`, `HandoverChange`, `DraftIncident`, `DraftKeyPoint`, `DraftChangeInfo`, `DraftKBUpdate`. Multiple users can co-edit a handover draft with live presence indicators, field-level typing indicators, and soft locking.

YJS CRDT library is self-hosted (`static/js/yjs.bundle.js`, ~91 KB) — no CDN dependency. Routes: `routes/collaboration.py` (API endpoints) and `routes/collab_sse.py` (SSE stream). See `docs/COLLABORATIVE_EDITING.md` for full architecture.

**Single-process constraint:** The in-memory field state (`_field_states`, `_typing_indicators`) lives inside the Flask process. Deployments must use a single Gunicorn worker — horizontal scaling requires Redis.

### Session Security

Every request runs `validate_session()` middleware that checks `session_token` against the DB — allows server-side forced logout (e.g., admin terminates a user session).

### Background Scheduler (Celery Execution Tier)

All background job execution is delegated exclusively to Celery — the HTTP-serving process (Gunicorn) runs **zero** scheduled jobs (REQ-003/ADR-001).

**Architecture:**
- `celery_app.py` — standalone Celery application; reads `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` exclusively from environment variables.
- `celeryconfig.py` — Beat periodic schedule for all four job types.
- `tasks/` package — individual task modules:
  - `tasks/ctask_tasks.py` — CTask auto-assignment (every 2 minutes)
  - `tasks/email_tasks.py` — email digest (hourly)
  - `tasks/servicenow_tasks.py` — ServiceNow incident/CTask sync (every 5 minutes)
  - `tasks/retry_tasks.py` — DLQ retry sweep (every 10 minutes)
  - `tasks/dlq_handler.py` — on-failure callback; writes `failed_tasks` DB record and dispatches ops alert

**Starting workers (all required for background jobs):**
```bash
# Celery worker (processes tasks from queue)
celery -A celery_app worker --loglevel=info

# Celery Beat (enqueues periodic tasks — must run as a single instance)
celery -A celery_app beat --loglevel=info
```

**Environment variables required:**
```bash
export CELERY_BROKER_URL=redis://redis:6379/0
export CELERY_RESULT_BACKEND=redis://redis:6379/0
```

**Scheduler management API** (`services/ctask_scheduler.py`):
- `get_scheduler_status()` — uses `celery.control.inspect(timeout=2.0)`; returns structured dict; never raises even when broker is unreachable (REQ-004/REQ-013).
- `force_scheduler_check()` — dispatches `run_ctask_assignment.delay()`.
- `start_ctask_scheduler()` / `stop_ctask_scheduler()` — no-ops; managed via docker-compose.

**Dead-letter queue:** Tasks exhausting all 3 retries write a `FailedTask` record (see `models/failed_task.py`) and dispatch an ops alert. Failed records can be re-queued by setting `status='pending_retry'` — the retry sweep picks them up automatically.

### Operator Scripts

`scripts/` holds operator utilities not invoked by the app:
- `db_backup.sh`, `app_backup.sh`, `backup_status.sh` — backup helpers
- `convert_prints_to_logging*.py` — one-off codemods already applied, don't re-run
- `scripts/migrations/` — ad-hoc SQL scripts (`add_performance_indexes.sql`, `add_uns_event_id.sql`, `add_session_columns.sql`, etc.)

`archive/` contains old dev/debug scripts (`check_*.py`, `debug_*.py`, shell helpers) preserved for reference — they are not part of the running app.

## Key Environment Variables

| Variable | Purpose |
|---|---|
| `LOCAL_DEVELOPMENT=true` | Uses SQLite, disables ProxyFix, skips Docker-secret checks |
| `FLASK_ENV` | `production` or `development` |
| `FORCE_HTTPS` | Redirect all HTTP to HTTPS |
| `APP_DOMAIN` / `APP_BASE_URL` | Used for OAuth redirect URIs |
| `DATABASE_URL` | Override DB connection string |
| `CELERY_BROKER_URL` | Redis broker URL for Celery (default: `redis://redis:6379/0`) |
| `CELERY_RESULT_BACKEND` | Redis result backend URL (default: `redis://redis:6379/0`) |
| `TEST_BASE_URL` | Base URL for integration tests (default: `http://localhost:5000`) |
| `TEST_SUPERADMIN_PASSWORD` | Superadmin password for tests (required for non-localhost) |
| `TEST_ADMIN_PASSWORD` | Account admin password for tests (required for non-localhost) |
| `TEST_USER_PASSWORD` | Regular user password for tests (required for non-localhost) |

## Recent Features (CTCOAMSHM-1)

These were added on the `CTCOAMSHM-1-realtime-collab-handover` branch and require 4 new DB columns on prod (see `docs/PROD_DEPLOYMENT_GUIDE.md`):

- **Incident carryforward**: Unresolved `Open`/`Handover` incidents auto-populate the next shift's handover form. Controlled by `incident.is_resolved` (TINYINT, default 0) and `incident.resolved_at` (DATETIME). A 7-day rolling window (via JOIN to `Shift.date`) limits how far back carryforward looks — prevents pre-feature incidents from flooding the form.
- **Unified incident section**: The 5-card incident layout was replaced by a single Status dropdown section in `templates/handover_form.html`.
- **Roster scheduler**: `team_member.scheduling_role` (`lead`/`support`) and `team_member.lead_shift` (preferred shift code, e.g. `E`) added to support automated roster generation via `routes/roster_scheduler.py`.
- **Real-time collaborative editing**: SSE-based co-editing of handover drafts. YJS CRDT bundle is self-hosted at `static/js/yjs.bundle.js`.

## Known Quirks

- `base.html` exists **both** at the repo root and in `templates/`. Flask renders from `templates/`; the root copy is stale — don't edit it.
- `start.sh` has a hardcoded `userpassword` in the DB readiness wait loop — dev leftover, does not affect production secrets.
- `migration/` (singular, at root) is a legacy data migration directory — unrelated to `migrations/` (Alembic). Don't confuse the two.
- SSL cert files (`fullchain.pem`, `private.key`, `star.lab.epam.com.pfx`) are present locally for nginx but are in `.gitignore` — never commit them.
