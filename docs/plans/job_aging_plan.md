# Job Aging Report Implementation Plan

## Overview
Create a new Job Aging report API endpoint that provides comprehensive job aging information, including financial data from CostSets, timing information, and current status.

## Implementation Details

### 1. Service Layer (`apps/accounting/services.py`)
- **Add `JobAgingService` class** with methods:
  - `get_job_aging_data()`: Main method to fetch and process all job aging data
  - `_calculate_time_in_status()`: Calculate days in current status using JobEvent model
  - `_calculate_job_age()`: Calculate days since job creation
  - `_get_last_activity()`: Find most recent activity across ALL sources:
    - JobEvent entries (all types, not just status changes)
    - TimeEntry records (when time was last added)
    - MaterialEntry records (when materials were last added)
    - AdjustmentEntry records (when adjustments were made)
    - Job model updates (updated_at field)
  - `_get_financial_totals()`: Extract estimate/quote/actual totals from CostSets

### 2. API View (`apps/accounting/views/job_aging_view.py`)
- **Create `JobAgingAPIView`**: RESTful API endpoint
- **Return JSON structure**:
  ```json
  {
    "jobs": [
      {
        "id": "uuid",
        "job_number": 1234,
        "name": "Job Name",
        "client_name": "Client Name",
        "status": "in_progress",
        "status_display": "In Progress",
        "financial_data": {
          "estimate_total": 5000.00,
          "quote_total": 4800.00,
          "actual_total": 4750.00
        },
        "timing_data": {
          "created_date": "2024-01-15",
          "created_days_ago": 45,
          "days_in_current_status": 12,
          "last_activity_date": "2024-02-27",
          "last_activity_days_ago": 1,
          "last_activity_type": "time_entry",
          "last_activity_description": "Time added by John Smith"
        }
      }
    ]
  }
  ```

### 3. URL Configuration (`apps/accounting/urls.py`)
- **Add endpoint**: `path("api/reports/job-aging/", JobAgingAPIView.as_view(), name="api_job_aging")`

### 4. Data Sources & Logic
- **Job Model**: Primary data source for job information
- **CostSet Model**: Financial data (estimate/quote/actual totals from cost_lines)
- **JobEvent Model**: Status change tracking and other job events
- **TimeEntry Model**: Time tracking activity (most recent date field)
- **MaterialEntry Model**: Material usage activity (most recent accounting_date)
- **AdjustmentEntry Model**: Adjustment activity (most recent accounting_date)
- **Last Activity Logic**: Compare timestamps across all sources to find the true last activity
- **Time Calculations**: Use Django's timezone-aware datetime handling
- **Relative Dates**: Calculate "X days ago" format for all date fields

### 5. Performance Optimizations
- **Use `select_related()`** for client, latest_estimate, latest_quote, latest_actual
- **Use `prefetch_related()`** for cost_lines, events, and related activity records
- **Efficient subqueries** to get max dates from related tables
- **Single query approach** with annotations where possible
- **Database-level date calculations** using Django ORM functions

### 6. Data Processing
- **Filter active jobs** (exclude archived unless requested)
- **Sort by configurable criteria** (default: last_activity_days_ago DESC)
- **Handle edge cases**: Jobs without events, missing cost data, etc.
- **Financial totals calculation**: Sum cost_lines.total_rev for each CostSet
- **Activity type mapping**: Determine activity source and create descriptive text

## Files to Create/Modify
1. **✅ COMPLETED**: `apps/accounting/services.py` - Add JobAgingService class
   - Added JobAgingService with proper error handling using persist_app_error
   - Includes all required methods: get_job_aging_data, _get_financial_totals, _get_timing_data, _calculate_time_in_status, _get_last_activity
   - Follows defensive programming principles with comprehensive error logging and persistence
2. **Create**: `apps/accounting/views/job_aging_view.py` - New API view
3. **Modify**: `apps/accounting/urls.py` - Add URL pattern
4. **Modify**: `apps/accounting/views/__init__.py` - Import new view

## Testing Approach
- **Manual testing** via API endpoint
- **Test with various job states** and activity types
- **Verify last activity detection** across all data sources
- **Validate date calculations** and relative formatting