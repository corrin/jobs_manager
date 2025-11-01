# Plan: Restructure Job File API Endpoints

## Current Problems

1. **TWO upload views** with different operationIds:
   - `JobFileUploadView` → "uploadJobFilesRest"
   - `JobFileView.post()` → "uploadJobFilesApi"

2. **Overlapping URL patterns** causing operationId collisions:
   - `/rest/jobs/files/upload/` (upload endpoint)
   - `/rest/jobs/files/` (base - no identifier)
   - `/rest/jobs/files/<int:job_number>/` (list by job)
   - `/rest/jobs/files/<path:file_path>/` (download by path)
   - `/rest/jobs/files/<int:file_path>/` (delete by ID??)

3. **ONE view class handling MULTIPLE URL patterns with conditional routing:**
   ```python
   def get(self, request, file_path=None, job_number=None):
       if job_number:
           return self._get_by_number(job_number)  # List files
       elif file_path:
           return self._get_by_path(file_path)     # Download file
       else:
           return error                             # Ambiguous
   ```

4. **Inconsistent patterns:**
   - Job number sometimes in URL, sometimes in request body
   - `file_path` param used for both paths and IDs
   - Same view handling different URL patterns

## Target REST Structure

**Core REST Principles:**
1. **Required parameters in URL path, NOT request body** - Identifiers (job_number, file_id) must be in URL
2. **Request body for data only** - Body contains actual data being created/updated, not identifiers
3. **Consistent resource hierarchy** - All file operations under /jobs/{job_number}/files/
4. **No duplicate operations** - One endpoint per operation, no redundant views

### View Class 1: `JobFilesCollectionView`
**URL:** `/job/rest/jobs/{job_id}/files/`
**Responsibility:** Collection operations on a job's files

**Methods:**
```
POST   /job/rest/jobs/{job_id}/files/                      uploadJobFiles
GET    /job/rest/jobs/{job_id}/files/                      listJobFiles
```

### View Class 2: `JobFileDetailView`
**URL:** `/job/rest/jobs/{job_id}/files/{file_id}/`
**Responsibility:** Operations on a specific file resource

**Methods:**
```
GET    /job/rest/jobs/{job_id}/files/{file_id}/            getJobFile
PUT    /job/rest/jobs/{job_id}/files/{file_id}/            updateJobFile
DELETE /job/rest/jobs/{job_id}/files/{file_id}/            deleteJobFile
```

### View Class 3: `JobFileThumbnailView`
**URL:** `/job/rest/jobs/{job_id}/files/{file_id}/thumbnail/`
**Responsibility:** Serve thumbnail images

**Methods:**
```
GET    /job/rest/jobs/{job_id}/files/{file_id}/thumbnail/  getJobFileThumbnail
```

**Total: 3 URL patterns → 6 endpoints → 6 unique operationIds**

**Why include job_id in file operations?**
- Consistent resource hierarchy (all operations under /jobs/{job_id}/)
- Explicit job context for authorization checks
- Can validate file belongs to specified job
- Clearer API semantics
- **Uses UUID (not int job_number) - consistent with all other job endpoints**

## Implementation Steps

### 1. Create NEW view file: `apps/job/views/job_files_rest.py`

Create three view classes with single responsibilities:

```python
class JobFilesCollectionView(JobNumberLookupMixin, APIView):
    """
    Collection operations: /jobs/{job_number}/files/
    - POST: Upload files to this job
    - GET: List all files for this job
    """

    @extend_schema(operation_id="uploadJobFiles", ...)
    def post(self, request, job_number):
        # job_number from URL path
        # files from multipart form data
        pass

    @extend_schema(operation_id="listJobFiles", ...)
    def get(self, request, job_number):
        # job_number from URL path
        pass


class JobFileDetailView(APIView):
    """
    Resource operations: /jobs/files/{file_id}/
    - GET: Download/view file content
    - PUT: Update file metadata
    - DELETE: Delete file
    """

    @extend_schema(operation_id="getJobFile", ...)
    def get(self, request, file_id):
        # file_id (UUID) from URL path
        pass

    @extend_schema(operation_id="updateJobFile", ...)
    def put(self, request, file_id):
        # file_id (UUID) from URL path
        # metadata in JSON body
        pass

    @extend_schema(operation_id="deleteJobFile", ...)
    def delete(self, request, file_id):
        # file_id (UUID) from URL path
        pass


class JobFileThumbnailView(APIView):
    """
    Thumbnail operations: /jobs/files/{file_id}/thumbnail/
    - GET: Serve thumbnail image
    """

    @extend_schema(operation_id="getJobFileThumbnail", ...)
    def get(self, request, file_id):
        # file_id (UUID) from URL path
        pass
```

