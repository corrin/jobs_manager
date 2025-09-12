# Timesheet API View Documentation

## Business Purpose
Provides comprehensive REST API for timesheet management in jobbing shop operations. Handles time entry creation, editing, and tracking across staff members and jobs. Supports daily and weekly timesheet overviews, autosave functionality, and paid absence management. Critical for accurate labor cost tracking and billing throughout the quote → job → invoice workflow.

## Views

### StaffListAPIView
**File**: `apps/timesheet/views/api.py`
**Type**: Class-based view (APIView)
**URL**: `/timesheet/api/staff/`

#### What it does
- Provides filtered list of staff members for timesheet interfaces
- Excludes administrative staff and inactive users
- Returns formatted staff data for dropdown and selection components

#### Parameters
- No parameters required

#### Returns
- **200 OK**: Filtered staff list with display names and contact information
- **500 Internal Server Error**: Staff retrieval failures

#### Integration
- Uses get_excluded_staff() utility for filtering logic
- Ordered by last name, first name for consistent presentation
- Includes avatar placeholder for future UI enhancements

### TimeEntriesAPIView
**File**: `apps/timesheet/views/api.py`
**Type**: Class-based view (APIView)
**URL**: `/timesheet/api/entries/`

#### What it does
- **GET**: Retrieves time entries for specific staff and date ranges
- **POST**: Creates new time entries with job pricing associations
- **PUT**: Updates existing time entries with field-level changes
- **DELETE**: Removes time entries with soft validation

#### Parameters
- **GET**: `staff_id`, `date` or `start_date`/`end_date` (query parameters)
- **POST**: JSON body with time entry data including staff, job pricing, hours, rates
- **PUT**: `entry_id` (path parameter) and JSON body with updates
- **DELETE**: `entry_id` (path parameter)

#### Returns
- **GET**: Time entries with related job and staff information
- **POST**: Created time entry with 201 status
- **PUT**: Updated time entry data
- **DELETE**: Success confirmation with 204 status
- **400/404/500**: Validation errors, not found, or system failures

#### Integration
- Links to Staff and JobPricing models for complete workflow
- Supports flexible hour calculation (direct hours or items × minutes)
- TimeEntryAPISerializer for consistent data formatting

### JobsAPIView
**File**: `apps/timesheet/views/api.py`
**Type**: Class-based view (APIView)
**URL**: `/timesheet/api/jobs/`

#### What it does
- Provides list of active jobs available for time entry
- Filters jobs by status to exclude completed/archived items
- Uses CostSet system integration for modern timesheet workflow

#### Parameters
- No parameters required

#### Returns
- **200 OK**: Active jobs with client information and cost set status
- **500 Internal Server Error**: Job retrieval failures

#### Integration
- Filters by active job statuses (quoting, in_progress, etc.)
- Ensures jobs have actual cost sets for time tracking
- TimesheetJobAPISerializer for structured job data

### WeeklyOverviewAPIView
**File**: `apps/timesheet/views/api.py`
**Type**: Class-based view (APIView)
**URL**: `/timesheet/api/weekly-overview/`

#### What it does
- Provides comprehensive weekly timesheet overview for all staff
- Organizes time entries by staff member and day
- Calculates daily and weekly totals for reporting

#### Parameters
- `start_date`: Week start date in YYYY-MM-DD format (optional, defaults to current week)

#### Returns
- **200 OK**: Weekly data with staff entries, daily totals, and week summaries
- **400 Bad Request**: Invalid date format
- **500 Internal Server Error**: Data retrieval failures

#### Integration
- Uses get_excluded_staff() for consistent staff filtering
- Seven-day week structure with date range calculations
- TimeEntryAPISerializer for entry data consistency

### autosave_timesheet_api
**File**: `apps/timesheet/views/api.py`
**Type**: Function-based API view
**URL**: `/timesheet/api/autosave/`

#### What it does
- Provides real-time autosave functionality for timesheet entries
- Updates specific fields without full form submission
- Maintains data integrity during extended editing sessions

#### Parameters
- JSON body with `entry_id` and field updates

#### Returns
- **200 OK**: Autosave success confirmation with entry ID
- **400 Bad Request**: Missing entry ID
- **404 Not Found**: Entry not found
- **500 Internal Server Error**: Autosave failures

#### Integration
- Updates only provided fields for efficient data handling
- Maintains existing entry relationships and constraints

### DailyTimesheetAPIView
**File**: `apps/timesheet/views/api.py`
**Type**: Class-based view (APIView)
**URL**: `/timesheet/api/daily/`

#### What it does
- Provides comprehensive daily timesheet overview using modern CostLine system
- Delivers daily summary with staff hours, status, and alerts
- Integrates with DailyTimesheetService for business logic

#### Parameters
- `date`: Target date in YYYY-MM-DD format (optional, defaults to today)

#### Returns
- **200 OK**: Daily timesheet data with staff summaries and metrics
- **400 Bad Request**: Invalid date format
- **500 Internal Server Error**: Service failures

#### Integration
- Delegates to DailyTimesheetService for business logic separation
- DailyTimesheetSummarySerializer for structured response format
- Comprehensive error handling with staff-level detail filtering

### WeeklyTimesheetAPIView
**File**: `apps/timesheet/views/api.py`
**Type**: Class-based view (APIView)
**URL**: `/timesheet/api/weekly/`

#### What it does
- **GET**: Comprehensive weekly timesheet data using WeeklyTimesheetService
- **POST**: Submits paid absence requests with validation and processing
- Provides complete weekly overview for Vue.js frontend integration

#### Parameters
- **GET**: `start_date` (optional Monday date), `export_to_ims` (optional boolean)
- **POST**: JSON body with paid absence data (staff_id, dates, leave_type, hours)

#### Returns
- **GET**: Complete weekly data with daily breakdowns, totals, and navigation
- **POST**: Paid absence submission confirmation with 201 status
- **400/500**: Validation errors or processing failures

#### Integration
- Uses WeeklyTimesheetService for complex business logic
- Supports IMS export mode for external system integration
- Comprehensive paid absence workflow with date validation
- Navigation helper data for week-to-week interface movement

## Error Handling
- **400 Bad Request**: Missing required fields, invalid date formats, or validation errors
- **401 Unauthorized**: Authentication required for all endpoints
- **404 Not Found**: Staff members, time entries, or jobs not found
- **500 Internal Server Error**: Database errors, service failures, or unexpected system errors
- Comprehensive input validation and sanitization
- Detailed logging for debugging and monitoring
- Staff-level error detail filtering for security

## Related Views
- Job management views for time entry job associations
- Staff management views for user relationships
- Modern timesheet views for UI integration
- Costing views for labor cost tracking and billing
