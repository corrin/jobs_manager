#!/bin/bash

# Shared deployment script for both GitHub Actions CD and machine startup
# Usage: ./deploy_machine.sh [branch_name] [machine_type]
#
# Arguments:
#   branch_name: Git branch to deploy (default: main)
#   machine_type: scheduler|frontend (default: auto-detect)

set -e  # Exit on any error

# Configuration
# Always deploy main branch (CD only triggers on main)
MACHINE_TYPE=${2:-"auto"}
PROJECT_PATH="/opt/workflow_app/jobs_manager"
LOG_FILE="$PROJECT_PATH/logs/deploy_machine.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

# Auto-detect machine type if not specified
detect_machine_type() {
    if systemctl is-active --quiet scheduler 2>/dev/null; then
        echo "scheduler"
    else
        echo "frontend"
    fi
}

# Validate environment
validate_environment() {
    log "Validating deployment environment..."

    if [ ! -d "$PROJECT_PATH" ]; then
        log_error "Project directory $PROJECT_PATH does not exist"
        exit 1
    fi

    if [ "$MACHINE_TYPE" = "auto" ]; then
        MACHINE_TYPE=$(detect_machine_type)
        log "Auto-detected machine type: $MACHINE_TYPE"
    fi

    log_success "Environment validation complete"
}

# Update code from git
update_code() {
    log "Updating code from git (branch: main)..."

    cd "$PROJECT_PATH"

    # Clean any local changes to tracked files
    git reset --hard

    # Ensure we're on main branch
    git checkout main

    # Pull latest changes and force sync with remote
    git fetch origin main
    git reset --hard origin/main

    # Ensure deploy script has execute permissions
    chmod +x "$PROJECT_PATH/scripts/deploy_machine.sh"

    log_success "Code update complete"
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."

    cd "$PROJECT_PATH"
    source .venv/bin/activate

    # Python dependencies
    poetry install

    # Node dependencies
    npm install

    log_success "Dependencies installation complete"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."

    cd "$PROJECT_PATH"
    source .venv/bin/activate

    python manage.py migrate

    log_success "Database migrations complete"
}

# Collect static files
collect_static() {
    log "Collecting static files..."

    cd "$PROJECT_PATH"
    source .venv/bin/activate

    python manage.py collectstatic --noinput

    log_success "Static files collection complete"
}

# Restart services based on machine type
restart_services() {
    log "Restarting services for $MACHINE_TYPE machine..."

    case $MACHINE_TYPE in
        "scheduler")
            sudo systemctl restart scheduler
            sudo systemctl reload nginx
            log_success "Scheduler machine services restarted"
            ;;
        "frontend")
            sudo systemctl restart gunicorn-uat
            sudo systemctl reload nginx
            log_success "Frontend/Backend machine services restarted"
            ;;
        *)
            log_error "Unknown machine type: $MACHINE_TYPE"
            exit 1
            ;;
    esac
}

# Main deployment function
main() {
    log "Starting deployment process..."
    log "Branch: main"
    log "Machine Type: $MACHINE_TYPE"
    log "Project Path: $PROJECT_PATH"

    validate_environment
    update_code
    install_dependencies
    run_migrations
    collect_static
    restart_services

    log_success "Deployment completed successfully!"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"