**Key implementation notes:**
- `JobFilesCollectionView` uses `job_number` (int) from URL path
- `JobFileDetailView` uses `file_id` (UUID) from URL path
- No conditional routing logic - each URL maps to one view
- Each HTTP method has unique operationId
- Move thumbnail view into same file for consolidation

### 2. Delete OLD files

**Delete entirely:**
- `apps/job/views/job_file_upload.py` (redundant upload view)
- `apps/job/views/job_file_view.py` (messy conditional routing view)

### 3. Update URL patterns: `apps/job/urls_rest.py`

**A. Update imports (around line 13-14):**

Remove:
```python
from apps.job.views.job_file_upload import JobFileUploadView
from apps.job.views.job_file_view import JobFileThumbnailView, JobFileView
```

Add:
```python
from apps.job.views.job_files_rest import (
    JobFilesCollectionView,
    JobFileDetailView,
    JobFileThumbnailView,
)
```

**B. Delete old URL patterns (lines 198-222):**

Remove ALL of these:
```python
path("rest/jobs/files/upload/", JobFileUploadView.as_view(), name="job_file_upload"),
path("rest/jobs/files/<uuid:file_id>/thumbnail/", JobFileThumbnailView.as_view(), name="job_file_thumbnail"),
path("rest/jobs/files/<int:job_number>/", JobFileView.as_view(), name="job_files_list"),
path("rest/jobs/files/", JobFileView.as_view(), name="job_file_base"),
path("rest/jobs/files/<path:file_path>/", JobFileView.as_view(), name="job_file_download"),
path("rest/jobs/files/<int:file_path>/", JobFileView.as_view(), name="job_file_delete"),
```

**C. Add new URL patterns:**

```python
# Job Files - Collection operations (job-scoped)
path(
    "rest/jobs/<int:job_number>/files/",
    JobFilesCollectionView.as_view(),
    name="job_files_collection",
),

# Job Files - Resource operations (file-scoped)
path(
    "rest/jobs/files/<uuid:file_id>/",
    JobFileDetailView.as_view(),
    name="job_file_detail",
),
path(
    "rest/jobs/files/<uuid:file_id>/thumbnail/",
    JobFileThumbnailView.as_view(),
    name="job_file_thumbnail",
),
```

### 4. Update view exports

Run the auto-generation script:
```bash
python scripts/update_init.py
```

This will update `apps/job/views/__init__.py` to remove old exports and add new ones.

### 5. Verification

**A. Generate OpenAPI schema:**
```bash
python manage.py spectacular --file schema.yml
```

**B. Verify schema:**
- [ ] Search for numeric suffixes: `grep -E "uploadJobFiles_[0-9]|deleteJobFile_[0-9]" schema.yml` should return nothing
- [ ] Count job file endpoints: Should be exactly 6
- [ ] All operationIds unique: uploadJobFiles, listJobFiles, getJobFile, updateJobFile, deleteJobFile, getJobFileThumbnail

**C. Test backend operations:**
- [ ] Upload files: `POST /job/rest/jobs/{job_number}/files/` with multipart form data
- [ ] List files: `GET /job/rest/jobs/{job_number}/files/`
- [ ] Download file: `GET /job/rest/jobs/{job_number}/files/{file_id}/`
- [ ] Update metadata: `PUT /job/rest/jobs/{job_number}/files/{file_id}/` with JSON body `{filename, print_on_jobsheet}`
- [ ] Delete file: `DELETE /job/rest/jobs/{job_number}/files/{file_id}/`
- [ ] Get thumbnail: `GET /job/rest/jobs/{job_number}/files/{file_id}/thumbnail/`

### 6. Create Frontend Migration Guide

**AFTER implementation is complete**, write `docs/api/job_files_api_migration.md` with:

