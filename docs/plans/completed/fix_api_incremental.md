# Incremental Job Files API Fix

## Problem
- 6 operationId collisions in OpenAPI schema
- Multiple URL patterns causing duplicates
- Job files has TWO upload views

## Incremental Steps (Test After Each)

### Step 1: Remove Duplicate Upload View
**Change:** Delete `JobFileUploadView` (redundant with `JobFileView.post()`)

**Files:**
- Delete: `apps/job/views/job_file_upload.py`
- Edit: `apps/job/urls_rest.py` - remove line 203 (`rest/jobs/files/upload/`)
- Edit: `apps/job/urls_rest.py` - remove import

**Test:**
```bash
python manage.py spectacular --file /tmp/schema.yml
grep "uploadJobFiles" /tmp/schema.yml
# Should show one fewer collision
```

**Expected result:** 5 collisions instead of 6

---

### Step 2: Consolidate URL Patterns (Fix Main Problem)
**Change:** Remove duplicate URL patterns that map to same view

**Problem:** Same `JobFileView` mapped to 3 URLs causes 3x `retrieveJobFilesApi`

**File:** `apps/job/urls_rest.py`

Remove these duplicate patterns:
- Line 215: `"rest/jobs/files/"` (ambiguous - no identifier)
- Line 217: `"rest/jobs/files/<path:file_path>/"` (ambiguous - path vs ID)
- Line 222: `"rest/jobs/files/<int:file_path>/"` (confusing - file_path parameter used for delete)

Keep only:
- `"rest/jobs/files/<int:job_number>/"` for list/upload/update operations
- `"rest/jobs/files/<uuid:file_id>/thumbnail/"` for thumbnails

**Test:**
```bash
python manage.py spectacular --file /tmp/schema.yml
# Should show 0 warnings
```

**Expected result:** Zero operationId collisions

---

### Step 3: Split JobFileView into Two Views
**Change:** Separate collection operations from resource operations

**New file:** `apps/job/views/job_file_views_split.py`

Create two views:
- `JobFilesListView` - handles GET with job_number
- `JobFileDetailView` - handles GET/PUT/DELETE with file_id

**Test:**
```bash
python manage.py test apps.job.tests.test_job_files
```

---

### Step 4: Change URL Structure (Breaking)
**Change:** Move from `int:job_number` to `uuid:job_id`

Update all URLs to use `uuid:job_id` for consistency

**Test:**
```bash
# Manual curl tests for each operation
```

---

### Step 5: Write Frontend Migration Guide
**Change:** Document what changed for frontend

**File:** `docs/api/job_files_api_migration.md`

---

## Current Status
- [ ] Step 1: Remove duplicate upload view (reduces collisions from 6 to 5)
- [ ] Step 2: Consolidate URL patterns (fixes remaining collisions)
- [ ] Step 3: Split views (better organization)
- [ ] Step 4: Change URL structure to uuid:job_id (consistency)
- [ ] Step 5: Write migration guide (documentation)
