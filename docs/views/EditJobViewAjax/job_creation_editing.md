# Job Creation and Editing Views

## Business Purpose
Handles core job creation and editing functionality for jobbing shop workflow. Manages job lifecycle from initial creation through editing, with real-time autosave and comprehensive data validation. Critical for maintaining job data integrity throughout the quote → job → invoice process.

## Views

### create_job_view
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based template view
**URL**: `/job/create/`

#### What it does
- Renders job creation interface template
- Provides foundation for new job creation workflow
- Serves as entry point for job creation process

#### Parameters
- No parameters required

#### Returns
- **200 OK**: Job creation template (`jobs/create_job_and_redirect.html`)

#### Integration
- Template-based job creation interface
- Foundation for AJAX job creation workflow
- Client-side form handling and validation

### create_job_api
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/create/`

#### What it does
- Creates new jobs with comprehensive data validation
- Handles client relationship establishment
- Generates job numbers and initializes pricing structures
- Manages job folder creation and file synchronization

#### Parameters
- JSON body with job creation data:
  - `name`: Job name (required)
  - `client_id`: Client UUID (required)
  - `description`: Job description (optional)
  - `order_number`: Client order reference (optional)
  - `contact_id`: Primary contact UUID (optional)

#### Returns
- **201 Created**: JSON with created job data and redirect URL
- **400 Bad Request**: Validation errors or missing required data
- **500 Internal Server Error**: Job creation failures

#### Integration
- JobSerializer for data validation and processing
- Client relationship validation and establishment
- Job number generation and uniqueness enforcement
- File system integration for job document management
- Transaction safety for data integrity

### edit_job_view_ajax
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based template view
**URL**: `/job/edit/<uuid:job_id>/`

#### What it does
- Renders comprehensive job editing interface
- Provides complete job data including pricing history
- Supports real-time editing with autosave functionality
- Integrates file management and document handling

#### Parameters
- `job_id`: UUID of job to edit (path parameter)

#### Returns
- **200 OK**: Job editing template with complete job context
- **404 Not Found**: Job not found

#### Integration
- Complete job data serialization with JobSerializer
- Historical pricing data with revision tracking
- Latest pricing data for all stages (estimate, quote, actual)
- Job file synchronization and document management
- Company defaults integration for pricing calculations
- Template context with comprehensive job information

### autosave_job_view
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/autosave/`

#### What it does
- Provides real-time autosave functionality for job editing
- Handles partial job updates without full form submission
- Maintains data consistency during extended editing sessions
- Supports concurrent editing with conflict resolution

#### Parameters
- JSON body with job update data:
  - `job_id`: Job UUID (required)
  - Various job fields for partial updates

#### Returns
- **200 OK**: JSON success confirmation with updated job data
- **400 Bad Request**: Validation errors or invalid job ID
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Autosave processing failures

#### Integration
- JobSerializer for partial update validation
- Transaction safety for data integrity
- Real-time data synchronization
- Conflict detection and resolution mechanisms
- File system synchronization on job updates

## Data Validation and Business Rules

### Job Creation Validation
- Client relationship verification
- Job name uniqueness within client scope
- Required field validation (name, client)
- Contact validation when specified
- Order number format validation

### Job Editing Constraints
- Job status workflow validation
- Pricing stage consistency checks
- File attachment limits and validation
- User permission verification
- Data integrity maintenance across updates

### Autosave Behavior
- Incremental field updates
- Transaction rollback on validation failures
- Concurrent editing conflict detection
- Automatic retry mechanisms for transient failures
- Real-time UI feedback integration

## Error Handling
- **400 Bad Request**: Validation errors, missing required fields, or business rule violations
- **401 Unauthorized**: Insufficient permissions for job operations
- **404 Not Found**: Job or related resources not found
- **409 Conflict**: Concurrent editing conflicts or duplicate data
- **500 Internal Server Error**: Database errors, file system failures, or unexpected system errors

## Integration Points
- Client management for relationship establishment
- File management for document handling
- Pricing system for cost calculation
- Job numbering system for unique identification
- Template system for user interface rendering

## Performance Considerations
- Transaction optimization for data integrity
- File synchronization efficiency
- Real-time autosave debouncing
- Historical data pagination for large jobs
- Selective data loading for editing interfaces
