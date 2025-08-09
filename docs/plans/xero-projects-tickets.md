# Xero Projects Implementation Tickets

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

## Core Sync Infrastructure

### Ticket 3: Xero Projects API Integration
- Add Projects API calls to `apps/workflow/api/xero/xero.py`
- Implement `get_projects`, `create_project`, `update_project`
- Implement bulk time/expense entry operations
- Test with Xero sandbox

### Ticket 4: Projects Transform Function
- Create `transform_project()` function in sync.py
- Map Xero project fields to Job fields (including status mapping)
- Handle estimate mapping from `latest_estimate`
- Add error handling

### Ticket 5: Projects ENTITY_CONFIG
- Add projects to `ENTITY_CONFIGS` in sync.py
- Test projects sync in scheduled sync process

## Push Sync (Our System → Xero)

### Ticket 6: Job to Xero Push Function
- Create `sync_job_to_xero(job)` function
- Single API call per job with bulk time/expense data
- Map `kind='time'` → time entries, all others → expenses
- Track synced CostLines with Xero IDs

### Ticket 7: Sync Trigger Integration
- Add sync trigger on job save (edit button)
- Add sync trigger on archive status change
- Add "Sync Now" UI button
- Integrate with hourly scheduled sync

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
