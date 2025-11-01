# Seed Xero from Database - Implementation Plan

## Overview

Create a management command to seed Xero development tenant with database clients and jobs. This is needed after production database restore to populate Xero with all contacts and projects for realistic development testing.

## Problem Statement

After restoring production database to development:

1. Clients have invalid `xero_contact_id` values (from production Xero tenant)
2. Jobs cannot sync to Xero Projects because contacts don't exist
3. Need to populate development Xero tenant with all necessary data

## Architecture Requirements

- **Management Command**: Pure orchestration and UI feedback
- **Sync Module**: All Xero API logic and business rules
- **Separation of Concerns**: No Xero imports in management commands
- **Crash Recovery**: Use existing database fields for progress tracking

## Implementation Tickets

### Ticket 1: Move Xero API Functions to Sync Module ✅

**File:** `apps/workflow/api/xero/sync.py`

**Add new functions:**

```python
def get_all_xero_contacts():
    """Fetch all contacts from Xero (including archived)"""
    # Move logic from management command
    # Return list of {'name': str, 'contact_id': str}

def create_client_contact_in_xero(client):
    """Create a single client as Xero contact"""
    # Move logic from management command
    # Use existing sync patterns (error handling, rate limiting)
    # Return True/False for success
```

**Requirements:**

- Follow existing sync.py patterns for error handling
- Use existing `SLEEP_TIME` rate limiting
- Use existing `persist_app_error()` for errors
- Use existing logging patterns

### Ticket 2: Create Bulk Sync Functions ✅

**File:** `apps/workflow/api/xero/sync.py`

**Add bulk processing functions:**

```python
def seed_clients_to_xero(clients):
    """Bulk process clients: link existing contacts + create missing ones"""
    # Get all existing Xero contacts (one API call)
    # For each client: link if exists, create if missing
    # Return dict: {'linked': count, 'created': count, 'failed': []}

def seed_jobs_to_xero(jobs):
    """Bulk process jobs: create Xero projects"""
    # Use existing sync_job_to_xero() for each job
    # Return dict: {'created': count, 'failed': []}
```

**Requirements:**

- Minimize API calls (fetch all contacts once)
- Handle individual failures gracefully
- Return structured results for reporting
- Use existing `sync_job_to_xero()` for consistency

### Ticket 3: Refactor Management Command ✅

**File:** `apps/workflow/management/commands/seed_xero_from_database.py`

**Remove:**

- All Xero imports: `AccountingApi`, `api_client`, `get_tenant_id`
- All direct API calls
- Unused imports: `transaction`
- Methods: `get_existing_xero_contacts()`, `create_contact_in_xero()`

**Keep:**

- Orchestration: find clients/jobs needing sync
- UI feedback: progress reporting and summaries
- Error handling: catch and report sync failures
- Command line options: `--dry-run`

**New structure:**

```python
def process_contacts(self, dry_run):
    # Find clients needing sync
    # Call sync.seed_clients_to_xero(clients)
    # Report results

def process_projects(self, dry_run):
    # Find jobs needing sync
    # Call sync.seed_jobs_to_xero(jobs)
    # Report results
```

### Ticket 4: Update Backup-Restore Process ✅

**File:** `docs/backup-restore-process.md`

**Replace Step 21:** Instead of `scripts/push_clients_to_xero.py`

```bash
python manage.py seed_xero_from_database
```

**Update expected output** to match new command format

**Benefits:**

- Single command instead of multiple scripts
- Crash-resistant and resumable
- Proper separation of concerns
- Consistent with existing codebase patterns

## Success Criteria

- [x] Management command has no direct Xero imports
- [x] All Xero logic is in sync.py module
- [x] Command handles crashes gracefully (resumable)
- [x] Bulk operations minimize API calls
- [x] Existing contacts are linked, missing ones created
- [x] All jobs with valid contacts get Xero project IDs
- [x] Backup-restore process updated with new command

## Testing

1. **Dry run**: Verify correct counts without changes
2. **Partial run**: Test crash recovery by interrupting
3. **Full run**: Complete seed operation
4. **Verification**: All clients have `xero_contact_id`, all jobs have `xero_project_id`
5. **Xero Projects sync test**: Original failing sync should now work
