# Job Management Operations

## Business Purpose
Handles advanced job management operations including month-end processing, event tracking, complexity management, and job deletion. Supports administrative workflows and job lifecycle management in jobbing shop operations.

## Views

### process_month_end
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/month-end/`

#### What it does
- Processes month-end operations for job accounting
- Archives completed job pricing and creates new revisions
- Handles job state transitions for accounting periods
- Manages historical data preservation and new period setup

#### Parameters
- JSON body with month-end processing data:
  - `job_id`: Job UUID to process (required)
  - Additional month-end specific parameters

#### Returns
- **200 OK**: JSON success confirmation with processing results
- **400 Bad Request**: Invalid job state or processing errors
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Month-end processing failures

#### Integration
- archive_and_reset_job_pricing() service for pricing management
- Job status workflow validation
- Historical data preservation mechanisms
- Accounting period transition handling

### add_job_event
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/events/add/`

#### What it does
- Adds manual events to job audit trail
- Supports custom event logging for job workflow tracking
- Maintains comprehensive job history and communication log
- Enables user-defined milestone and note tracking

#### Parameters
- JSON body with event data:
  - `job_id`: Job UUID (required)
  - `description`: Event description (required)
  - `event_type`: Event category (optional)
  - Additional event metadata

#### Returns
- **201 Created**: JSON with created event details
- **400 Bad Request**: Validation errors or missing required fields
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Event creation failures

#### Integration
- JobEvent model for audit trail management
- Event categorization and tagging
- User tracking for event attribution
- Timeline integration for job history display

### toggle_complex_job
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/toggle-complex/`

#### What it does
- Toggles complex job mode for advanced workflow features
- Controls access to detailed costing and specialized processing
- Manages job complexity classification and feature availability
- Handles complexity-specific validation and business rules

#### Parameters
- JSON body with complexity toggle data:
  - `job_id`: Job UUID (required)
  - `complex_job`: Boolean flag for complexity mode (required)

#### Returns
- **200 OK**: JSON confirmation with updated complexity status
- **400 Bad Request**: Invalid complexity state or validation errors
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Complexity toggle failures

#### Integration
- Job model complexity flag management
- Feature availability control based on complexity
- Workflow validation for complexity requirements
- UI state management for complex job interfaces

### delete_job
**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view (DELETE only)
**URL**: `/job/api/delete/<uuid:job_id>/`

#### What it does
- Soft deletes jobs with comprehensive validation
- Handles job deletion business rules and constraints
- Manages related data cleanup and integrity preservation
- Provides safe job removal with audit trail maintenance

#### Parameters
- `job_id`: Job UUID to delete (path parameter)

#### Returns
- **200 OK**: JSON confirmation of successful deletion
- **400 Bad Request**: Job cannot be deleted due to business rules
- **404 Not Found**: Job not found
- **409 Conflict**: Job has dependencies preventing deletion
- **500 Internal Server Error**: Deletion processing failures

#### Integration
- Business rule validation for deletion eligibility
- Related data dependency checking
- Soft deletion pattern for data preservation
- Audit trail maintenance for deletion tracking
- File system cleanup for job documents

## Business Rules and Constraints

### Month-End Processing
- Jobs must be in appropriate status for month-end processing
- Pricing revisions must be properly archived
- Historical data integrity must be maintained
- Accounting period consistency validation

### Event Management
- Events must have valid descriptions and classifications
- User attribution required for all manual events
- Event timestamps must be accurate and consistent
- Audit trail completeness enforcement

### Complexity Management
- Complex job features require appropriate user permissions
- Complexity changes must validate existing job data
- Feature availability controlled by complexity status
- Business rules enforcement for complex workflows

### Job Deletion
- Jobs with active invoices cannot be deleted
- Jobs with purchase orders require special handling
- Time entries and costs must be properly handled
- Client relationships preserved during deletion

## Error Handling
- **400 Bad Request**: Business rule violations, validation errors, or invalid job states
- **401 Unauthorized**: Insufficient permissions for management operations
- **404 Not Found**: Job or related resources not found
- **409 Conflict**: Data dependencies preventing operation completion
- **500 Internal Server Error**: System failures, database errors, or unexpected processing issues

## Audit and Tracking
- All management operations create audit trail entries
- User attribution for all job modifications
- Timestamp tracking for operation history
- Status change logging for workflow compliance

## Integration Points
- Job workflow system for status management
- Accounting system for month-end processing
- File management for document handling
- User management for permission validation
- Event system for audit trail maintenance