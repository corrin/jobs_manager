# Xero Payroll Integration Plan

**Date:** 2025-11-03
**Branch:** `feature/xero-payroll` (based on `main`)
**Status:** In Progress

## Overview

Integrate Xero Payroll API to enable submission of weekly timesheets from jobs_manager to Xero Payroll. This replaces the legacy IMS payroll system. The system acts as a data entry frontend - users enter time and leave, then explicitly post to Xero via a "post week to Xero" button.

## Architecture Decisions

### Core Concepts

1. **Magic Jobs for Leave**: Leave is tracked as time entries (CostLine) on special "magic jobs":
   - "Annual Leave"
   - "Sick Leave"
   - "Other Leave"
   - "Unpaid Leave"

2. **No Sync, Only Submit**: One-way data submission to Xero (not bidirectional sync)
   - jobs_manager is data entry tool
   - Xero is source of truth for rates, balances, payroll logic
   - No conflict resolution needed

3. **No New Models**: Use existing CostLine infrastructure for all time tracking

4. **Leave Type Matters**: Annual vs Sick vs Unpaid are treated differently in Xero Payroll API

### Technical Approach

- Identify leave by pattern matching job names
- Collect week's CostLine entries and categorize by leave type
- Map to Xero Payroll timesheet format
- Submit via Xero Payroll API using Staff.xero_user_id

## Implementation Tasks

### 1. Xero Payroll API Client
**File:** `apps/workflow/api/xero/payroll.py`

Create new service class for Xero Payroll API integration:
- Use `xero_python.payrollau` (or `payrolluk`/`payrollus` depending on region)
- `post_timesheet(employee_id, week_start, time_entries)` - Submit weekly timesheet
- `get_employees()` - Fetch Xero employee list for ID matching
- Handle authentication via existing XeroToken infrastructure

### 2. Token Scope Updates
**File:** `apps/workflow/models/xero_token.py`

Add Xero Payroll API scopes:
- `payroll.timesheets` - Submit timesheets
- `payroll.employees` - Read employee data
- `payroll.settings` - Read payroll settings (leave types, earnings rates)

### 3. Leave Type Identification
**File:** `apps/job/utils.py` or `apps/timesheet/utils.py`

Utility function to identify leave type from job name:
```python
def get_leave_type(job_name: str) -> Optional[str]:
    """
    Returns: "annual", "sick", "other", "unpaid", or None
    """
```

Pattern matching on job name to categorize.

### 4. Payroll Posting Service
**File:** `apps/timesheet/services/payroll_sync.py`

Core business logic for posting timesheets:
```python
def post_week_to_xero(staff_id: UUID, week_start_date: date) -> dict:
    """
    Collect CostLine entries for staff/week and submit to Xero Payroll.

    Returns:
        {
            'success': bool,
            'xero_timesheet_id': str,
            'entries_posted': int,
            'leave_hours': decimal,
            'work_hours': decimal,
        }
    """
```

Logic:
1. Validate staff has `xero_user_id`
2. Collect CostLine entries (kind='time') for date range
3. Categorize by leave type (annual/sick/other/unpaid vs work)
4. Map rate_multiplier to Xero earnings rates
5. Submit to Xero Payroll API
6. Return result

### 5. REST API Endpoint
**File:** `apps/timesheet/views/payroll_api.py`

Create endpoint for posting to Xero:
```
POST /api/timesheet/post-week-to-xero/
{
    "staff_id": "uuid",
    "week_start_date": "2025-11-03"
}

Response:
{
    "success": true,
    "xero_timesheet_id": "...",
    "entries_posted": 45,
    "leave_hours": 8.0,
    "work_hours": 37.0
}
```

### 6. Jobs API Enhancement
**File:** `apps/timesheet/views/api.py`

Enhance JobsAPIView response to include leave type:
```json
{
    "id": "...",
    "job_number": "123",
    "description": "Annual Leave",
    "leave_type": "annual"  // NEW: "annual", "sick", "other", "unpaid", or null
}
```

This allows frontend to:
- Filter magic jobs in payroll mode
- Display appropriate UI for leave entry
- Distinguish leave types visually

## Data Flow

```
User enters hours → CostLine (kind='time')
                           ↓
                  Magic job detection
                  (by job name pattern)
                           ↓
         ┌─────────────────┴──────────────┐
         ↓                                ↓
    Leave entry                      Work entry
    (Annual/Sick/                    (Regular job)
     Other/Unpaid)
         ↓                                ↓
         └─────────────────┬──────────────┘
                           ↓
          User clicks "Post Week to Xero"
                           ↓
                 Payroll Sync Service
                           ↓
                Map to Xero format
                (leave vs earnings)
                           ↓
                  Xero Payroll API
                           ↓
                 Timesheet submitted
```

## Frontend Integration Points

The frontend will need to:
1. Display leave_type field in job listings
2. Add "payroll mode" toggle to show/hide magic jobs
3. Add "Post Week to Xero" button
4. Display posting status/results

**Note:** Frontend changes are out of scope for this backend implementation.

## Testing Strategy

1. **Unit Tests:**
   - Leave type identification from job names
   - CostLine categorization logic
   - Xero API payload mapping

2. **Integration Tests:**
   - Xero Payroll API calls (use test/demo environment)
   - End-to-end posting workflow
   - Rate multiplier mapping

3. **Manual Testing:**
   - Test with real Xero Payroll demo company
   - Verify different leave types post correctly
   - Test overtime/rate multipliers

## Migration Notes

### From IMS to Xero Payroll

- Keep `Staff.ims_payroll_id` field for historical reference
- IMS export can be deprecated after Xero Payroll is stable
- No data migration needed (fresh start)

### Staff to Xero Employee Mapping

- Use `Staff.xero_user_id` field (already exists)
- Manual one-time setup to populate xero_user_id for each staff member
- Can use `get_employees()` API call to fetch Xero employee list for matching

## Security Considerations

- Xero Payroll API requires elevated permissions
- Ensure OAuth token refresh handles new scopes
- Validate staff_id and date inputs to prevent unauthorized submissions
- Use defensive programming: fail early on missing xero_user_id

## Future Enhancements (Out of Scope)

- Tracking which entries have been posted to Xero (add fields to CostLine)
- Preventing duplicate submissions
- Leave balance queries from Xero
- Bidirectional sync (if ever needed)
- Bulk posting for multiple staff

## Dependencies

- `xero-python` library (already in use)
- Xero Payroll API access (requires account setup)
- Staff.xero_user_id populated for all active staff

## Rollout Plan

1. Implement backend changes
2. Test with demo Xero Payroll account
3. Populate Staff.xero_user_id for production staff
4. Frontend implements UI changes
5. Parallel run with IMS (verify accuracy)
6. Full cutover to Xero Payroll
7. Deprecate IMS integration
