#!/bin/bash
set -euo pipefail

# Usage: rollback_release.sh 20250130_221922
# Provide the date/time suffix of the backup folder to restore.

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <BACKUP_TIMESTAMP>"
  echo "Example: $0 20250130_221922"
  exit 1
fi

BACKUP_TIMESTAMP="$1"
BACKUP_ROOT="/var/backups/jobs_manager"
DATE_DIR="$BACKUP_ROOT/$BACKUP_TIMESTAMP"
CODE_BACKUP="$DATE_DIR/code_${BACKUP_TIMESTAMP}.tgz"
DB_BACKUP="$DATE_DIR/db_${BACKUP_TIMESTAMP}.sql.gz"
PROJECT_DIR="/home/django_user/jobs_manager"
SERVICE="gunicorn"  # Adjust if your service name differs

# 1) Ensure backups actually exist
if [[ ! -f "$CODE_BACKUP" ]]; then
  echo "ERROR: Code backup not found: $CODE_BACKUP"
  exit 1
fi
if [[ ! -f "$DB_BACKUP" ]]; then
  echo "ERROR: DB backup not found: $DB_BACKUP"
  exit 1
fi

# 2) Stop Gunicorn
echo "=== Stopping $SERVICE..."
systemctl stop "$SERVICE"

# 3) Remove current code
echo "=== Removing existing code at $PROJECT_DIR..."
rm -rf "$PROJECT_DIR"

# 4) Restore code from tarball
echo "=== Restoring code from $CODE_BACKUP..."
tar -zxf "$CODE_BACKUP" -C /home/django_user
chown -R django_user:django_user "$PROJECT_DIR"

# 5) Restore DB
echo "=== Restoring DB from $DB_BACKUP..."
gunzip < "$DB_BACKUP" | mysql -u root jobs_manager

# 6) Restart Gunicorn
echo "=== Starting $SERVICE..."
systemctl start "$SERVICE"

echo "=== Rollback complete. Verify the site is now running the older version! ==="
