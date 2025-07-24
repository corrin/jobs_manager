#!/bin/bash
set -euo pipefail

detect_environment() {
    case "$(hostname)" in
        "msm")
            ENV="PROD"; PROJECT_DIR="/home/django_user/jobs_manager"
            USER_DIR="/home/django_user"; APP_USER="django_user" ;;
        "uat-scheduler")
            ENV="SCHEDULER"; PROJECT_DIR="/opt/workflow_app/jobs_manager"
            USER_DIR="/opt/workflow_app"; APP_USER="ubuntu" ;;
        "uat"|"uat-frontend")
            ENV="UAT"; PROJECT_DIR="/opt/workflow_app/jobs_manager"
            USER_DIR="/opt/workflow_app"; APP_USER="ubuntu" ;;
        *)
            echo "ERROR: Unknown hostname $(hostname)"; exit 1 ;;
    esac
}

create_backup() {
    [ "$ENV" != "PROD" ] && return
    echo "=== Creating backup ==="
    local release_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="/var/backups/jobs_manager/$release_date"

    mkdir -p "$backup_dir"
    tar -zcf "$backup_dir/code_backup.tar.gz" -C "$PROJECT_DIR" . --exclude='gunicorn.sock'
    mysqldump -u root jobs_manager | gzip > "$backup_dir/database_backup.sql.gz"
    rclone copy "$backup_dir" "gdrive:msm_backups/$release_date"
    echo "Backup completed: $backup_dir"
}

deploy_application() {
    echo "=== Deploying application ==="
    cd "$PROJECT_DIR"

    # Determine virtual environment path based on environment
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "ERROR: No virtual environment found (.venv or venv)"
        exit 1
    fi
    git pull
    npm install
    poetry install
    python manage.py migrate
    python manage.py collectstatic --clear --noinput
}

build_frontend() {
    [ "$ENV" = "SCHEDULER" ] && return
    echo "=== Building Vue.js frontend ==="
    cd "$USER_DIR/jobs_manager_front"
    npm install
    npm run build
}

validate_prerequisites() {
    echo "=== Validating prerequisites ==="

    # Check required commands
    for cmd in git npm poetry python mysqldump; do
        command -v "$cmd" >/dev/null || { echo "ERROR: $cmd not found"; exit 1; }
    done

    # Check rclone only for PROD
    [ "$ENV" = "PROD" ] && { command -v rclone >/dev/null || { echo "ERROR: rclone not found"; exit 1; }; }

    # Check directories exist
    [ -d "$PROJECT_DIR" ] || { echo "ERROR: $PROJECT_DIR not found"; exit 1; }
    [ "$ENV" != "SCHEDULER" ] && [ ! -d "$USER_DIR/jobs_manager_front" ] && { echo "ERROR: $USER_DIR/jobs_manager_front not found"; exit 1; }

    # Check database connectivity
    mysqladmin -u root ping >/dev/null 2>&1 || { echo "ERROR: Cannot connect to MariaDB"; exit 1; }

    # Check backup directory writable (PROD only)
    if [ "$ENV" = "PROD" ]; then
        mkdir -p /var/backups/jobs_manager/test 2>/dev/null || { echo "ERROR: Cannot write to /var/backups/jobs_manager"; exit 1; }
        rmdir /var/backups/jobs_manager/test
    fi

    echo "Prerequisites validated"
}

restart_services() {
    case "$ENV" in
        "PROD") echo "=== Restarting Gunicorn ==="; sudo systemctl restart gunicorn ;;
        "UAT") echo "=== Restarting Gunicorn ==="; sudo systemctl restart gunicorn-uat ;;
        "SCHEDULER") echo "=== Restarting Scheduler ==="; sudo systemctl restart scheduler ;;
    esac
}

# Main execution
detect_environment
validate_prerequisites
echo "=== Deploying to $ENV environment ==="
create_backup
deploy_application
build_frontend
restart_services
echo "Deployment to $ENV environment completed successfully"
