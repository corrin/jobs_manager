# Job Management View Documentation

## Business Purpose

Handles month-end processing for special long-running jobs in jobbing shop operations. Enables archival of accumulated costs and reset of pricing stages for ongoing projects, supporting continuous cost tracking and financial reporting across multiple accounting periods.

## Views

### month_end_view

**File**: `apps/job/views/job_management_view.py`
**Type**: Function-based view (staff authentication required)
**URL**: `/jobs/month-end/`

#### What it does

- Displays special jobs eligible for month-end processing
- Shows accumulated hours and revenue since last month-end
- Processes selected jobs by archiving current pricing and resetting stages
- Maintains historical pricing data while enabling fresh cost tracking

#### Parameters

- **GET**: No parameters required
- **POST**: `job_ids[]` - List of job IDs selected for month-end processing

#### Returns

- **GET**: Template `jobs/month_end.html` with special jobs data
- **POST**: Redirect to same page with success/error messages

#### Integration

- Uses `archive_and_reset_job_pricing` service for pricing archival
- Processes only jobs with status "special" (long-running projects)
- Creates historical JobPricing records for audit trail
- Resets estimate/quote pricing stages with company defaults
- No direct Xero integration (internal workflow management)

#### Business Logic

1. **Job Selection**: Identifies jobs with status "special"
2. **Data Collection**: Calculates total hours and revenue since last month-end
3. **Processing**: Archives current pricing data and creates fresh pricing stages
4. **Historical Tracking**: Maintains audit trail of monthly cost accumulations

#### Authentication

- Requires staff-level authentication (`@user_passes_test(is_staff)`)
- Restricts access to authorized personnel only

## Error Handling

- **Job Not Found**: Logs error and continues processing other selected jobs
- **Processing Failures**: Captures exceptions and displays warning messages
- **Success Messages**: Confirms successful processing with job names
- Atomic transactions ensure data integrity during pricing archival

## Related Views

- JobPricing views for pricing stage management
- KPI views for month-end financial reporting
- Job costing views for accumulated cost analysis
- Special job status management in job workflow