- Summary of changes (OLD vs NEW endpoints)
- Side-by-side code examples for each operation
- OpenAPI operationId changes (removed numeric suffixes)
- Steps to regenerate frontend client code
- Testing checklist

**Template structure:**
```markdown
# Job Files API Migration Guide

## Breaking Changes
[OLD endpoint] → [NEW endpoint]

## Migration by Operation
### 1. Upload Files
OLD: POST /jobs/files/upload/ with job_number in body
NEW: POST /jobs/{job_number}/files/ with job_number in URL

### 2. List Files
...

## Code Generation
npm run generate-api

## Testing Checklist
```

**Coordinate with frontend team:**
- Provide them the clean schema.yml
- Share migration guide
- Wait for frontend to update before removing old code

## Breaking Changes (Intentional)

All old endpoints will return 404 to force frontend migration:

| Old Endpoint | Status | New Endpoint |
|-------------|--------|--------------|
| `POST /rest/jobs/files/upload/` | ❌ 404 | `POST /rest/jobs/{job_number}/files/` |
| `GET /rest/jobs/files/<int:job_number>/` | ❌ 404 | `GET /rest/jobs/{job_number}/files/` |
| `GET /rest/jobs/files/` | ❌ 404 | Ambiguous - no replacement |
| `GET /rest/jobs/files/<path:file_path>/` | ❌ 404 | `GET /rest/jobs/files/{file_id}/` |
| `PUT /rest/jobs/files/<int:job_number>/` | ❌ 404 | `PUT /rest/jobs/files/{file_id}/` |
| `DELETE /rest/jobs/files/<int:file_path>/` | ❌ 404 | `DELETE /rest/jobs/files/{file_id}/` |

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Upload endpoints | 2 (duplicate) | 1 (consolidated) |
| URL patterns | 6+ overlapping | 3 distinct |
| View classes | 2 with routing logic | 3 with single responsibility |
| Job number | Sometimes URL, sometimes body | Always in URL path |
| File identifier | Mixed (path/ID/number) | Always UUID in path |
| OperationIds | Duplicates + numeric suffixes | 6 unique IDs |
| Total endpoints | 15+ | 6 |
| Tech debt | High | Low |

✅ **ONE upload endpoint** (not two)
✅ **Clear resource hierarchy** (/jobs/{job_number}/files/)
✅ **No operationId collisions** (6 unique IDs)
✅ **Reduced tech debt** (15+ endpoints → 6)
✅ **Follows REST conventions** (collections vs resources)
✅ **Type-safe URLs** (UUID for file_id, int for job_number)
✅ **Break old patterns** (force migration to clean API)
✅ **Single responsibility per view** (no conditional routing)

## Frontend Migration Guide

The frontend needs to update three operations:

### 1. Upload files
**Before:**
```javascript
POST /job/rest/jobs/files/upload/
Body: multipart/form-data
  - job_number: "12345"
  - files: [file1, file2]
```

**After:**
```javascript
POST /job/rest/jobs/12345/files/
Body: multipart/form-data
  - files: [file1, file2]
```

### 2. Delete file
**Before:**
```javascript
DELETE /job/rest/jobs/files/{file_id}/
```

**After:**
```javascript
DELETE /job/rest/jobs/files/{file_id}/
```
(No change - already correct)

### 3. Update metadata
**Before:**
```javascript
PUT /job/rest/jobs/files/{job_number}/
Body:
  - filename: "new_name.pdf"
  - print_on_jobsheet: true
```

**After:**
```javascript
PUT /job/rest/jobs/files/{file_id}/
Body:
  - filename: "new_name.pdf"
  - print_on_jobsheet: true
```

**Key change:** Use `file_id` (UUID) instead of `job_number` in URL path.

## Acceptance Criteria

### MUST PASS - OpenAPI Schema Validation

**1. Zero duplicate operationIds:**
```bash
python manage.py spectacular --file schema.yml

# Should output: "Warnings: 0"
# Currently shows 6 warnings with collisions
```

**2. No numeric suffixes:**
```bash
grep -E "_[0-9]$" schema.yml | grep operationId

# Should return: nothing
# Currently finds: uploadJobFilesApi_2, deleteJobFilesApi_3, etc.
```

