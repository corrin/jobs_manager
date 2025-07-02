# Job File View Documentation

## Business Purpose
Provides comprehensive file management functionality for job-related documents in jobbing shop operations. Handles file upload, download, update, deletion, and thumbnail generation for job documentation. Essential for managing technical drawings, specifications, photos, and supporting materials throughout the job lifecycle, with integration to workshop jobsheets and Dropbox storage.

## Views

### JobFileView
**File**: `apps/job/views/job_file_view.py`
**Type**: Class-based view (APIView)
**URLs**: Multiple endpoints for complete file management

#### What it does
- Provides comprehensive REST API for job file management
- Handles file upload, download, update, and deletion operations
- Manages Dropbox integration for file storage and synchronization
- Supports file metadata management and jobsheet printing control
- Enables workshop access to job documentation and materials

#### URL Patterns
- `/rest/jobs/files/` - Base file operations (POST, PUT)
- `/rest/jobs/files/<int:job_number>/` - List files for specific job (GET)
- `/rest/jobs/files/<path:file_path>/` - Download specific file (GET)
- `/rest/jobs/files/<int:file_path>/` - Delete file by ID (DELETE)

### post (File Upload Method)
**File**: `apps/job/views/job_file_view.py`
**Type**: Method within JobFileView
**URL**: `/rest/jobs/files/` (POST)

#### What it does
- Handles multi-file uploads with validation and error handling
- Creates job-specific Dropbox folders with proper permissions
- Stores files with comprehensive metadata tracking
- Manages file size validation and corruption detection
- Defaults to printing files on jobsheets for workshop access

#### Parameters
- Form data with file upload information:
  - `job_number`: Job number to attach files to (required)
  - `files`: Multiple files for upload (required)

#### Returns
- **201 Created**: Files successfully uploaded
  - `status`: "success"
  - `uploaded`: Array of uploaded file metadata
  - `message`: Success confirmation
- **207 Multi-Status**: Partial success with some upload failures
  - `status`: "partial_success"
  - `uploaded`: Successfully uploaded files
  - `errors`: Array of error messages for failed uploads
- **400 Bad Request**: No files provided or validation errors
- **404 Not Found**: Job not found for specified job number

#### Integration
- JobNumberLookupMixin for job validation
- Dropbox folder management with permission settings
- File size validation and corruption detection
- JobFile model update_or_create for metadata persistence

### get (File Retrieval Method)
**File**: `apps/job/views/job_file_view.py`
**Type**: Method within JobFileView
**URLs**: Multiple GET endpoints

#### What it does
- Serves files for download with proper MIME type detection
- Lists files associated with specific jobs
- Handles file streaming for large documents
- Provides inline file serving for browser viewing

#### Parameters
- **Option 1**: List files for job
  - `job_number`: Job number to list files for (path parameter)
- **Option 2**: Download specific file
  - `file_path`: Relative path to file in Dropbox (path parameter)

#### Returns
- **200 OK**: File data or file list
  - File download: Binary file response with proper headers
  - File list: JSON array of file metadata
- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: File or job not found

#### Integration
- JobFileSerializer for file metadata formatting
- MIME type detection for proper content headers
- FileResponse for efficient file streaming
- Dropbox path resolution for file access

### put (File Update Method)
**File**: `apps/job/views/job_file_view.py`
**Type**: Method within JobFileView
**URL**: `/rest/jobs/files/` (PUT)

#### What it does
- Updates existing files with new content or metadata
- Handles jobsheet printing flag updates without file replacement
- Manages file replacement with validation and integrity checks
- Supports partial updates for metadata-only changes

#### Parameters
- Form data with update information:
  - `job_number`: Job number for file location (required)
  - `filename`: Existing filename to update (required for metadata-only updates)
  - `print_on_jobsheet`: Boolean flag for workshop printing
  - `files`: New file content (optional for metadata-only updates)

