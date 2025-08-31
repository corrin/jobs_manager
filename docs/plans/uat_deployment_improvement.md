(venv) ubuntu@uat:/opt/workflow_app/jobs_manager$ cat docs/plans/uat_deployment_improvement.md
# UAT Deployment Improvement Plan

## Overview
This document outlines the improvements needed for the UAT deployment process to handle the dual-machine architecture properly, where the scheduler runs 24/7 and the frontend/main UAT runs on-demand.

## Current Issues
1. **Parallel execution**: Both machines deploy simultaneously, potentially causing database migration conflicts
2. **No startup sync**: Main UAT doesn't auto-update when booted
3. **Deployment happens even if scheduler fails**: Frontend deploys with `continue-on-error: true` regardless of scheduler status

## Proposed Solution

### 1. Sequential Deployment in GitHub Actions
- Deploy to scheduler first (always running, critical path)
- **Only deploy to main UAT if scheduler succeeds**
- Remove `continue-on-error: true` between deployment steps
- Keep deployment atomic - scheduler must succeed first

### 2. Add Startup Deployment Service
- Create systemd service that runs on boot for main UAT
- Runs the same `deploy_machine.sh` script
- Ensures machine always runs current version when powered on

## Implementation Steps

### Step 1: Update GitHub Actions Workflow
**File**: `.github/workflows/cd.yml`

**Changes needed**:
- Remove parallel deployment (currently both steps run simultaneously)
- Deploy scheduler first and wait for completion
- Only deploy to frontend if scheduler deployment succeeds
- Keep `continue-on-error: true` ONLY for handling when frontend machine is offline (not for ignoring scheduler failures)

**Key logic**:
```yaml
- name: Deploy to Scheduler Machine
  # Deploy to scheduler first - this MUST succeed
  # Run migrations here since scheduler is always online

- name: Deploy to Frontend/Backend Machine
  # Only runs if scheduler deployment succeeded
  continue-on-error: true  # Only for when machine is offline, not for deployment failures
  # Skip migrations since scheduler already ran them
```

### Step 2: Create Startup Deployment Service
**File**: `scripts/deploy-on-startup.service`

**Purpose**: Systemd service that runs once on boot to sync the frontend/main UAT with latest code

**Contents**:
```ini
[Unit]
Description=Deploy latest code on startup
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ubuntu
ExecStart=/opt/workflow_app/jobs_manager/scripts/deploy_machine.sh main frontend
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Installation**:
```bash
# On the frontend/main UAT machine only
sudo cp scripts/deploy-on-startup.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable deploy-on-startup.service
```

### Step 3: Modify deploy_machine.sh (Optional)
The existing `deploy_machine.sh` script should work as-is, but consider:
- Add a check to skip migrations on frontend if they were recently run (to avoid duplicate migration attempts)
- Add better logging to identify which machine is deploying

## Testing Plan

### Test Scenario 1: Both Machines Online
1. Push code to main branch
2. Verify scheduler deploys first
3. Verify frontend deploys only after scheduler succeeds
4. Verify migrations run only once (on scheduler)

### Test Scenario 2: Frontend Offline
1. Turn off frontend machine
2. Push code to main branch
3. Verify scheduler deploys successfully
4. Verify GitHub Actions shows warning (not error) for frontend
5. Boot frontend machine
6. Verify startup service runs and syncs code

### Test Scenario 3: Scheduler Deployment Fails
1. Introduce a deliberate error (e.g., bad migration)
2. Push code to main branch
3. Verify scheduler deployment fails
4. Verify frontend deployment is NOT attempted
5. Verify GitHub Actions fails the entire workflow

### Test Scenario 4: Frontend Boot After Multiple Deployments
1. Keep frontend offline
2. Push multiple deployments
3. Boot frontend
4. Verify it pulls latest main branch (not an intermediate state)

## Expected Outcomes
- **No migration conflicts**: Sequential deployment ensures migrations run only once
- **Scheduler priority**: Critical 24/7 service always deploys first
- **Auto-sync on boot**: Frontend always runs current code when powered on
- **Clear failure modes**: Deployment fails fast if scheduler has issues
- **Resilient to offline machines**: Frontend being offline doesn't break deployments

## Rollback Plan
If issues arise:
1. Revert `.github/workflows/cd.yml` to previous version
2. Disable `deploy-on-startup.service` on frontend
3. Return to manual deployment process

## Timeline
- **Step 1**: 30 minutes (update GitHub Actions)
- **Step 2**: 30 minutes (create and install startup service)
- **Testing**: 1-2 hours (run through all scenarios)
- **Total**: ~3 hours

## Notes for Implementation
- Ensure GitHub secrets are correctly configured for both machines
- The `deploy_machine.sh` script already handles machine type detection
- Consider adding Slack/email notifications for deployment status
