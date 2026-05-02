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

## Branch naming
- Features: `feature/<short-description>`
- Bugfixes: `fix/<short-description>`
- Always branch from `master`

## Running tests

Tests are HTTP integration tests — they require a running app instance.

```bash
# Start the app first, then:
export TEST_SUPERADMIN_PASSWORD=<your-superadmin-password>
python tests/run_tests.py --url http://localhost:5000 --user superadmin --password $TEST_SUPERADMIN_PASSWORD --verbose
pytest tests/test_application.py -v
```

## Linting

```bash
ruff check . --fix
ruff format .
```

## Pull request checklist
- [ ] Tests pass
- [ ] Lint passes (`ruff check .`)
- [ ] `secrets/` directory was not committed
- [ ] No `.env` files (other than `.example` templates) were committed
- [ ] CHANGELOG.md updated if user-facing change
- [ ] Confluence updated if architecture changed