#### Returns
- **200 OK**: File successfully updated
  - `status`: "success"
  - `message`: Update confirmation
  - `print_on_jobsheet`: Updated flag value
- **400 Bad Request**: Invalid parameters or file corruption
- **404 Not Found**: File not found for update

#### Integration
- File integrity validation during replacement
- Jobsheet printing flag management
- Dropbox file overwrite with safety checks
- JobFile model metadata updates

### delete (File Deletion Method)
**File**: `apps/job/views/job_file_view.py`
**Type**: Method within JobFileView
**URL**: `/rest/jobs/files/<int:file_path>/` (DELETE)

#### What it does
- Deletes job files and associated metadata
- Removes files from Dropbox storage
- Cleans up JobFile database records
- Handles safe deletion with error recovery

#### Parameters
- `file_path`: JobFile ID for deletion (path parameter, despite name)

#### Returns
- **204 No Content**: File successfully deleted
- **404 Not Found**: File not found for deletion
- **500 Internal Server Error**: Deletion failures

#### Integration
- Dropbox file removal with existence checking
- JobFile model record deletion
- Error handling for partial deletion scenarios

### JobFileThumbnailView
**File**: `apps/job/views/job_file_view.py`
**Type**: Class-based view (APIView)
**URL**: `/rest/jobs/files/<uuid:file_id>/thumbnail/`

#### What it does
- Serves JPEG thumbnails for job files
- Provides optimized preview images for file management interfaces
- Supports file preview without downloading full documents
- Enables quick visual identification of file contents

#### Parameters
- `file_id`: JobFile UUID for thumbnail generation (path parameter)

#### Returns
- **200 OK**: JPEG thumbnail image
- **404 Not Found**: Thumbnail not available or file not found

#### Integration
- JobFile model thumbnail path management
- FileResponse for JPEG image serving
- Active file status validation

## File Management Features
- **Dropbox Integration**: Files stored in `DROPBOX_WORKFLOW_FOLDER/Job-{job_number}/`
- **Permission Management**: Automatic folder (0o2775) and file (0o664) permissions
- **File Validation**: Size verification and corruption detection
- **Metadata Tracking**: MIME type, filename, path, and printing preferences
- **Update Handling**: Support for both file replacement and metadata-only updates

## Error Handling
- **400 Bad Request**: Invalid parameters, empty files, or validation failures
- **404 Not Found**: Job or file not found
- **207 Multi-Status**: Partial success scenarios for batch operations
- **500 Internal Server Error**: File system or database errors
- Comprehensive logging for debugging and audit trails
- Graceful handling of file corruption and incomplete uploads

## Business Rules
- Files are organized by job number in dedicated Dropbox folders
- Default setting enables printing on jobsheets for workshop access
- File updates maintain integrity through size validation
- Deletion removes both file system and database records
- Thumbnail generation supports quick file preview
- Multiple files can be uploaded in single requests

## Integration Points
- **JobNumberLookupMixin**: Job validation and error handling
- **JobLookupMixin**: Generic job lookup functionality
- **Dropbox Integration**: File storage and synchronization
- **JobFile Model**: Metadata persistence and relationship management
- **JobFileSerializer**: Response data formatting and API consistency

## Performance Considerations
- Efficient file chunking for large uploads
- FileResponse for optimized file streaming
- Batch processing for multi-file operations
- MIME type detection with caching
- Relative path calculation for storage efficiency
- Thumbnail serving for quick previews

## Security Considerations
- Job number validation prevents unauthorized file access
- File size validation prevents system abuse
- Permission management for multi-user access
- Input validation for all file operations
- Error message sanitization to prevent information leakage

## Workshop Integration
- Files marked for jobsheet printing appear in workshop documentation
- Thumbnail support enables quick file identification
- Download functionality provides workshop access to specifications
- File organization by job number supports workflow efficiency

## Related Views
- JobFileUploadView for dedicated upload functionality
- Job management views for project lifecycle
- Workshop views for production documentation access
- Kanban views for file attachment visualization