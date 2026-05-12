# Contributing to ShiftHandover

## Prerequisites
- Python 3.11+, Docker, docker-compose (or podman-compose)

## Local setup

```bash
cp secrets/README.md secrets/   # create secrets files per the README
docker-compose up -d
flask db upgrade
```

Or without Docker (SQLite):
```bash
pip install -r requirements.txt
export LOCAL_DEVELOPMENT=true
export DATABASE_URL=sqlite:///local_shifthandover.db
python app.py
```

## Git workflow

```
develop  →  staging  (auto-deploy on every merge to develop)
master   →  production  (manual deploy, promoted from develop)
```

1. **Branch from `develop`** (not `master`)
2. Open MR targeting `develop` — pipeline must pass, 1 approval required
3. Merge to `develop` → auto-deploys to staging
4. When staging is validated, `develop` is merged to `master` → manual deploy to prod

## Branch naming
- Features: `feature/SHO-<number>-<short-description>`
- Bugfixes: `fix/SHO-<number>-<short-description>`

## Running tests

### Unit tests (no running app required)

```bash
pytest tests/test_startup_checks.py tests/test_celery_app.py tests/test_dlq_handler.py \
       tests/test_celery_tasks.py tests/test_ctask_scheduler.py \
       tests/test_validators.py tests/test_rbac_errors.py \
       tests/test_audit_service.py tests/test_tests_config.py \
       tests/test_validation.py tests/test_worker_status.py -v
```

### HTTP integration tests (require a running app instance)

```bash
# Start the app first, then set credentials:
export TEST_SUPERADMIN_PASSWORD=<your-superadmin-password>
export TEST_ADMIN_PASSWORD=<your-admin-password>
export TEST_USER_PASSWORD=<your-user-password>
python tests/run_tests.py --url http://localhost:5000 --user superadmin --password $TEST_SUPERADMIN_PASSWORD --verbose
pytest tests/test_application.py -v
```

**Important:** `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, and `TEST_USER_PASSWORD`
must be set before running tests against any non-localhost `TEST_BASE_URL`. The
sentinel fallbacks (`admin123`, `test123`) only work against `localhost`.

## Background worker (Celery)

All scheduled background jobs run in the Celery execution tier — the Flask web
process has no scheduler. For full functionality during development, run:

```bash
# Terminal 1 — Celery worker
celery -A celery_app worker --loglevel=info

# Terminal 2 — Celery Beat (periodic task scheduler — single instance only)
celery -A celery_app beat --loglevel=info

# Required environment variables
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

With Docker, `celery-worker` and `celery-beat` services start automatically.

### Adding a new background task

1. Create a task function in the appropriate `tasks/*.py` module using `bind=True,
   max_retries=3, default_retry_delay=30`.
2. On `MaxRetriesExceededError`, call `tasks.dlq_handler.on_task_failure(...)`.
3. Register the task in `celeryconfig.py` `beat_schedule` if it is periodic.
4. Add a unit test in `tests/test_celery_tasks.py`.

## Database schema changes

**All new schema changes must go through Alembic** (REQ-011):

```bash
flask db migrate -m "short description"
flask db upgrade
```

After generating the migration, add an entry to `migrations/README.md` with:
- Order number (next sequential integer)
- Revision ID (from the generated file name)
- Description
- Type: `alembic`
- Status: `pending`

Never write raw SQL for changes that should be environment-portable.

## Linting

```bash
ruff check . --fix
ruff format .
```

## Pull request checklist
- [ ] Unit tests pass (`pytest tests/test_*.py -v`)
- [ ] Lint passes (`ruff check .`)
- [ ] `secrets/` directory was not committed
- [ ] No `.env` files (other than `.example` templates) were committed
- [ ] No binary documents (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`) committed — use Confluence
- [ ] If schema changed: `flask db migrate` run, migration registered in `migrations/README.md`
- [ ] If new Celery task: registered in `celeryconfig.py` and tested in `tests/test_celery_tasks.py`
- [ ] CHANGELOG.md updated if user-facing change
- [ ] Confluence updated if architecture changed
- [ ] Minimum 1 peer review approval required before merging to develop (REQ-012)
