#!/bin/bash
set -euo pipefail

# Detect environment
if [ -d "/home/django_user/jobs_manager" ]; then
    PROJECT_DIR="/home/django_user/jobs_manager"
    USER_DIR="/home/django_user"
    APP_USER="django_user"
    ENV="PROD"
elif [ -d "/opt/workflow_app/jobs_manager" ]; then
    PROJECT_DIR="/opt/workflow_app/jobs_manager"
    USER_DIR="/opt/workflow_app"
    APP_USER="ubuntu"
    # Check if this is scheduler-only machine
    if [ -f "/etc/SCHEDULER_MACHINE" ]; then
        ENV="SCHEDULER"
    else
        ENV="UAT"
    fi
else
    echo "ERROR: Project directory not found"
    exit 1
fi

BACKUP_ROOT="/var/backups/jobs_manager"
RELEASE_DATE=$(date +%Y%m%d_%H%M%S)
DATE_DIR="$BACKUP_ROOT/$RELEASE_DATE"

echo "=== Deploying to $ENV environment ==="

mkdir -p "$DATE_DIR"

echo "=== Backing up code to $DATE_DIR/code_${RELEASE_DATE}.tgz..."
CODE_BACKUP="$DATE_DIR/code_${RELEASE_DATE}.tgz"
tar -zcf "$CODE_BACKUP" \
    -C "$USER_DIR" \
    --exclude='gunicorn.sock' \
    jobs_manager

if [ "$ENV" = "PROD" ]; then
    echo "=== Backing up DB to $DATE_DIR/db_${RELEASE_DATE}.sql.gz..."
    DB_BACKUP="$DATE_DIR/db_${RELEASE_DATE}.sql.gz"
    mysqldump -u root jobs_manager | gzip > "$DB_BACKUP"

    echo "=== Copying backups to Google Drive under msm_backups/$RELEASE_DATE/ …"
    rclone copy "$DATE_DIR" gdrive:msm_backups/"$RELEASE_DATE"
else
    echo "=== Skipping DB backup and Google Drive upload for UAT environment ==="
fi

echo "=== Deploying (su to $APP_USER)…"
su - "$APP_USER" -c "$PROJECT_DIR/scripts/deploy_app.sh"

if [ "$ENV" = "PROD" ]; then
    echo "=== Restarting Gunicorn…"
    systemctl restart gunicorn
elif [ "$ENV" = "UAT" ]; then
    echo "=== Restarting Gunicorn…"
    systemctl restart gunicorn
elif [ "$ENV" = "SCHEDULER" ]; then
    echo "=== Restarting Scheduler…"
    systemctl restart scheduler
fi