**3. Count check:**
```bash
# Total operationIds should equal unique operationIds
echo "Total: $(grep -c operationId schema.yml)"
echo "Unique: $(grep operationId schema.yml | sort -u | wc -l)"

# These two numbers must match
```

### MUST PASS - REST Compliance

**1. Required identifiers in URL path (NOT body/query):**
- ✅ job_number in URL path
- ✅ file_id in URL path
- ❌ NO identifiers in request body
- ❌ NO identifiers as required query params

**2. Request body contains only data:**
- ✅ File content (multipart form data)
- ✅ Metadata (filename, print_on_jobsheet)
- ❌ NO identifiers (job_number, file_id)

**3. One endpoint per operation:**
- ✅ No conditional routing in view methods
- ✅ No optional URL segments causing duplicates
- ✅ Each HTTP method + URL = unique operationId

### MUST PASS - Functional Tests

**1. Upload files:**
```bash
curl -X POST http://localhost:8000/job/rest/jobs/12345/files/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test1.pdf" \
  -F "files=@test2.pdf"

# Expected: 201 Created with uploaded file IDs
```

**2. List files:**
```bash
curl -X GET http://localhost:8000/job/rest/jobs/12345/files/ \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with array of files
```

**3. Download file:**
```bash
curl -X GET http://localhost:8000/job/rest/jobs/12345/files/{file_id}/ \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with file content
```

**4. Update metadata:**
```bash
curl -X PUT http://localhost:8000/job/rest/jobs/12345/files/{file_id}/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "renamed.pdf", "print_on_jobsheet": true}'

# Expected: 200 OK with updated metadata
```

**5. Delete file:**
```bash
curl -X DELETE http://localhost:8000/job/rest/jobs/12345/files/{file_id}/ \
  -H "Authorization: Bearer $TOKEN"

# Expected: 204 No Content
```

**6. Old endpoints return 404:**
```bash
# These should all return 404
curl -X POST http://localhost:8000/job/rest/jobs/files/upload/
curl -X GET http://localhost:8000/job/rest/jobs/files/12345/

# Expected: 404 Not Found (endpoints deleted)
```

## Scope: Codebase-Wide Problem

**This is NOT just a job files issue.** The same violations exist across multiple modules:

### Current OpenAPI Schema Warnings:
```
Warning: operationId "retrieveJobFilesApi" has collisions
  [('/job/rest/jobs/files/', 'get'),
   ('/job/rest/jobs/files/{file_path}/', 'get'),
   ('/job/rest/jobs/files/{job_number}/', 'get')]

Warning: operationId "getDailyTimesheetSummaryByDate" has collisions
  [('/timesheets/api/daily/', 'get'),
   ('/timesheets/api/daily/{target_date}/', 'get')]

Warning: operationId "getStaffDailyTimesheetDetailByDate" has collisions
  [('/timesheets/api/staff/{staff_id}/daily/', 'get'),
   ('/timesheets/api/staff/{staff_id}/daily/{target_date}/', 'get')]
```

### Other Violations Found:

**1. Modern Timesheet (`apps/job/views/modern_timesheet_views.py`):**
```python
# WRONG: Required identifiers in query params
GET /rest/timesheet/entries/?staff_id=<uuid>&date=<date>

# WRONG: Required identifiers in body
POST /rest/timesheet/entries/
Body: {
    job_id: "uuid",      # ❌ Should be in URL
    staff_id: "uuid",    # ❌ Should be in URL
    date: "2024-01-01",  # ❌ Should be in URL
    hours: 8.5
}
```

**Should be:**
```python
GET /rest/timesheet/staff/{staff_id}/date/{entry_date}/

POST /rest/jobs/{job_number}/timesheet/staff/{staff_id}/date/{entry_date}/
Body: {
    hours: 8.5,         # ✅ Data only
    description: "...", # ✅ Data only
    is_billable: true   # ✅ Data only
}
```

**This plan focuses on job files first.** Timesheet and other modules will be fixed in subsequent phases using the same principles.

## Next Steps

1. Execute implementation steps 1-4 for job files
2. Run acceptance criteria tests
3. Generate and verify clean OpenAPI schema (no warnings)
4. Provide `schema.yml` to frontend team
5. Frontend updates generated client code
6. Test all operations end-to-end
7. Deploy backend changes
8. Deploy frontend changes
9. **Create similar plans for timesheet and other modules**
