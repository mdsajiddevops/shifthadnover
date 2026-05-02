"""
Pre-flight startup checks (COMP-004).

Validates that all required secrets are present and the primary database is
reachable before Gunicorn binds to any port (REQ-014).

Run standalone:  python startup_checks.py
Exit 0 on success, exit 1 on any failure with a JSON error to stderr.
Total timeout budget: ≤10 s (secrets check ≤5 s, DB probe ≤5 s).
"""
import json
import os
import sys

# Module-level reference so tests can patch startup_checks.create_engine.
# Guarded so this module is importable without sqlalchemy (test environments).
try:
    from sqlalchemy import create_engine, text
except ImportError:  # pragma: no cover
    create_engine = None  # type: ignore[assignment]
    text = str  # type: ignore[assignment]  # fallback: pass raw string to execute

# ---------------------------------------------------------------------------
# Required secrets — all resolved via the 3-tier hierarchy:
#   1. /run/secrets/<name>  (Docker secrets, production)
#   2. ./secrets/<name>     (local dev files)
#   3. os.environ[NAME]     (environment variables)
# ---------------------------------------------------------------------------
REQUIRED_SECRETS = [
    'flask_secret_key',
    'database_url',
    'secrets_master_key',
]

# Local development bypasses Docker-secret checks (uses SQLite instead).
LOCAL_DEVELOPMENT = os.environ.get('LOCAL_DEVELOPMENT', '').lower() == 'true'


def _resolve_secret(name: str) -> str | None:
    """Return the secret value or None if unavailable."""
    docker_path = f'/run/secrets/{name}'
    local_path = f'./secrets/{name}'

    for path in (docker_path, local_path):
        try:
            with open(path) as fh:
                return fh.read().strip()
        except OSError:
            pass

    return os.environ.get(name.upper())


def _fail(check: str, field: str, error: str) -> None:
    json.dump({'check': check, 'field': field, 'error': error}, sys.stderr)
    sys.stderr.write('\n')
    sys.exit(1)


def check_secrets() -> None:
    """Verify all required secrets are present and non-empty."""
    if LOCAL_DEVELOPMENT:
        return  # Docker secrets not required in local dev mode.

    for name in REQUIRED_SECRETS:
        try:
            value = _resolve_secret(name)
        except Exception as exc:
            _fail('secrets', name, f'resolution error: {exc}')

        if not value:
            _fail('secrets', name, 'secret is absent or empty')


def check_database() -> None:
    """Probe primary database with a SELECT 1 query (≤5 s timeout)."""
    if LOCAL_DEVELOPMENT:
        db_url = os.environ.get('DATABASE_URL', 'sqlite:///local_shifthandover.db')
    else:
        db_url = _resolve_secret('database_url')
        if not db_url:
            _fail('database', 'PRIMARY_DB', 'DATABASE_URL secret unavailable')

    try:
        connect_args: dict = {}
        if db_url.startswith('mysql') or db_url.startswith('postgresql'):
            connect_args['connect_timeout'] = 5

        engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=False,
        )
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        engine.dispose()
    except Exception as exc:
        _fail('database', 'PRIMARY_DB', str(exc))


if __name__ == '__main__':
    check_secrets()
    check_database()
    json.dump({'check': 'all', 'status': 'ok'}, sys.stdout)
    sys.stdout.write('\n')
    sys.exit(0)
