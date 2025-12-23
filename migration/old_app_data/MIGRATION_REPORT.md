# Shift Handover Data Migration Report

## Source Server Details
- **Server IP**: 35.200.202.18
- **Username**: shifthandoversajid
- **Application Path**: ~/shift_handover_app/
- **Database**: MySQL 8.0 - shift_handover
- **Export Date**: December 23, 2025

---

## Exported Data Summary

### 1. Handover Data (`handover_data.sql`)
Contains shift handover reports and related data:

| Table | Records | Description |
|-------|---------|-------------|
| `shift` | 123 | Main shift handover records |
| `shift_key_point` | 254 | Key points for each shift |
| `shift_key_point_update` | 17 | Updates/changes to key points |
| `incident` | 299 | Incidents recorded in handovers |
| `handover_request` | 123 | Handover request records |
| `handover_response` | varies | Response records |
| `current_shift_engineers` | varies | Current shift engineer assignments |
| `next_shift_engineers` | varies | Next shift engineer assignments |
| `handover_incident_response_log` | varies | Incident response logs |

### 2. Reference Data (`reference_data.sql`)
Contains organizational structure:

| Table | Description |
|-------|-------------|
| `account` | Account/Organization records |
| `team` | Team definitions |
| `user` | User accounts |
| `team_member` | Team membership records |
| `user_team_memberships` | Multi-team user associations |

### 3. Roster Data (`roster_data.sql`)
Contains shift scheduling data:

| Table | Description |
|-------|-------------|
| `shift_roster` | Shift schedule assignments |
| `escalation_matrix_file` | Escalation matrix uploads |
| `team_shift_timing_configs` | Shift timing configurations |

### 4. Full Backup (`full_database_dump.sql`)
Complete database dump (3.0 MB) - includes all tables with structure and data.

---

## Data Verification Checklist

Before importing, verify the following:

### Shift Records Sample:
```
- Shift ID 23: Date 2025-11-21, Evening→Night, Account 3, Team 12
- Shift ID 75: Date 2025-11-26, Morning→Evening, Account 3, Team 13 (with detailed notes)
- Shift ID 100: Date 2025-12-05, Morning→Evening, Account 3, Team 5 (AGV incident details)
```

### Key Point Records Sample:
```
- KP ID 158: "Sensue Monitoring - Morning" - Account 3, Team 13
- KP ID 180: "Complete ELITEA DOM Agent Feedback" - Account 3, Team 5
- KP ID 247: "test key point" - Account 1, Team 2
```

### Accounts in Data:
- Account ID 1: Test Account
- Account ID 3: Production Account (CTC)

### Teams in Data:
- Team ID 2: Test Team
- Team ID 5: CTC Supply Chain
- Team ID 6: TechOps Team
- Team ID 12: CTC L2 Support
- Team ID 13: CTC L1 Support

---

## Import Instructions

### Option 1: Import Only Handover Data (Recommended for First Run)
```bash
# Connect to local MySQL and import handover data
docker exec -i shifthandover_v3-db-1 mysql -uroot -p<password> shifthandover < migration/old_app_data/handover_data.sql
```

### Option 2: Import Full Database (Complete Migration)
```bash
# This will import ALL data including users, teams, accounts
docker exec -i shifthandover_v3-db-1 mysql -uroot -p<password> shifthandover < migration/old_app_data/full_database_dump.sql
```

### Option 3: Selective Import (Step by Step)
```bash
# 1. First import reference data (accounts, teams, users)
docker exec -i shifthandover_v3-db-1 mysql -uroot -p<password> shifthandover < migration/old_app_data/reference_data.sql

# 2. Then import handover data
docker exec -i shifthandover_v3-db-1 mysql -uroot -p<password> shifthandover < migration/old_app_data/handover_data.sql

# 3. Finally import roster data
docker exec -i shifthandover_v3-db-1 mysql -uroot -p<password> shifthandover < migration/old_app_data/roster_data.sql
```

---

## Important Notes

1. **Foreign Key Constraints**: The import files disable foreign key checks during import
2. **Auto-increment IDs**: Will continue from existing values
3. **No Data Deletion**: Original data in GCP server is untouched
4. **Backup First**: Always backup your local database before importing

---

## Post-Import Verification

After import, verify data integrity:
```sql
-- Check shift counts
SELECT COUNT(*) FROM shift;

-- Check key points
SELECT COUNT(*) FROM shift_key_point;

-- Verify recent shifts
SELECT id, date, current_shift_type, status FROM shift ORDER BY id DESC LIMIT 10;
```

---

## Files Location
```
migration/old_app_data/
├── full_database_dump.sql    (3.0 MB - Complete backup)
├── handover_data.sql         (154 KB - Handover records)
├── reference_data.sql        (32 KB - Accounts, Teams, Users)
├── roster_data.sql           (67 KB - Shift rosters)
└── MIGRATION_REPORT.md       (This file)
```




