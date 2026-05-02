#!/bin/bash

# Startup script for Shift Handover Application
echo "Starting Shift Handover Application..."

# Local development (SQLite) skips the MySQL readiness check entirely
if [ "$LOCAL_DEVELOPMENT" = "true" ]; then
  echo "LOCAL_DEVELOPMENT=true — skipping MySQL readiness check, using SQLite."
else
  # Read DATABASE_URL from Docker secret; fail loudly if missing
  DATABASE_URL=$(cat /run/secrets/database_url 2>/dev/null)
  if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set and /run/secrets/database_url not found. Cannot start." >&2
    exit 1
  fi
  export DATABASE_URL

  # Read DB user password for the readiness probe
  DB_PASS=$(cat /run/secrets/mysql_user_password 2>/dev/null)
  if [ -z "$DB_PASS" ]; then
    echo "ERROR: /run/secrets/mysql_user_password not found. Cannot start." >&2
    exit 1
  fi

  echo "Waiting for database connection..."
  python << PYEOF
import time, os, sys

db_pass = open('/run/secrets/mysql_user_password').read().strip()
max_attempts = 30

for attempt in range(1, max_attempts + 1):
    try:
        import pymysql
        conn = pymysql.connect(
            host='shift-db',
            user='user',
            password=db_pass,
            database='shifthandover',
            charset='utf8mb4'
        )
        conn.close()
        print("Database connection successful!")
        sys.exit(0)
    except Exception as e:
        print(f"Database connection attempt {attempt}/{max_attempts}: {e}")
        time.sleep(2)

print("ERROR: Failed to connect to database after 30 attempts", file=sys.stderr)
sys.exit(1)
PYEOF

  # Abort if the readiness check failed
  if [ $? -ne 0 ]; then
    exit 1
  fi
fi

# Initialize database schema / run Alembic migrations
echo "Initializing database schema..."
python << PYEOF
import os, sys

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # LOCAL_DEVELOPMENT path: SQLite URL expected via environment
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///local_shifthandover.db')

try:
    from sqlalchemy import create_engine, text
    from alembic.config import Config
    from alembic import command

    engine = create_engine(database_url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Database connection successful!")

    if os.path.exists('alembic.ini'):
        alembic_cfg = Config('alembic.ini')
        alembic_cfg.set_main_option('sqlalchemy.url', database_url)
        command.upgrade(alembic_cfg, 'head')
        print("Database migrations applied successfully!")
    else:
        print("alembic.ini not found, creating tables manually...")
        from app import app, db
        with app.app_context():
            db.create_all()
        print("Database tables created!")

except Exception as e:
    print(f"WARNING: Database initialization failed: {e}")
    print("Continuing without database initialization...")
PYEOF

# Start Flask application
echo "Starting Flask application on port 5000..."
exec python app.py
