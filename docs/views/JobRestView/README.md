# Job REST View Documentation

## Business Purpose
Provides comprehensive REST API for core job management operations in jobbing shop workflow. Handles complete job lifecycle from creation through completion, including job details, status management, and entry tracking (time, materials, adjustments). Central to the quote → job → invoice workflow and supports real-time job editing with autosave functionality.

## Views

### BaseJobRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Base class for job REST operations (APIView)
**URL**: N/A (base class)

#### What it does
- Provides common functionality for all job REST views
- Implements centralized error handling and JSON parsing
- Supports JWT authentication through DRF APIView inheritance
- Follows clean code principles with single responsibility

#### Integration
- CSRF exempt decorator for API endpoints
- Centralized service layer error handling with appropriate HTTP status codes
- Structured error responses for client-side handling

### JobCreateRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView
**URL**: `/job/rest/jobs/`

#### What it does
- Creates new jobs with client association and job number generation
- Supports optional fields for comprehensive job setup
- Delegates business logic to JobRestService for clean separation

#### Parameters
- JSON body with job data:
  - `name`: Job name (required)
  - `client_id`: UUID of client (required)
  - `description`: Job description (optional)
  - `order_number`: Client order number (optional)
  - `notes`: Additional notes (optional)
  - `contact_id`: Client contact UUID (optional)

#### Returns
- **201 Created**: Created job with ID, job number, and success message
- **400 Bad Request**: Validation errors or missing required fields
- **500 Internal Server Error**: Job creation failures

#### Integration
- Uses JobRestService.create_job for business logic
- Generates sequential job numbers automatically
- Creates associated JobPricing records for all stages

### JobDetailRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView
**URL**: `/job/rest/jobs/<uuid:job_id>/`

#### What it does
- **GET**: Retrieves complete job data for editing interfaces
- **PUT**: Updates job data with autosave functionality
- **DELETE**: Soft deletes jobs with business rule validation

#### Parameters
- `job_id`: UUID of job (path parameter)
- **PUT**: JSON body with updated job fields
- **DELETE**: No body required

#### Returns
- **GET**: Complete job data including pricing, entries, and status
- **PUT**: Updated job data for frontend reactivity
- **DELETE**: Success confirmation
- **404 Not Found**: Job not found
- **400/403**: Business rule violations

#### Integration
- Supports real-time editing with immediate data refresh
- Validates job status transitions and deletion permissions
- Maintains job audit trail through JobEvent creation

### JobToggleComplexRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView
**URL**: `/job/rest/jobs/toggle-complex/`

#### What it does
- Toggles complex job mode for advanced workflow features
- Controls access to detailed costing and advanced job management
- Updates job configuration for specialized processing

#### Parameters
- JSON body with toggle data:
  - `job_id`: UUID of job to toggle (required)
  - `complex_job`: Boolean flag for complex mode (required)

#### Returns
- **200 OK**: Toggle confirmation with updated status
- **400 Bad Request**: Missing required parameters
- **404 Not Found**: Job not found

#### Integration
- Uses JobRestService.toggle_complex_job for business logic
- Affects job interface and available features
- Logs configuration changes for audit purposes

### JobTogglePricingMethodologyRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView (DEPRECATED)
**URL**: `/job/rest/jobs/toggle-pricing-methodology/`

#### What it does
- **DEPRECATED**: This endpoint is no longer used
- All pricing stages (estimate, quote, actual) are created automatically
- Maintained for backward compatibility only

#### Returns
- **400 Bad Request**: Deprecation notice with explanation

### JobEventRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView
**URL**: `/job/rest/jobs/<uuid:job_id>/events/`

#### What it does
- Creates manual job events for audit trail and communication
- Supports custom event descriptions for workflow tracking
- Maintains comprehensive job history

#### Parameters
- `job_id`: UUID of job (path parameter)
- JSON body with event data:
  - `description`: Event description (required)

#### Returns
- **201 Created**: Created event confirmation
- **400 Bad Request**: Missing description
- **404 Not Found**: Job not found

#### Integration
- Creates JobEvent records with timestamp and user tracking
- Supports job workflow documentation and communication

### JobTimeEntryRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView
**URL**: `/job/rest/jobs/<uuid:job_id>/time-entries/`

#### What it does
- Creates time entries for labor cost tracking and billing
- Supports hourly billing with separate cost and revenue rates
- Integrates with timesheet and costing systems

#### Parameters
- `job_id`: UUID of job (path parameter)
- JSON body with time entry data:
  - `description`: Task description (required)
  - `hours`: Hours worked (required)
  - `charge_out_rate`: Billing rate per hour (required)
  - `wage_rate`: Cost rate per hour (required)

#### Returns
- **201 Created**: Created time entry with updated job data
- **400 Bad Request**: Invalid data or missing fields
- **404 Not Found**: Job not found

#### Integration
- Creates TimeEntry records linked to job pricing
- Updates job costing calculations automatically
- Returns refreshed job data for real-time updates

### JobMaterialEntryRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView
**URL**: `/job/rest/jobs/<uuid:job_id>/material-entries/`

#### What it does
- Creates material entries for parts and supplies cost tracking
- Supports quantity-based costing with separate cost and revenue rates
- Integrates with inventory and purchasing systems

#### Parameters
- `job_id`: UUID of job (path parameter)
- JSON body with material entry data:
  - `description`: Material description (required)
  - `quantity`: Quantity used (required)
  - `unit_cost`: Cost per unit (required)
  - `unit_revenue`: Revenue per unit (required)

#### Returns
- **201 Created**: Created material entry with updated job data
- **400 Bad Request**: Invalid data or missing fields
- **404 Not Found**: Job not found

#### Integration
- Creates MaterialEntry records for job costing
- Links to stock management and purchase orders
- Updates job profitability calculations

### JobAdjustmentEntryRestView
**File**: `apps/job/views/job_rest_views.py`
**Type**: Class-based view extending BaseJobRestView
**URL**: `/job/rest/jobs/<uuid:job_id>/adjustment-entries/`

#### What it does
- Creates adjustment entries for miscellaneous costs or credits
- Supports positive and negative adjustments for accurate costing
- Handles special circumstances and cost corrections

#### Parameters
- `job_id`: UUID of job (path parameter)
- JSON body with adjustment data:
  - `description`: Adjustment description (required)
  - `amount`: Adjustment amount (required, can be negative)

#### Returns
- **201 Created**: Created adjustment entry with updated job data
- **400 Bad Request**: Invalid data or missing fields
- **404 Not Found**: Job not found

#### Integration
- Creates AdjustmentEntry records for job costing
- Supports cost corrections and special charges
- Updates job financial calculations immediately

## Error Handling
- **400 Bad Request**: Validation errors, missing required fields, or business rule violations
- **403 Forbidden**: Permission errors for job access or modification
- **404 Not Found**: Job or related resources not found
- **500 Internal Server Error**: Database errors, service failures, or unexpected system errors
- Centralized error handling with structured responses and appropriate HTTP status codes

## Related Views
- Job costing views for detailed financial tracking
- Kanban views for visual job status management
- Timesheet views for time entry integration
- Client views for customer relationship management
