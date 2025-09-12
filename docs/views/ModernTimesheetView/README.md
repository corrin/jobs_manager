# Modern Timesheet View Documentation

## Business Purpose
Provides modern REST API for timesheet management in jobbing shop operations. Bridges legacy TimeEntry system with modern CostLine architecture, enabling accurate time tracking and billing for job costing. Essential for tracking billable vs non-billable hours and calculating job profitability.

## Views

### ModernTimesheetEntryView
**File**: `apps/job/views/modern_timesheet_views.py`
**Type**: Class-based view (APIView with authentication)
**URL**: `/jobs/rest/timesheet/entries/`

#### What it does
- **GET**: Retrieves timesheet entries for specific staff member and date
- **POST**: Creates new timesheet entries as CostLines in actual cost sets
- Calculates billable vs non-billable hours and cost/revenue totals
- Provides bridge between legacy timesheet system and modern costing architecture

#### Parameters
- **GET**:
  - `staff_id`: UUID of staff member
  - `date`: Entry date in YYYY-MM-DD format
- **POST**: JSON body with timesheet entry data including job_id, staff_id, hours, entry_date

#### Returns
- **GET**: Staff timesheet data with cost lines, totals, and summary statistics
- **POST**: Created CostLine data with 201 status

#### Integration
- Uses CostLine model with kind='time' for timesheet entries
- Integrates with TimesheetToCostLineService for data migration
- Stores staff/date metadata in JSON fields for querying
- No direct Xero integration (internal time tracking)

### ModernTimesheetDayView
**File**: `apps/job/views/modern_timesheet_views.py`
**Type**: Class-based view (APIView with authentication)
**URL**: `/jobs/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/`

#### What it does
- Retrieves all timesheet entries for specific staff member on specific date
- Provides day-level view of staff time allocation across jobs
- Calculates daily totals for hours, cost, and revenue

#### Parameters
- `staff_id`: UUID of staff member
- `entry_date`: Date in YYYY-MM-DD format

#### Returns
- JSON response with staff info, cost lines, and daily totals

#### Integration
- Queries CostLine with timesheet metadata for staff/date filtering
- Uses TimesheetCostLineSerializer for consistent API response format

### ModernTimesheetJobView
**File**: `apps/job/views/modern_timesheet_views.py`
**Type**: Class-based view (APIView with authentication)
**URL**: `/jobs/rest/timesheet/jobs/<uuid:job_id>/`

#### What it does
- Retrieves all timesheet entries for specific job
- Shows time allocation across all staff members for the job
- Provides job-level time tracking and cost analysis

#### Parameters
- `job_id`: UUID of job

#### Returns
- JSON response with job info, timesheet cost lines, and job totals

#### Integration
- Accesses actual cost set for the job
- Filters for time cost lines created from timesheets
- Supports job-level time and cost analysis

## Error Handling
- **400 Bad Request**: Missing or invalid parameters (staff_id, date, hours)
- **404 Not Found**: Staff member or job not found
- **500 Internal Server Error**: Database errors or cost line creation failures
- Comprehensive input validation with guard clauses
- Atomic transactions for data integrity

## Related Views
- Job costing views for cost analysis
- CostLine management views for cost tracking
- Legacy timesheet views for data migration
- KPI views for time-based performance metrics
