#!/bin/bash
set -euo pipefail

BACKUP_ROOT="/var/backups/jobs_manager"
RELEASE_DATE=$(date +%Y%m%d_%H%M%S)
DATE_DIR="$BACKUP_ROOT/$RELEASE_DATE"
PROJECT_DIR="/home/django_user/jobs_manager"

mkdir -p "$DATE_DIR"

echo "=== Backing up code to $DATE_DIR/code_${RELEASE_DATE}.tgz..."
CODE_BACKUP="$DATE_DIR/code_${RELEASE_DATE}.tgz"
tar -zcf "$CODE_BACKUP" \
    -C /home/django_user \
    --exclude='gunicorn.sock' \
    jobs_manager

echo "=== Backing up DB to $DATE_DIR/db_${RELEASE_DATE}.sql.gz..."
DB_BACKUP="$DATE_DIR/db_${RELEASE_DATE}.sql.gz"
mysqldump -u root jobs_manager | gzip > "$DB_BACKUP"

echo "=== Copying backups to Google Drive under msm_backups/$RELEASE_DATE/ …"
rclone copy "$DATE_DIR" gdrive:msm_backups/"$RELEASE_DATE"

echo "=== Deploying (su to django_user)…"
su - django_user -c "/usr/local/bin/deploy_app.sh"

echo "=== Restarting Gunicorn…"
systemctl restart gunicorn

sleep 10

echo "=== Restarting Xero Sync"
systemctl restart xero-sync.service
echo "=== Deployment complete. Verify the site is running correctly! ==="
