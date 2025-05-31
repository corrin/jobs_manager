#!/bin/bash
BACKUP_DIR="/var/backups/mysql"
mkdir -p $BACKUP_DIR
TODAY=$(date +%Y%m%d)
MONTH=$(date +%Y%m)

# Daily backup with compression
mysqldump -u root jobs_manager | gzip > $BACKUP_DIR/daily_$TODAY.sql.gz

# Monthly backup on 1st
if [ $(date +%d) = "01" ]; then
    cp $BACKUP_DIR/daily_$TODAY.sql.gz $BACKUP_DIR/monthly_$MONTH.sql.gz
fi

# Sync to Google Drive
rclone copy $BACKUP_DIR gdrive:msm_backups/
