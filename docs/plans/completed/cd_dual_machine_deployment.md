# CD Dual Machine Deployment Plan

> **Note**: The `deploy_machine.sh` script created by this plan has since been
> consolidated into `scripts/deploy.sh` which handles all environments
> (PROD, UAT, SCHEDULER). See `docs/plans/completed/deployment_consolidation.md`.

## Current State

- Single machine CD deployment via GitHub Actions
- UAT environment now split into two machines:
  - **Scheduler machine**: Always running
  - **Frontend/Backend machine**: Usually switched off

## Goal Architecture

### Optimistic CD Pipeline (GitHub Actions)

When PR merged to `main`:

1. **Try to deploy to both machines simultaneously**
2. **Continue if one machine is offline** (don't fail entire deployment)
3. **Log which machines were successfully updated**
4. **Notify of any offline machines**

### Pessimistic Startup Process

When machine boots:

1. **Run same deployment process** as CD pipeline
2. **Pull latest main branch**
3. **Install dependencies, run migrations, restart services**
4. **Ensures machine "catches up" to current deployment state**

## Implementation Plan

### 1. GitHub Actions Workflow Changes

- **Add new secrets** for second machine:
  - `SCHEDULER_HOST` / `SCHEDULER_USER`
  - `FRONTEND_HOST` / `FRONTEND_USER`
- **Modify workflow** to deploy to both machines with error handling
- **Use `continue-on-error: true`** for frontend/backend deployment
- **Add logging** for deployment success/failure per machine

### 2. Create Systemd Scheduler Service

Create proper systemd service for the scheduler:

- **Replace manual `python manage.py run_scheduler`**
- **Auto-start on boot and restart on failure**
- **Proper logging and service management**
- **Enable scheduler restart in deployment**

### 3. Shared Deployment Script

Create `scripts/deploy_machine.sh` that both CD and startup can use:

- **Idempotent operations** (safe to run multiple times)
- **Git pull latest main**
- **Poetry + npm install**
- **Run migrations**
- **Collect static files**
- **Restart services** (gunicorn, scheduler, nginx)

### 4. Systemd Startup Service

Create service that runs on boot:

- **Calls shared deployment script**
- **Runs once on startup**
- **Logs to systemd journal**
- **Handles failures gracefully**

### 5. Machine-Specific Configurations

- **Scheduler machine**: Runs scheduler service
- **Frontend/Backend machine**: Runs gunicorn + nginx, no scheduler
- **Both**: Run deployment script with appropriate service restarts

## Benefits

- **Resilient**: Deployment succeeds even if one machine offline
- **Consistent**: Same deployment process for CD and startup
- **Automated**: No manual intervention needed when machines boot
- **Visible**: Clear logging of which machines were updated

## Testing Strategy

1. **Both machines online**: Verify both get deployed
2. **Frontend/Backend offline**: Verify scheduler deploys, frontend skipped
3. **Scheduler offline**: Verify frontend deploys, scheduler skipped
4. **Machine startup**: Verify startup service catches up to latest deployment
5. **Deployment idempotency**: Verify running deployment twice is safe

## Files to Modify/Create

- `.github/workflows/cd.yml` - Update for dual machine deployment
- `scripts/scheduler.service` - New systemd service for scheduler
- `scripts/deploy_machine.sh` - Shared deployment logic
- `systemd/deploy-on-startup.service` - Startup deployment service
- GitHub repository secrets - Add new machine credentials
