# Migrations

This directory contains two types of schema changes. Read this before touching
anything — mixing the two without care causes schema drift.

---

## 1. Alembic versioned migrations (`migrations/versions/`)

Managed by Flask-Migrate. Applied automatically at startup via `flask db upgrade`
(or `alembic upgrade head` in `start.sh`). These are the **authoritative** schema
history — never edit a committed revision file.

REQ-010: every migration is catalogued below with identifier, status, and execution order.

| Order | Revision ID / File | Description | Type | Status |
|------|--------------------|-------------|------|--------|
| 1 | `001_team_roster_tables.py` | Initial team and roster tables | alembic | applied |
| 2 | `add_app_config_table.py` | App-level feature config storage | alembic | applied |
| 3 | `add_application_detail_table.py` | Application detail fields | alembic | applied |
| 4 | `add_checkin_system.py` | Engineer check-in/check-out | alembic | applied |
| 5 | `add_collaborative_handover_tables.py` | Draft/lock/change tables for co-editing | alembic | applied |
| 6 | `add_incident_fields.py` | Extra fields on incident records | alembic | applied |
| 7 | `add_jira_id_to_keypoint.py` | Jira issue ID column on key points | alembic | applied |
| 8 | `add_servicenow_config_table.py` | ServiceNow connection config | alembic | applied |
| 9 | `add_servicenow_tables.py` | ServiceNow CTask and incident tables | alembic | applied |
| 10 | `add_status_to_shift_change_info.py` | Status field on change info records | alembic | applied |
| 11 | `add_team_email_configuration.py` | Per-team email config | alembic | applied |
| 12 | `add_user_role_column.py` | Role column on user table | alembic | applied |
| 13 | `add_failed_tasks_table.py` *(pending generation)* | Dead-letter queue table for exhausted Celery tasks | alembic | pending |

**To add a new schema change:** always use `flask db migrate -m "description"` — never
write a raw SQL file for changes that should be environment-portable (REQ-011).

---

## 2. Ad-hoc SQL scripts (`migrations/*.sql`)

These were run **manually** on specific environments. They are NOT tracked by
Alembic and will NOT run automatically. Before applying to a new environment,
verify whether the change is already covered by an Alembic revision above.

| File | Purpose | Status |
|------|---------|--------|
| `init_local.sql` | Seed data + schema bootstrap for local Docker dev | Applied to local dev only |
| `init_test.sql` | Minimal schema for CI/integration test runs | Applied in CI only |
| `add_performance_indexes.sql` | Composite indexes for dashboard query performance | Applied to production |
| `add_team_email_columns.sql` | Extra columns on team email config (pre-migration era) | Applied to production |
| `add_user_team_memberships.sql` | Junction table for multi-team user membership | Applied to production |
| `alter_incident_title_length.sql` | Increase incident title VARCHAR length | Applied to production |
| `create_collaboration_tables.sql` | Early version of collaboration tables (superseded by Alembic `add_collaborative_handover_tables.py`) | **Do not re-apply** — covered by Alembic |
| `add_draft_collaboration_tables.sql` | Draft incident/keypoint tables (superseded by Alembic revision) | **Do not re-apply** — covered by Alembic |
| `create_team_feature_config_table.sql` | Team feature flag table (first attempt) | Check against `add_app_config_table.py` before applying |
| `create_team_feature_config_simple.sql` | Simplified version of above | Check against `add_app_config_table.py` before applying |

---

## 3. Ad-hoc Python scripts (`migrations/*.py`)

One-off data migration scripts run manually. Safe to re-read but not to re-run.

| File | Purpose | Status |
|------|---------|--------|
| `add_email_configuration_tables.py` | Creates email config tables via SQLAlchemy (pre-Alembic era) | Applied — superseded by Alembic |
| `add_team_email_config.py` | Populates default team email config rows | Applied to production |
| `migrate_user_teams.py` | Backfills UserTeamMembership from legacy single-team user records | Applied to production — one-time data migration |

---

## Rules going forward

1. **All new schema changes must go through Alembic** — `flask db migrate` + `flask db upgrade`
2. **Never run a raw SQL script without checking if Alembic already covers it** (see "Do not re-apply" entries above)
3. **If a raw SQL fix is urgent** (hotfix scenario), run it manually then immediately create an Alembic migration that matches, so the revision chain stays accurate
4. **Document it here** — update this table when any script is applied to a new environment

---

## Applying to a fresh environment

```bash
# 1. Alembic handles all versioned changes automatically:
flask db upgrade

# 2. Apply the performance indexes manually (not in Alembic chain):
mysql -u user -p shifthandover < migrations/add_performance_indexes.sql

# 3. Seed local dev data if needed:
mysql -u user -p shifthandover < migrations/init_local.sql
```
