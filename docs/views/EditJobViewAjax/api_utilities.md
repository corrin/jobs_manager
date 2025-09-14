# Job Editing API Utilities

## Business Purpose

Provides essential API endpoints for job editing interface support. Handles company defaults retrieval, job status management, and pricing data access for real-time job editing workflows in jobbing shop operations.

## Views

### get_company_defaults_api

**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view
**URL**: `/job/api/company-defaults/`

#### What it does

- Retrieves company-wide default settings for job creation
- Provides markup rates and default rates for new jobs
- Ensures consistent pricing across job creation workflow
- Uses helper function to guarantee single instance retrieval

#### Parameters

- No parameters required

#### Returns

- **200 OK**: JSON with company default settings
  - `materials_markup`: Default materials markup percentage
  - `time_markup`: Default time markup percentage
  - `charge_out_rate`: Default hourly charge rate
  - `wage_rate`: Default wage rate

#### Integration

- Uses get_company_defaults() helper for singleton pattern
- Provides foundation data for job pricing calculations
- Float conversion for JavaScript compatibility

### api_fetch_status_values

**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view
**URL**: `/job/api/status-values/`

#### What it does

- Returns available job status options for status dropdowns
- Provides standardized status values for job workflow management
- Supports job status transition interfaces and validation

#### Parameters

- No parameters required

#### Returns

- **200 OK**: JSON array of available job status values
- Status options include workflow stages (quoting, in_progress, completed, etc.)

#### Integration

- Job.STATUS_CHOICES model integration
- Status workflow validation support
- Dropdown population for job editing interfaces

### fetch_job_pricing_api

**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view
**URL**: `/job/api/pricing/<uuid:job_id>/`

#### What it does

- Retrieves comprehensive job pricing data including historical revisions
- Provides complete cost breakdown (time, materials, adjustments)
- Returns job files and document management information
- Supports detailed job analysis and pricing review

#### Parameters

- `job_id`: UUID of job to fetch pricing for (path parameter)

#### Returns

- **200 OK**: Comprehensive job pricing data including:
  - Latest pricing for all stages (estimate, quote, actual)
  - Historical pricing revisions with complete breakdowns
  - Time entries with cost and revenue calculations
  - Material entries with quantity and pricing details
  - Adjustment entries for cost corrections
  - Job files and document status
  - Total cost and revenue calculations by category
- **404 Not Found**: Job not found

#### Integration

- JobPricingSerializer for structured data format
- get_historical_job_pricings() service for revision tracking
- get_latest_job_pricings() for current pricing state
- sync_job_folder() for file synchronization
- Comprehensive pricing breakdown with cost/revenue separation

## Error Handling

- **404 Not Found**: Job not found for pricing retrieval
- **500 Internal Server Error**: Database errors or calculation failures
- Graceful handling of missing pricing data
- Float conversion safety for JavaScript consumption

## Data Structures

### Company Defaults Response

```json
{
  "materials_markup": 0.25,
  "time_markup": 0.15,
  "charge_out_rate": 105.0,
  "wage_rate": 32.5
}
```

### Job Pricing Response Structure

- Complete pricing hierarchy with stage-specific data
- Historical revision tracking with timestamps
- Detailed cost breakdowns by category (time, materials, adjustments)
- File management integration with document status
- Calculated totals for cost and revenue analysis

## Related Views

- Job creation and editing views for pricing application
- Job management views for status workflow
- Cost calculation views for pricing accuracy
- File management views for document integration
