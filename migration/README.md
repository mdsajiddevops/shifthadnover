# migration/ — Legacy Data Migration (NOT Alembic)

This directory is **not** the Flask-Migrate/Alembic schema migration directory.

| Directory | Purpose |
|-----------|---------|
| `migration/` (this dir) | One-time data migration scripts from the v1/v2 app to the current schema |
| `migrations/` (repo root) | Flask-Migrate (Alembic) schema migrations — this is the authoritative source |

The scripts here (`migrate_data.py`, `migrate_with_flask.py`) were used to port data from the old SQLite-based app to the current MySQL schema. They are preserved for reference only and should not be re-run.

For schema changes, always use:
```bash
flask db migrate -m "description"
flask db upgrade
```
