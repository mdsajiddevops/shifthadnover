#!/bin/bash
# Startup script for Shift Handover Application (COMP-001).
#
# Sequence:
#   1. startup_checks.py — validates secrets and DB reachability (REQ-014).
#      Non-zero exit aborts here; Gunicorn is never started.
#   2. Alembic migrations — applies any pending schema changes.
#   3. exec gunicorn — replaces this shell as PID 1 for clean signal handling.
#
# REQ-001: startup is defined here, not in the application module.
# REQ-002: Gunicorn is the WSGI server; parameters come from gunicorn.conf.py.

set -e

echo "Starting Shift Handover Application..."

# ── 1. Pre-flight checks (secrets + DB reachability) ────────────────────────
python startup_checks.py

# ── 2. Database migrations ───────────────────────────────────────────────────
echo "Initialising database schema..."
python - <<'PYEOF'
import os, sys

if os.environ.get('LOCAL_DEVELOPMENT', '').lower() == 'true':
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///local_shifthandover.db')
else:
    # Read from Docker secret (already validated by startup_checks.py).
    try:
        db_url = open('/run/secrets/database_url').read().strip()
    except OSError:
        db_url = os.environ.get('DATABASE_URL', '')

if not db_url:
    print('ERROR: DATABASE_URL unavailable for migration step.', file=sys.stderr)
    sys.exit(1)

try:
    from alembic.config import Config
    from alembic import command

    if os.path.exists('alembic.ini'):
        alembic_cfg = Config('alembic.ini')
        alembic_cfg.set_main_option('sqlalchemy.url', db_url)
        command.upgrade(alembic_cfg, 'head')
        print('Database migrations applied successfully!')
    else:
        from app import app, db
        with app.app_context():
            db.create_all()
        print('Database tables created via SQLAlchemy create_all.')
except Exception as exc:
    print(f'WARNING: Database initialisation failed: {exc}')
    print('Continuing without migration — manual intervention may be required.')
PYEOF

# ── 3. Launch WSGI server ────────────────────────────────────────────────────
echo "Starting Flask application via Gunicorn on port 5000..."
exec gunicorn --config gunicorn.conf.py app:app
