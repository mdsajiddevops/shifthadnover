# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This App Does

Multi-team shift handover management web app for NOC/operations teams. Core flows: create/draft/submit handover forms, track incidents and key points, manage shift rosters, check-in/check-out, send email notifications, and generate reports. Supports ServiceNow integration, SSO, and real-time collaborative editing of handover drafts.

## Running the App

**With Docker (standard):**
```bash
docker-compose up --build
# App at http://localhost:5000, MySQL on 3306
```

**Without Docker (local dev with SQLite):**
```bash
pip install -r requirements.txt
export LOCAL_DEVELOPMENT=true
export DATABASE_URL=sqlite:///local_shifthandover.db
python app.py
```

**Production:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Database Migrations

Schema is managed via Flask-Migrate (in `migrations/`), but `start.sh` calls Alembic's Python API directly (`command.upgrade(cfg, 'head')`) on container start — so any migration must work under both entry points.

```bash
# Generate a new migration
flask db migrate -m "description"

# Apply migrations
flask db upgrade

# Manual SQL scripts for ad-hoc changes (run directly):
# add_performance_indexes.sql
# add_uns_event_id.sql
```

`alembic.ini` has a placeholder DB URL (`user:password@db`) — the real URL is injected at runtime by `start.sh`.

## Running Tests

All tests are HTTP integration tests — they require a **running app instance** (Docker or local dev). There is no unit-test layer.

Two runners coexist:

```bash
# Custom suite runner (admin sanity checks)
python tests/run_tests.py --url http://localhost:5000 --user superadmin --password $TEST_SUPERADMIN_PASSWORD --verbose

# pytest (test_application.py only)
pytest tests/test_application.py -v

# Single test
pytest tests/test_application.py::TestKeyPointsConsistency::test_no_duplicate_keypoints -v

# Standalone scripts (each accepts --url/--user/--password)
python tests/test_user_activities.py        # 37 tests, any user
python tests/test_admin_activities.py       # 31 tests, admin only
python tests/test_handover_workflow.py      # full draft → submit → verify flow
python tests/test_change_info.py            # change-info dedup + reports
```

Test config (base URL, default creds, timeouts) lives in `tests/config.py`.

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

DB-polling based — no Redis or WebSockets. Models: `HandoverSession`, `SectionLock`, `HandoverChange`, `DraftIncident`, `DraftKeyPoint` in `models/collaboration.py`. Multiple users can co-edit a handover draft by polling for lock state and change deltas.

### Session Security

Every request runs `validate_session()` middleware that checks `session_token` against the DB — allows server-side forced logout (e.g., admin terminates a user session).

### Background Scheduler

Background jobs (ServiceNow CTask polling) run via **Celery Beat** — see `celery_app.py` and `tasks.py`. The `celery-worker` and `celery-beat` services in `docker-compose.yml` must be running for scheduled tasks to execute. The Gunicorn web process has no scheduler and can be scaled to multiple workers safely.

### Operator Scripts

`scripts/` holds operator utilities that are not invoked by the app: `db_backup.sh`, `app_backup.sh`, `backup_status.sh` for backups, and `convert_prints_to_logging*.py` are one-off codemods that have already been applied — don't re-run them.

## Key Environment Variables

| Variable | Purpose |
|---|---|
| `LOCAL_DEVELOPMENT=true` | Uses SQLite, disables ProxyFix |
| `FLASK_ENV` | `production` or `development` |
| `FORCE_HTTPS` | Redirect all HTTP to HTTPS |
| `APP_DOMAIN` / `APP_BASE_URL` | Used for OAuth redirect URIs |
| `DATABASE_URL` | Override DB connection string |

## Known Quirks

- `backup_temp.sql` and `backup_v3.sql` in the repo root are large SQL dumps (7.5MB / 3.7MB) — likely should not be committed.
- Files named `*(1).py` (e.g., `services/servicenow_service(1).py`, `models/servicenow_models(1).py`) are unintentional duplicate copies — ignore them, edit the un-suffixed file.
- `base.html` exists **both** at the repo root and in `templates/`. Flask renders from `templates/`; the root copy is stale — don't edit it.
- The repo root contains many `backup_YYYYMMDD_HHMMSS/` directories and `check_*.py` / `debug_*.py` / `fix_*.py` scripts that show as tracked-deleted in `git status`. Treat them as obsolete — don't extend or revive them.
- `start.sh` has a hardcoded `userpassword` in the DB readiness wait loop — dev leftover, does not affect production secrets.
