# Deployment Script Consolidation Plan

## Objective
Replace the existing deployment scripts (`deploy_app.sh`, `deploy_release.sh`, and `deploy_machine.sh`) with a single, reliable deployment script that runs as the application user.

## Current State Analysis

### Existing Scripts
1. **`deploy_app.sh`** - User-level deployment (incomplete - missing service restarts)
2. **`deploy_release.sh`** - Root-level orchestrator with backups and service management
3. **`deploy_machine.sh`** - Full-featured deployment script for UAT environments with proper logging and service management

### Problems
- Three scripts with overlapping functionality
- Different approaches to environment detection (directory paths vs service detection)
- Inconsistent service restart patterns
- `deploy_app.sh` is incomplete (no service restarts)

## Proposed Solution

### Single Script Architecture
Create `scripts/deploy.sh` that:
- Runs entirely as application user
- Uses sudo for systemctl commands only
- Handles all environments (PROD/UAT/SCHEDULER)
- Includes all deployment steps in one place

## Implementation Plan

### Step 1: Sudoers Configuration

Add to `/etc/sudoers` using `visudo`:

**Production server** (`/home/django_user/jobs_manager`):
```
django_user ALL=(ALL) NOPASSWD: /bin/systemctl restart gunicorn-prod
```

**UAT server** (`/opt/workflow_app/jobs_manager`):
```
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart gunicorn-uat
```

**Scheduler server** (`/opt/workflow_app/jobs_manager` + `/etc/SCHEDULER_MACHINE`):
```
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart scheduler
```

### Step 2: Create `scripts/deploy.sh`

#### Header and Error Handling
```bash
#!/bin/bash
set -euo pipefail
```

#### Environment Detection
Use hostname-based detection instead of directory paths:
```bash
HOSTNAME=$(hostname)
case "$HOSTNAME" in
    "msm")
        ENV="PROD"
        PROJECT_DIR="/home/django_user/jobs_manager"
        USER_DIR="/home/django_user"
        APP_USER="django_user"
        ;;
    "uat-scheduler")
        ENV="SCHEDULER"
        PROJECT_DIR="/opt/workflow_app/jobs_manager"
        USER_DIR="/opt/workflow_app"
        APP_USER="ubuntu"
        ;;
    "uat"|"uat-frontend")
        ENV="UAT"
        PROJECT_DIR="/opt/workflow_app/jobs_manager"
        USER_DIR="/opt/workflow_app"
        APP_USER="ubuntu"
        ;;
    *)
        echo "ERROR: Unknown hostname $HOSTNAME"
        exit 1
        ;;
esac
```

#### Backup Section (PROD Only)
Copy backup logic from `deploy_release.sh` lines 25-51:
- Create timestamped backup directory: `/var/backups/jobs_manager/$RELEASE_DATE`
- Code backup: `tar -zcf` with `--exclude='gunicorn.sock'`
- Database backup: `mysqldump -u root jobs_manager | gzip`
- Google Drive upload: `rclone copy` to `gdrive:msm_backups/`

**Note**: May need to adjust backup directory permissions or location if `/var/backups` is not writable by app user.

#### Core Deployment Steps
Replace the `su` call to `deploy_app.sh` with inline deployment:
```bash
echo "=== Deploying application ==="
cd "$PROJECT_DIR"
source .venv/bin/activate
git pull
npm install
poetry install
python manage.py migrate
python manage.py collectstatic --clear --noinput
```

#### Frontend Build (Non-SCHEDULER Only)
Copy from `deploy_release.sh` lines 56-61:
```bash
if [ "$ENV" != "SCHEDULER" ]; then
    echo "=== Building Vue.js frontend ==="
    cd "$USER_DIR/jobs_manager_front"
    npm install
    npm run build
fi
```

#### Service Restart
Replace `systemctl` calls with `sudo systemctl`:
```bash
if [ "$ENV" = "PROD" ]; then
    echo "=== Restarting Gunicorn ==="
    sudo systemctl restart gunicorn-prod
elif [ "$ENV" = "UAT" ]; then
    echo "=== Restarting Gunicorn ==="
    sudo systemctl restart gunicorn-uat
elif [ "$ENV" = "SCHEDULER" ]; then
    echo "=== Restarting Scheduler ==="
    sudo systemctl restart scheduler
fi
```

#### Success Message
```bash
echo "Deployment to $ENV environment completed successfully"
```

### Step 3: Testing Requirements

Before deploying to production, test on each environment:

1. **Verify sudo permissions**:
   ```bash
   sudo systemctl restart gunicorn-prod  # On PROD
   sudo systemctl restart gunicorn-uat   # On UAT
   sudo systemctl restart scheduler      # On SCHEDULER
   ```

2. **Test backup operations** (PROD only):
   - Verify `/var/backups/jobs_manager` is writable by `django_user`
   - Test `mysqldump` command works as `django_user`
   - Test `rclone` configuration is accessible

3. **Test full deployment**:
   - Run `./scripts/deploy.sh` on each environment
   - Verify services restart successfully
   - Verify application is accessible
   - Verify no permission errors

### Step 4: File Cleanup

After successful testing:
1. Delete `scripts/deploy_app.sh`
2. Delete `scripts/deploy_release.sh`
3. Delete `scripts/deploy_machine.sh`

## Risk Mitigation

### Backup Strategy
- Keep old scripts in version control until new script is proven
- Test thoroughly on UAT before PROD deployment
- Have rollback plan ready

### Permission Issues
If backup directory permissions are problematic:
- Option 1: Change backup location to user-writable directory
- Option 2: Use `sudo` for backup operations only
- Option 3: Create backup directory with proper permissions

### Service Restart Failures
- Ensure exact service names match existing systemctl services
- Test sudo permissions before full deployment
- Have manual restart procedures documented

## Success Criteria

1. **Single script** handles all environments
2. **No user switching** - runs entirely as app user
3. **All deployment steps** work correctly
4. **Service restarts** function properly
5. **Backups work** (PROD only)
6. **Zero downtime** deployments
7. **Simplified maintenance** - one script to debug/modify

## Timeline

- **Phase 1**: Update sudoers configuration (1 hour)
- **Phase 2**: Create and test new script (2 hours)
- **Phase 3**: Production validation (1 hour)
- **Phase 4**: Cleanup old scripts (15 minutes)

**Total estimated time**: 4.25 hours

## Approval Required

This plan requires approval before implementation due to:
- System configuration changes (sudoers)
- Production deployment script changes
- File deletions

Once approved, implementation will proceed step-by-step with testing at each phase.
