# Job File Upload View Documentation

## Business Purpose

Provides file upload functionality for job-related documents in jobbing shop operations. Handles document attachment to specific jobs, manages Dropbox integration for file storage, and maintains file metadata for workshop access. Essential for job documentation, technical drawings, specifications, and supporting materials throughout the job lifecycle.

## Views

### JobFileUploadView

**File**: `apps/job/views/job_file_upload.py`
**Type**: Class-based view (APIView)
**URL**: `/rest/jobs/files/upload/`

#### What it does

- Provides REST API endpoint for uploading files to specific jobs
- Handles multiple file uploads in a single request
- Manages Dropbox folder creation and file storage
- Creates JobFile database records with metadata
- Supports job documentation and workshop materials
- Enables file attachment workflow for job management

#### Parameters

- Form data with file upload information:
  - `job_number`: Job number to attach files to (required)
  - `files`: Multiple files for upload (required)

#### Returns

- **200 OK**: Files successfully uploaded
  - `status`: "success"
  - `uploaded`: Array of uploaded file data with metadata
  - `message`: Success confirmation message
- **400 Bad Request**: Missing required parameters or validation errors
  - `status`: "error"
  - `message`: Detailed error description
- **404 Not Found**: Job not found for specified job number
- **500 Internal Server Error**: File system or database errors

#### Integration

- JobNumberLookupMixin for job validation and retrieval
- MultiPartParser and FormParser for file upload handling
- JobFileSerializer for response data formatting
- Dropbox integration for file storage and synchronization
- JobFile model for metadata persistence

### post (Upload Method)

**File**: `apps/job/views/job_file_upload.py`
**Type**: Method within JobFileUploadView

#### What it does

- Handles POST requests for multi-file upload operations
- Validates job existence before processing uploads
- Creates job-specific Dropbox folders with proper permissions
- Stores files in Dropbox workflow folder structure
- Creates or updates JobFile records with metadata
- Manages file permissions and folder structure

#### Parameters

- Same as parent JobFileUploadView
- Processes multiple files simultaneously

#### Returns

- Comprehensive upload results with file metadata
- Detailed error messages for validation failures

#### Integration

- Dropbox folder management with configurable paths
- File permission management (0o664 for files, 0o2775 for folders)
- JobFile model update_or_create for metadata handling
- Relative path calculation for Dropbox integration

## File Management

- **Dropbox Integration**: Files stored in `DROPBOX_WORKFLOW_FOLDER/Job-{job_number}/`
- **Folder Creation**: Automatic job-specific folder creation with proper permissions
- **File Permissions**: 0o664 for uploaded files, 0o2775 for folders
- **Duplicate Handling**: update_or_create pattern prevents duplicate JobFile records
- **Metadata Storage**: MIME type, filename, and path information preserved

## Error Handling

- **400 Bad Request**: Missing job_number or no files uploaded
- **404 Not Found**: Job not found for specified job number
- **500 Internal Server Error**: File system errors or database failures
- Comprehensive error messages for troubleshooting
- Legacy error format support for compatibility

## Business Rules

- Files are organized by job number in Dropbox folders
- Multiple files can be uploaded in a single request
- Existing files are updated rather than duplicated
- All uploaded files default to not printing on job sheets
- Files are marked as "active" status upon upload
- Job must exist before files can be attached

## Integration Points

- **JobNumberLookupMixin**: Job validation and error handling
- **Dropbox Integration**: File storage and synchronization
- **JobFile Model**: Metadata persistence and relationship management
- **JobFileSerializer**: Response data formatting and API consistency
- **Settings Configuration**: Dropbox folder path configuration

## Performance Considerations

- Efficient file chunking for large file uploads
- Batch processing of multiple files in single request
- Optimized folder creation with exist_ok parameter
- update_or_create pattern prevents duplicate database queries
- Relative path calculation for storage efficiency

## Security Considerations

- Job number validation prevents unauthorized file association
- File permission management for secure access
- MIME type validation and storage
- Folder permission settings for multi-user access
- Input validation for file and job parameters

## File Storage Structure

```
DROPBOX_WORKFLOW_FOLDER/
├── Job-{job_number}/
│   ├── uploaded_file1.pdf
│   ├── uploaded_file2.dwg
│   └── ...
```

## Related Views

- JobFileView for file management and access
- Job management views for job lifecycle
- Workshop views for file access during production
- JobFile model for metadata management
