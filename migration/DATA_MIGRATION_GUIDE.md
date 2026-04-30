# Shift Handover Data Migration Guide

## Overview

This guide helps you migrate shift handover reports and data from your old application to this new version without losing any data.

---

## Pre-Migration Checklist

- [ ] Backup old database completely
- [ ] Backup new database (if any existing data)
- [ ] Verify old database connection details
- [ ] Verify new database connection details
- [ ] Stop both applications during migration (recommended)
- [ ] Test migration on a staging environment first

---

## Tables to Migrate (Priority Order)

### Phase 1: Core Reference Data (Must migrate first)
1. `account` - Organization accounts
2. `team` - Teams
3. `user` - User accounts
4. `team_member` - Team member roster records
5. `user_team_memberships` - User-team associations

### Phase 2: Shift Handover Reports (Main Data)
1. `shift` - Main handover records
2. `incident` - Incidents
3. `shift_key_point` - Key points
4. `shift_key_point_update` - Key point updates
5. `shift_change_info` - Change information
6. `shift_kb_update` - KB updates
7. `current_shift_engineers` - Association table
8. `next_shift_engineers` - Association table

### Phase 3: Enhanced Handover Data (If applicable)
1. `handover_request`
2. `incident_assignment`
3. `incident_assignment_response`
4. `handover_incident_response_log`
5. `handover_response`
6. `handover_notification`
7. `handover_audit_log`

### Phase 4: Roster Data
1. `shift_roster` - Shift schedules
2. `team_shift_configs`
3. `roster_assignments`

### Phase 5: Configuration Data
1. `app_config`
2. `team_email_config`
3. `escalation_matrix_file`

---

## Migration Methods

### Method 1: Direct Database Migration (Recommended for same DB type)
Use this if both old and new apps use the same database type (e.g., both PostgreSQL).

### Method 2: Export/Import via Scripts (Recommended for different DB types)
Use this if databases are different or you need data transformation.

### Method 3: API-based Migration
Use this if you need to validate data during migration.

---

## Connection Configuration

Before running migration, update the connection details in the migration script:

```python
# Old Database (Source)
OLD_DB_CONFIG = {
    'host': 'old-server-ip',
    'port': 5432,
    'database': 'shift_handover_old',
    'user': 'db_user',
    'password': 'db_password'
}

# New Database (Target)
NEW_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'shift_handover',
    'user': 'db_user',
    'password': 'db_password'
}
```

---

## Running the Migration

### Step 1: Export from Old Database
```bash
python migration/migrate_data.py --action export --source old
```

### Step 2: Review Exported Data
Check the `migration/exports/` folder for exported JSON files.

### Step 3: Import to New Database
```bash
python migration/migrate_data.py --action import --target new
```

### Step 4: Verify Migration
```bash
python migration/migrate_data.py --action verify
```

---

## Rollback Plan

If migration fails:
1. Stop the new application
2. Restore new database from backup
3. Review migration logs in `migration/logs/`
4. Fix issues and retry

---

## Post-Migration Tasks

- [ ] Verify all reports are visible in the new app
- [ ] Check user accounts can log in
- [ ] Verify team assignments are correct
- [ ] Test creating new handover reports
- [ ] Verify historical data integrity
- [ ] Update any external integrations

---

## Support

For issues during migration, check:
1. `migration/logs/migration_YYYYMMDD_HHMMSS.log`
2. Database connection errors
3. Data type mismatches
4. Foreign key constraint violations







