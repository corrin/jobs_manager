# Job Files API Changes (Work in Progress)

**Status:** In progress - being updated as changes are made

## Changes Completed So Far

### Step 1: Removed Upload Endpoint ✅
**Date:** 2025-11-01

**Removed:**
```
POST /job/rest/jobs/files/upload/
```

**Use Instead:**
```
POST /job/rest/jobs/files/<int:job_number>/
```

---

### Step 2: Removed Ambiguous Endpoints ✅
**Date:** 2025-11-01

**Removed:**
```
/job/rest/jobs/files/                          (all methods)
/job/rest/jobs/files/<path:file_path>/         (all methods)
/job/rest/jobs/files/<int:file_path>/          (DELETE only)
```

**Use Instead:**
```
/job/rest/jobs/files/<int:job_number>/         (GET, POST, PUT, DELETE)
/job/rest/jobs/files/<uuid:file_id>/thumbnail/ (GET)
```

---

## Current API Structure

### File Operations (All use job_number)
```
POST   /job/rest/jobs/files/<int:job_number>/
       operationId: uploadJobFilesApi
       Body: multipart/form-data with files

GET    /job/rest/jobs/files/<int:job_number>/
       operationId: retrieveJobFilesApi
       Returns: Array of files for job

PUT    /job/rest/jobs/files/<int:job_number>/
       operationId: updateJobFilesApi
       Body: { filename, print_on_jobsheet }

DELETE /job/rest/jobs/files/<int:job_number>/
       operationId: deleteJobFilesApi
       Query: ?file_id=<uuid>
```

### Thumbnail
```
GET    /job/rest/jobs/files/<uuid:file_id>/thumbnail/
       operationId: getJobFileThumbnail
       Returns: JPEG image
```

---

## Breaking Changes Summary

### Removed Endpoints (Return 404)
```
❌ POST   /job/rest/jobs/files/upload/
❌ GET    /job/rest/jobs/files/
❌ POST   /job/rest/jobs/files/
❌ PUT    /job/rest/jobs/files/
❌ DELETE /job/rest/jobs/files/
❌ GET    /job/rest/jobs/files/<path:file_path>/
❌ POST   /job/rest/jobs/files/<path:file_path>/
❌ PUT    /job/rest/jobs/files/<path:file_path>/
❌ DELETE /job/rest/jobs/files/<path:file_path>/
❌ DELETE /job/rest/jobs/files/<int:file_id>/
```

### Migration Required
All file operations now require `<int:job_number>` in URL path:

**Before:**
```typescript
POST /job/rest/jobs/files/upload/
Body: { job_number: 12345, files: [...] }
```

**After:**
```typescript
POST /job/rest/jobs/files/12345/
Body: { files: [...] }
```

---

### Step 3: Split Views and Change to UUID ✅
**Date:** 2025-11-01

**Changes:**
- Split `JobFileView` into 3 separate view classes
- Changed from `int:job_number` to `uuid:job_id` in URLs
- All required identifiers now in URL path (REST compliant)

**Removed:**
```
POST   /job/rest/jobs/files/<int:job_number>/
GET    /job/rest/jobs/files/<int:job_number>/
PUT    /job/rest/jobs/files/<int:job_number>/
DELETE /job/rest/jobs/files/<int:job_number>/
```

**Added:**
```
Collection operations:
POST   /job/rest/jobs/<uuid:job_id>/files/
GET    /job/rest/jobs/<uuid:job_id>/files/

Resource operations:
GET    /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/
PUT    /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/
DELETE /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/

Thumbnail:
GET    /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/thumbnail/
```

---

## Final API Structure

### Collection Operations
```
POST   /job/rest/jobs/<uuid:job_id>/files/
       operationId: uploadJobFiles
       Body: multipart/form-data with files
       Returns: 201 Created with uploaded file data

GET    /job/rest/jobs/<uuid:job_id>/files/
       operationId: listJobFiles
       Returns: 200 OK with array of files for job
```

### Resource Operations
```
GET    /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/
       operationId: getJobFile
       Returns: Binary file content for download/viewing

PUT    /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/
       operationId: updateJobFile
       Body: { filename?, print_on_jobsheet? }
       Returns: 200 OK with updated metadata

DELETE /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/
       operationId: deleteJobFile
       Returns: 204 No Content
```

### Thumbnail
```
GET    /job/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/thumbnail/
       operationId: getJobFileThumbnail
       Returns: JPEG image binary
```

---

## Migration Guide for Frontend

### Before (Multiple Patterns)
```typescript
// Upload - required job_number in body
POST /job/rest/jobs/files/upload/
Body: { job_number: 12345, files: [...] }

// OR (ambiguous)
POST /job/rest/jobs/files/12345/
Body: { files: [...] }

// List
GET /job/rest/jobs/files/12345/

// Update - required filename in body to identify file
PUT /job/rest/jobs/files/12345/
Body: { filename: "old.pdf", print_on_jobsheet: true }

// Delete - required file_id in query param
DELETE /job/rest/jobs/files/12345/?file_id=<uuid>
```

### After (Clean REST)
```typescript
// Upload - job_id in URL only
POST /job/rest/jobs/<uuid>/files/
Body: { files: [...] }

// List - job_id in URL only
GET /job/rest/jobs/<uuid>/files/

// Download - both IDs in URL
GET /job/rest/jobs/<uuid>/files/<uuid>/

// Update - both IDs in URL
PUT /job/rest/jobs/<uuid>/files/<uuid>/
Body: { filename?: string, print_on_jobsheet?: boolean }

// Delete - both IDs in URL
DELETE /job/rest/jobs/<uuid>/files/<uuid>/

// Thumbnail - both IDs in URL
GET /job/rest/jobs/<uuid>/files/<uuid>/thumbnail/
```

### Key Changes
1. **Always use `uuid:job_id`**, never `int:job_number`
2. **All identifiers in URL path**, never in body or query params
3. **Two URL patterns**: collection (`/jobs/{id}/files/`) and resource (`/jobs/{id}/files/{id}/`)
4. **Unique operationIds**: No numeric suffixes (_2, _3, etc.)

---

## Verification

```bash
# Generate schema
python manage.py spectacular --file schema.yml

# Results after all changes:
# Warnings: 2 (2 unique) - only timesheet warnings
# Errors:   0
# Job file operationId collisions: 0 ✅

# Verify all 6 unique operationIds
grep "operationId.*JobFile" schema.yml
# Output:
# operationId: listJobFiles
# operationId: uploadJobFiles
# operationId: getJobFile
# operationId: updateJobFile
# operationId: deleteJobFile
# operationId: getJobFileThumbnail
```

---

**Status:** Complete ✅
**Last Updated:** 2025-11-01
