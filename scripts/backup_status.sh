#!/bin/bash
# Backup Status Script
# Shows the status of all backups

BACKUP_BASE="/home/shifthandoversajid/backups"

echo "============================================"
echo "        BACKUP STATUS REPORT"
echo "        $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Application Backups
echo "📁 APPLICATION BACKUPS:"
echo "------------------------"
if [ -d "$BACKUP_BASE/app" ]; then
    APP_COUNT=$(ls -1 $BACKUP_BASE/app/app_backup_*.tar.gz 2>/dev/null | wc -l)
    echo "Total backups: $APP_COUNT"
    if [ $APP_COUNT -gt 0 ]; then
        echo "Latest backup:"
        ls -lh $BACKUP_BASE/app/app_backup_*.tar.gz 2>/dev/null | tail -1
        echo ""
        echo "All backups:"
        ls -lh $BACKUP_BASE/app/app_backup_*.tar.gz 2>/dev/null
    fi
else
    echo "No application backups found."
fi
echo ""

# Database Backups
echo "🗄️  DATABASE BACKUPS:"
echo "------------------------"
if [ -d "$BACKUP_BASE/db" ]; then
    DB_COUNT=$(ls -1 $BACKUP_BASE/db/db_backup_*.sql.gz 2>/dev/null | wc -l)
    echo "Total backups: $DB_COUNT"
    if [ $DB_COUNT -gt 0 ]; then
        echo "Latest backup:"
        ls -lh $BACKUP_BASE/db/db_backup_*.sql.gz 2>/dev/null | tail -1
        echo ""
        echo "All backups:"
        ls -lh $BACKUP_BASE/db/db_backup_*.sql.gz 2>/dev/null
    fi
else
    echo "No database backups found."
fi
echo ""

# Disk Usage
echo "💾 DISK USAGE:"
echo "------------------------"
du -sh $BACKUP_BASE/app 2>/dev/null || echo "App backup dir: Not found"
du -sh $BACKUP_BASE/db 2>/dev/null || echo "DB backup dir: Not found"
du -sh $BACKUP_BASE 2>/dev/null || echo "Total backup dir: Not found"
echo ""

# Recent Log Entries
echo "📋 RECENT LOG ENTRIES:"
echo "------------------------"
if [ -f "$BACKUP_BASE/backup.log" ]; then
    tail -20 $BACKUP_BASE/backup.log
else
    echo "No backup log found."
fi
echo ""
echo "============================================"












