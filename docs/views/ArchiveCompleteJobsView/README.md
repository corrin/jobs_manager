# Archive Complete Jobs Views Documentation

## Business Purpose
Provides job archival functionality for completed and paid jobs in jobbing shop operations. Handles the transition of completed jobs from active workflow to archived status, maintaining historical records while optimizing active job management. Essential for end-of-month processing, record keeping, and system performance optimization.

## Views

### ArchiveCompleteJobsViews (Container Class)
**File**: `apps/job/views/archive_completed_jobs_view.py`
**Type**: Container class organizing related archival views

#### What it does
- Centralizes job archival functionality in a single organizational unit
- Contains template view, list API, and archival processing API
- Provides cohesive interface for job archival workflow
- Manages both UI and API aspects of job archival process

### ArchiveCompleteJobsTemplateView
**File**: `apps/job/views/archive_completed_jobs_view.py`
**Type**: Class-based view (TemplateView)
**URL**: `/job/archive-complete`

#### What it does
- Renders job archival interface for administrative users
- Displays list of completed and paid jobs ready for archival
- Provides web interface for bulk job archival operations
- Supports job selection and batch processing workflows

#### Parameters
- No parameters required

#### Returns
- **200 OK**: Archive complete jobs template with job data interface

#### Integration
- Template-based interface for job archival management
- Integration with job archival APIs for data processing
- Administrative interface for end-of-month operations

### ArchiveCompleteJobsListAPIView
**File**: `apps/job/views/archive_completed_jobs_view.py`
**Type**: Class-based view (ListAPIView)
**URL**: `/api/job/completed/`

#### What it does
- Provides REST API endpoint for retrieving completed and paid jobs
- Returns paginated list of jobs eligible for archival
- Supports job selection interface for bulk archival operations
- Filters jobs based on completion and payment status

#### Parameters
- Standard pagination parameters:
  - `page`: Page number for pagination
  - `page_size`: Number of jobs per page (max 100, default 50)

#### Returns
- **200 OK**: JSON with paginated completed job data
  - Pagination metadata (count, next, previous)
  - Job list with complete serialization data
- **401 Unauthorized**: Authentication required

#### Integration
- CompleteJobSerializer for consistent job data structure
- get_paid_complete_jobs service for business logic
- StandardResultsSetPagination for optimized data loading
- Authentication required for all access

### ArchiveCompleteJobsAPIView
**File**: `apps/job/views/archive_completed_jobs_view.py`
**Type**: Class-based view (APIView)
**URL**: `/api/job/completed/archive`

#### What it does
- Processes bulk job archival operations via POST requests
- Archives multiple jobs in a single transaction
- Handles partial success scenarios with detailed error reporting
- Manages job status transitions from active to archived

#### Parameters
- JSON body with archival data:
  - `ids`: Array of job UUIDs to archive (required)

#### Returns
- **200 OK**: All jobs successfully archived
  - `success`: True
  - `message`: Success message with archived count
- **207 Multi-Status**: Partial success with some errors
  - `success`: True (if any archived)
  - `message`: Status summary with counts
  - `errors`: Array of error details for failed jobs
- **400 Bad Request**: No jobs provided or all jobs failed
  - `success`: False
  - `error`: Error message describing the issue
- **401 Unauthorized**: Authentication required
- **500 Internal Server Error**: System failures during archival

#### Integration
- archive_complete_jobs service for business logic and validation
- Job model status updates and workflow management
- Audit trail creation for archival operations
- Error handling and partial success management

### post (ArchiveCompleteJobsAPIView)
**File**: `apps/job/views/archive_completed_jobs_view.py`
**Type**: Method within ArchiveCompleteJobsAPIView

#### What it does
- Handles POST requests for bulk job archival processing
- Validates job ID arrays and processes archival operations
- Manages transaction handling and error recovery
- Provides detailed response with success/failure information

#### Parameters
- Same as parent ArchiveCompleteJobsAPIView
- Enhanced error handling and validation

#### Returns
- Comprehensive archival status with detailed error reporting
- Multi-status responses for partial success scenarios

#### Integration
- Service layer delegation for business logic
- Comprehensive logging for audit and debugging
- Error aggregation and reporting

## Error Handling
- **400 Bad Request**: No job IDs provided or invalid job data
- **401 Unauthorized**: Authentication required for all archival operations
- **207 Multi-Status**: Partial success with some jobs failing archival
- **500 Internal Server Error**: System failures or database errors
- Comprehensive error logging for debugging and monitoring
- Detailed error messages for individual job failures

## Business Rules
- Only completed and paid jobs are eligible for archival
- Bulk archival operations support partial success scenarios
- Archived jobs are removed from active workflow but retained for records
- Archival operations require authentication and appropriate permissions
- End-of-month processing workflow integration

## Integration Points
- **Job Service**: archive_complete_jobs and get_paid_complete_jobs for business logic
- **Job Serializer**: CompleteJobSerializer for consistent data representation
- **Authentication System**: Required authentication for all operations
- **Pagination System**: StandardResultsSetPagination for performance optimization
- **Audit System**: Logging and tracking for archival operations

## Performance Considerations
- Paginated job listings for large datasets (50 jobs per page, max 100)
- Bulk archival operations for efficiency
- Service layer optimization for database operations
- Error handling without blocking successful operations
- Optimized queries for completed and paid job filtering

## Security Considerations
- Authentication required for all archival operations
- Input validation for job ID arrays
- Error message sanitization to prevent information leakage
- Audit logging for compliance and monitoring
- Transaction handling for data integrity

## Related Views
- Job management views for workflow transitions
- Month-end processing views for periodic operations
- Job status views for workflow management
- Audit views for archival tracking and compliance