# Backup Scripts Documentation

This document describes the backup scripts configured for the Shift Handover Application.

## Overview

The backup system consists of automated scripts that create regular backups of both the application code and the MySQL database. These scripts are scheduled using cron jobs on the production server.

## Backup Scripts

### 1. Application Backup (`app_backup.sh`)

**Purpose:** Creates a compressed backup of the entire shifthandover_v3 application directory.

**Location:** `~/scripts/app_backup.sh`

**Features:**
- Creates tar.gz compressed archive
- Excludes unnecessary files (`__pycache__`, `.git`, `*.pyc`, `venv`, `.env`)
- Automatic cleanup of backups older than 7 days
- Logs all operations to backup.log

**Output:** `~/backups/app/app_backup_YYYY-MM-DD_HH-MM-SS.tar.gz`

### 2. Database Backup (`db_backup.sh`)

**Purpose:** Creates a compressed SQL dump of the MySQL database.

**Location:** `~/scripts/db_backup.sh`

**Features:**
- Uses mysqldump with `--single-transaction` for consistent backups
- Includes routines and triggers
- Gzip compression for space efficiency
- Automatic cleanup of backups older than 7 days
- Logs all operations to backup.log

**Output:** `~/backups/db/db_backup_YYYY-MM-DD_HH-MM-SS.sql.gz`

### 3. Backup Status (`backup_status.sh`)

**Purpose:** Displays a comprehensive status report of all backups.

**Location:** `~/scripts/backup_status.sh`

**Shows:**
- List of all application backups with sizes
- List of all database backups with sizes
- Total disk usage
- Recent log entries

## Cron Schedule

All times are in **IST (Indian Standard Time)**. Server runs in UTC.

| Backup Type | IST Time | UTC Time | Frequency |
|-------------|----------|----------|-----------|
| Database | 8:00 AM | 2:30 AM | Daily |
| Database | 2:00 PM | 8:30 AM | Daily |
| Database | 10:00 PM | 4:30 PM | Daily |
| Application | 12:00 AM (midnight) | 6:30 PM | Daily |
| Status Report | Sunday 1:00 AM | Saturday 7:30 PM | Weekly |

### Crontab Configuration

```cron
# Database Backup - 3 times daily at 8AM, 2PM, 10PM IST
30 2 * * * /home/shifthandoversajid/scripts/db_backup.sh >> /home/shifthandoversajid/backups/cron.log 2>&1
30 8 * * * /home/shifthandoversajid/scripts/db_backup.sh >> /home/shifthandoversajid/backups/cron.log 2>&1
30 16 * * * /home/shifthandoversajid/scripts/db_backup.sh >> /home/shifthandoversajid/backups/cron.log 2>&1

# Application Backup - Once daily at midnight IST
30 18 * * * /home/shifthandoversajid/scripts/app_backup.sh >> /home/shifthandoversajid/backups/cron.log 2>&1

# Weekly status report - Sunday 1AM IST
30 19 * * 6 /home/shifthandoversajid/scripts/backup_status.sh >> /home/shifthandoversajid/backups/weekly_status.log 2>&1
```

## Directory Structure

```
~/
├── scripts/
│   ├── app_backup.sh        # Application backup script
│   ├── db_backup.sh         # Database backup script
│   ├── backup_status.sh     # Status report script
│   └── crontab_backup       # Crontab configuration file
│
└── backups/
    ├── app/                 # Application backups
    │   └── app_backup_*.tar.gz
    ├── db/                  # Database backups
    │   └── db_backup_*.sql.gz
    ├── backup.log           # Main backup log
    ├── cron.log            # Cron execution log
    └── weekly_status.log   # Weekly status reports
```

## Retention Policy

- **Retention Period:** 7 days
- **Automatic Cleanup:** Old backups are automatically deleted after 7 days
- **Database Backups per day:** 3 (approximately 21 backups retained)
- **Application Backups per day:** 1 (approximately 7 backups retained)

## Manual Operations

### Run Manual Backup

```bash
# Database backup
~/scripts/db_backup.sh

# Application backup
~/scripts/app_backup.sh
```

### Check Backup Status

```bash
~/scripts/backup_status.sh
```

### View Backup Logs

```bash
# View main backup log
tail -f ~/backups/backup.log

# View cron execution log
tail -f ~/backups/cron.log
```

### Manage Cron Jobs

```bash
# View current cron jobs
crontab -l

# Edit cron jobs
crontab -e

# Reinstall cron jobs from file
crontab ~/scripts/crontab_backup
```

## Restore Procedures

### Restore Database

```bash
# Uncompress and restore
gunzip -c ~/backups/db/db_backup_YYYY-MM-DD_HH-MM-SS.sql.gz | \
  docker exec -i shift-db mysql -uroot -prootpassword shifthandover
```

### Restore Application

```bash
# Stop the application
docker stop shift-web

# Backup current application (optional)
mv ~/shifthandover_v3 ~/shifthandover_v3_old

# Extract backup
cd ~/
tar -xzf ~/backups/app/app_backup_YYYY-MM-DD_HH-MM-SS.tar.gz

# Restart the application
docker restart shift-web
```

## Monitoring

### Check Cron Service Status

```bash
sudo systemctl status cron
```

### Verify Recent Backups

```bash
# Check if today's backups exist
ls -la ~/backups/db/db_backup_$(date +%Y-%m-%d)*.sql.gz
ls -la ~/backups/app/app_backup_$(date +%Y-%m-%d)*.tar.gz
```

## Troubleshooting

### Backup Failed

1. Check the backup log:
   ```bash
   tail -50 ~/backups/backup.log
   ```

2. Check disk space:
   ```bash
   df -h
   ```

3. Verify database container is running:
   ```bash
   docker ps | grep shift-db
   ```

### Cron Not Running

1. Check cron service:
   ```bash
   sudo systemctl status cron
   ```

2. Restart cron if needed:
   ```bash
   sudo systemctl restart cron
   ```

3. Check cron log:
   ```bash
   grep CRON /var/log/syslog | tail -20
   ```

## Configuration

### Database Connection

| Parameter | Value |
|-----------|-------|
| Container | shift-db |
| Database | shifthandover |
| User | root |
| Password | rootpassword |

### Backup Settings

| Setting | Value |
|---------|-------|
| Retention Days | 7 |
| App Backup Frequency | Once daily |
| DB Backup Frequency | 3 times daily |
| Compression | gzip |

---

*Last Updated: December 25, 2025*







