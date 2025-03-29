#!/bin/bash
set -euo pipefail

BACKUP_ROOT="/var/backups/jobs_manager"
RELEASE_DATE=$(date +%Y%m%d_%H%M%S)
CODE_BACKUP="$BACKUP_ROOT/code_${RELEASE_DATE}.tgz"
DB_BACKUP="$BACKUP_ROOT/db_${RELEASE_DATE}.sql.gz"
PROJECT_DIR="/home/django_user/jobs_manager"

mkdir -p "$BACKUP_ROOT"

echo "=== Backing up code to $CODE_BACKUP..."
tar -zcf "$CODE_BACKUP" \
    -C /home/django_user \
    --exclude='gunicorn.sock' \
    jobs_manager

echo "=== Backing up DB to $DB_BACKUP..."
mysqldump -u root jobs_manager | gzip > "$DB_BACKUP"

echo "=== Copying backups to Google Drive..."
rclone copy "$BACKUP_ROOT" gdrive:msm_backups/

echo "=== Deploying (su to django_user)..."
# This calls the second script as django_user
su - django_user -c "/usr/local/bin/deploy_app.sh"

echo "=== Restarting Gunicorn..."
systemctl restart gunicorn

echo "=== Deployment complete. Verify the site is running correctly!"