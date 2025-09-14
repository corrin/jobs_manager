# KPI View Documentation

## Business Purpose

Provides comprehensive Key Performance Indicator (KPI) analytics for a jobbing shop's daily operations. Displays labour productivity, gross profit targets, and business performance metrics in a calendar format, supporting management decision-making and performance tracking across the quote → job → invoice workflow.

## Views

### KPICalendarTemplateView

**File**: `apps/accounting/views/kpi_view.py`
**Type**: Class-based view (TemplateView)
**URL**: `/accounting/reports/calendar/`

#### What it does

- Renders the KPI Calendar dashboard page
- Provides frontend interface for viewing business analytics
- Displays monthly performance metrics with visual indicators

#### Parameters

- No specific parameters required

#### Returns

- Template: `reports/kpi_calendar.html` with KPI dashboard interface
- Context includes page title and calendar interface elements

#### Integration

- Uses FullCalendar JavaScript library for calendar display
- Connects to KPICalendarAPIView for data fetching
- No direct Xero integration (displays processed accounting data)

### KPICalendarAPIView

**File**: `apps/accounting/views/kpi_view.py`
**Type**: Class-based view (APIView)
**URL**: `/accounting/api/reports/calendar/`

#### What it does

- Provides KPI data for calendar display via REST API
- Calculates daily labour hours, billable percentages, and gross profit
- Aggregates time entries, material costs, and adjustment entries
- Applies company thresholds for performance color coding

#### Parameters

- `year`: Calendar year (defaults to current year)
- `month`: Calendar month 1-12 (defaults to current month)

#### Returns

- JSON response containing:
  - `calendar_data`: Daily KPI metrics with performance indicators
  - `monthly_totals`: Aggregated monthly statistics
  - `thresholds`: Company performance thresholds
  - `year`, `month`: Requested time period

#### Integration

- Uses KPIService for business logic calculations
- Processes TimeEntry, MaterialEntry, and AdjustmentEntry data
- Applies CompanyDefaults thresholds for performance evaluation
- Excludes specific staff members from calculations

## Error Handling

- **400 Bad Request**: Invalid year/month parameters (non-numeric or out of range)
- **500 Internal Server Error**: Database errors or calculation failures with detailed logging
- Comprehensive error logging with stack traces for debugging

## Related Views

- CompanyDefaults configuration affects threshold calculations
- TimeEntry views for labour data source
- MaterialEntry/AdjustmentEntry views for cost tracking
- Job management views for associated business context
