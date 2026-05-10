# ShiftOps — Shift Handover Management

Multi-team shift handover web application for NOC / operations teams. Built with Flask, MySQL, and Docker.

## Features

- **Handover forms** — create, draft, edit, and submit shift handover records
- **Incident tracking** — open/closed/priority incidents with carryforward (unresolved incidents auto-populate next shift)
- **Real-time collaborative editing** — multiple engineers can co-edit a draft simultaneously via SSE + YJS CRDT
- **Roster scheduler** — auto-generate shift rosters based on team member roles and lead shift preferences
- **Key points & change info** — track action items, KB updates, and scheduled changes across shifts
- **Reports** — filter by team, date, shift type; export CSV/Excel/PDF
- **Email notifications** — scheduled digests and priority alerts per team
- **ServiceNow integration** — sync incidents and C-tasks from ServiceNow
- **SSO / SAML** — EPAM SSO support alongside local auth
- **Multi-tenancy** — Account → Team → User hierarchy; users can belong to multiple teams

---

## Quick Start

### With Docker or Podman

```bash
# Docker
docker-compose up --build

# Podman (macOS)
podman-compose up --build
```

App: http://localhost:5000  
MySQL: localhost:3306

### Without Docker (SQLite, local dev)

```bash
pip install -r requirements.txt
export LOCAL_DEVELOPMENT=true
export DATABASE_URL=sqlite:///local_shifthandover.db
python3 app.py
```

### Production

See **`docs/PROD_DEPLOYMENT_GUIDE.md`** for the full step-by-step prod deployment checklist (GCP VM, DB migrations, container rebuild).

---

## Architecture

```
app.py              Flask app factory — registers all blueprints, middleware, scheduler
routes/             ~45 blueprints, one per domain (handover, reports, roster, collab, ...)
services/           Business logic, background tasks, external integrations
models/
  models.py         Core ORM models (User, Team, Shift, Incident, ...)
  collaboration.py  Collab models (HandoverSession, SectionLock, DraftIncident, ...)
templates/          Jinja2 templates; base.html is the master layout
static/js/
  yjs.bundle.js     Self-hosted YJS CRDT (~91 KB) for collaborative editing
  collaboration.js  Collab UI logic
migrations/         Alembic/Flask-Migrate migration files
scripts/
  migrations/       Ad-hoc SQL scripts (indexes, schema fixes)
  *.sh              Backup and operator utilities
archive/            Old dev/debug scripts kept for reference (not part of the app)
docs/               Architecture and operational guides
```

See **`CLAUDE.md`** for full developer reference (running tests, secrets resolution, quirks).

---

## Running Tests

The test suite has two tiers with different requirements:

### Unit Tests — run automatically in CI (no live app needed)

```bash
pytest tests/test_startup_checks.py \
       tests/test_celery_app.py \
       tests/test_validators.py \
       tests/test_rbac_errors.py \
       tests/test_audit_service.py -v
```

### Integration Tests — require a running app + database

Start the app first (`docker-compose up` or `python3 app.py`), then:

```bash
# Quick sanity (28 tests, admin)
python3 tests/run_tests.py --url http://localhost:5000 --user superadmin --password admin123

# Full pytest suite (37 tests)
pytest tests/test_application.py -v

# Standalone suites
python3 tests/test_user_activities.py    # 37 tests
python3 tests/test_admin_activities.py   # 31 tests
python3 tests/test_handover_workflow.py  # 26 tests (full draft→submit→verify)
python3 tests/test_change_info.py        # change info dedup + reports
```

> **CI coverage:** Unit tests run automatically on every push. Integration tests must be run manually against a local or staging environment before merging to master.

See **`tests/README.md`** for full test documentation.

---

## Database Migrations

Managed by Flask-Migrate / Alembic. `start.sh` runs `alembic upgrade head` on container start.

```bash
flask db migrate -m "description"   # generate
flask db upgrade                     # apply
```

See **`DATABASE_TABLES_REFERENCE.md`** for the full table catalogue.

---

## Documentation

| File | Contents |
|------|----------|
| `CLAUDE.md` | Developer reference — running the app, architecture, quirks |
| `docs/PROD_DEPLOYMENT_GUIDE.md` | Step-by-step production deployment (DB migrations, git pull, rebuild) |
| `docs/COLLABORATIVE_EDITING.md` | Real-time collab architecture, SSE schema, conflict handling |
| `docs/roster_scheduler_design.md` | Roster scheduler design and API |
| `docs/USER_GUIDE.md` | End-user guide |
| `docs/ADMIN_GUIDE.md` | Admin configuration guide |
| `DATABASE_TABLES_REFERENCE.md` | All DB tables and column details |
| `tests/README.md` | Test suite documentation |

---

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `LOCAL_DEVELOPMENT=true` | Use SQLite, disable ProxyFix |
| `FLASK_ENV` | `production` or `development` |
| `FORCE_HTTPS` | Redirect HTTP → HTTPS |
| `DATABASE_URL` | Override DB connection string |
| `APP_DOMAIN` / `APP_BASE_URL` | OAuth redirect URIs |

Required secret files for local dev (in `secrets/`): `flask_secret_key`, `database_url`, `sso_encryption_key`, `secrets_master_key`, `mysql_password`, `smtp_username`, `smtp_password`.

---

## Repository Structure

This project uses two repositories:

| Repository | Purpose |
|------------|---------|
| `git.garage.epam.com/shift-handover-automation/shifthandover_v3` | **Primary** — internal EPAM GitLab. All development, MRs, and CI/CD pipelines run here. |
| `github.com/mdsajiddevops/shifthadnover` | **Public mirror** — GitHub copy for external visibility. Pushed from the `develop` branch of the primary repo. Do not raise PRs here. |

**All contributions must go through the GitLab repository.** The GitHub repo is a read-only public mirror and is not the development source of truth.
