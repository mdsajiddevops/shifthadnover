#!/bin/bash
# Application Backup Script
# Runs once daily to backup the shifthandover_v3 application

# Configuration
APP_DIR="/home/shifthandoversajid/shifthandover_v3"
BACKUP_DIR="/home/shifthandoversajid/backups/app"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="app_backup_${TIMESTAMP}.tar.gz"
LOG_FILE="/home/shifthandoversajid/backups/backup.log"
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting application backup..." >> $LOG_FILE

# Create compressed backup (excluding unnecessary files)
cd /home/shifthandoversajid
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    --exclude='shifthandover_v3/__pycache__' \
    --exclude='shifthandover_v3/.git' \
    --exclude='shifthandover_v3/*.pyc' \
    --exclude='shifthandover_v3/venv' \
    --exclude='shifthandover_v3/.env' \
    shifthandover_v3

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h $BACKUP_DIR/$BACKUP_FILE | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Application backup completed: $BACKUP_FILE (Size: $BACKUP_SIZE)" >> $LOG_FILE
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Application backup failed!" >> $LOG_FILE
    exit 1
fi

# Cleanup old backups (keep only last 7 days)
find $BACKUP_DIR -name "app_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned up backups older than $RETENTION_DAYS days" >> $LOG_FILE

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Application backup process completed." >> $LOG_FILE
echo "----------------------------------------" >> $LOG_FILE






