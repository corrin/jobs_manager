# Xero Projects Implementation Tickets

## IMPORTANT GUIDELINES FOR CLAUDE CODE

**NEVER mark tickets as DONE (✅) unless ALL sub-tasks are actually completed and working.**

**Use these status indicators:**
- ✅ = Fully completed and tested
- ❌ = Not done, blocked, or failed
- 🔄 = In progress
- ⏸️ = Paused/waiting

**Always be accurate about what has actually been accomplished vs what has only been partially implemented.**

## Foundation

### Ticket 1: Model Changes
- Add Xero sync fields to Job model (`xero_project_id`, `xero_last_synced`, `xero_last_modified`)
- Add `xero_user_id` field to Staff model
- Add Xero sync fields to CostLine model (`xero_time_id`, `xero_expense_id`, sync timestamps)
- Create and run migrations

### Ticket 2: Invoice Model Refactoring
- Change Invoice.job from OneToOneField to ForeignKey
- Remove Job `invoiced` property, add `fully_invoiced` BooleanField
- Update all code using `job.invoice` to use `job.invoices` pattern
- Update all code using `job.invoiced` to use `job.fully_invoiced`
- Create and run migrations with data population
- in particular, set fully_invoiced to true for all jobs that have an invoice

## Push Sync (Our System → Xero) - PRIORITY

### Ticket 3: Xero Projects API Integration ✅ DONE
- Add Projects API calls to `apps/workflow/api/xero/xero.py`
- Implement `get_projects`, `create_project`, `update_project`
- Implement bulk time/expense entry operations
- Test with Xero sandbox

### Ticket 4: Job to Xero Push Function - IN PROGRESS
- ✅ Create `sync_job_to_xero(job)` function in sync.py
- ✅ Map Job fields to Xero project data (including status mapping)
- ✅ Handle estimate mapping from `latest_estimate`
- ❌ Single API call per job with bulk time/expense data - BLOCKED: missing "projects" scope in token
- ❌ Map `kind='time'` → time entries, all others → expenses - TODO
- ❌ Track synced CostLines with Xero IDs - TODO
- ✅ Add comprehensive error handling

**CRITICAL: Function created but CANNOT actually sync to Xero until token is re-authenticated with "projects" scope**

### Ticket 5: Initial Job Sync & Triggers
- Create management command to sync ALL existing jobs to Xero
- Add sync trigger on job save (edit button)
- Add sync trigger on archive status change
- Add "Sync Now" UI button
- Integrate with hourly scheduled sync
- Batch processing for API rate limits
- Handle all job types including shop jobs

### Ticket 6: Validation & Monitoring
- Validate every job exists as Xero project
- Add sync status tracking to Job model
- Error reporting and retry mechanisms
- Management command to verify sync integrity

## Pull Sync (Xero → Our System) - LATER

### Ticket 7: Projects Transform Function
- Create `transform_project()` function in sync.py
- Map Xero project fields to Job fields (including status mapping)
- Handle estimate mapping from `latest_estimate`
- Add error handling

### Ticket 8: Projects ENTITY_CONFIG
- Add projects to `ENTITY_CONFIGS` in sync.py
- Test projects sync in scheduled sync process

## Bidirectional Sync

### Ticket 8: CostLine to Xero Sync
- Sync individual CostLines to Xero time/expense entries
- Handle staff mapping via `xero_user_id`
- Bulk operations to minimize API calls
- Track sync status on CostLines

### Ticket 9: Xero to CostLine Creation
- Create CostLines from new Xero time/expense entries
- Map Xero time entries → time CostLines
- Map Xero expenses → material/adjust CostLines
- Handle staff mapping and prevent duplicates

## Migration & Deployment

### Ticket 10: Historical Job Sync
- Management command to sync all existing jobs
- Batch processing for API rate limits
- Handle all job types including shop jobs

### Ticket 11: Testing
- Unit tests for sync functions
- Integration tests with Xero sandbox
- Test error scenarios and edge cases

### Ticket 12: Production Deployment
- Update production Xero app with `projects` scope
- Deploy with migrations
- Run historical sync
- Monitor and document
