#!/bin/bash
# Database Backup Script
# Runs 3 times daily to backup the MySQL database

# Configuration
DB_CONTAINER="shift-db"
DB_NAME="shifthandover"
DB_USER="root"
DB_PASS="rootpassword"
BACKUP_DIR="/home/shifthandoversajid/backups/db"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="db_backup_${TIMESTAMP}.sql.gz"
LOG_FILE="/home/shifthandoversajid/backups/backup.log"
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting database backup..." >> $LOG_FILE

# Create database backup using mysqldump inside docker container
docker exec $DB_CONTAINER mysqldump -u$DB_USER -p$DB_PASS \
    --single-transaction \
    --routines \
    --triggers \
    --databases $DB_NAME | gzip > $BACKUP_DIR/$BACKUP_FILE

if [ $? -eq 0 ] && [ -s $BACKUP_DIR/$BACKUP_FILE ]; then
    BACKUP_SIZE=$(du -h $BACKUP_DIR/$BACKUP_FILE | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database backup completed: $BACKUP_FILE (Size: $BACKUP_SIZE)" >> $LOG_FILE
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Database backup failed!" >> $LOG_FILE
    # Remove empty/failed backup file
    rm -f $BACKUP_DIR/$BACKUP_FILE
    exit 1
fi

# Cleanup old backups (keep only last 7 days)
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned up backups older than $RETENTION_DAYS days" >> $LOG_FILE

# Count remaining backups
BACKUP_COUNT=$(ls -1 $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database backup process completed. Total backups: $BACKUP_COUNT" >> $LOG_FILE
echo "----------------------------------------" >> $LOG_FILE




