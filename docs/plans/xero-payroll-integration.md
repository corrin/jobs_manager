# Xero Payroll Integration

**Date:** 2025-11-03
**Branch:** `feature/xero-payroll`
**Status:** Backend Service Layer Complete - REST API & Frontend Not Implemented

## Overview

Backend service layer for submitting weekly timesheets to Xero Payroll NZ API. Replaces legacy IMS payroll system. Users enter time/leave as CostLine entries, then post entire week to Xero via service call.

**Scope of This PR:**
- Backend service layer and Xero API integration only
- Database migration for Xero Payroll configuration
- Management commands for Xero data retrieval and configuration
- **NOT INCLUDED:** REST API endpoints, frontend UI changes

## Critical Architectural Discovery

**Xero Payroll NZ uses separate APIs for work vs leave:**

- **Work Hours:** Timesheets API (`POST /timesheets`, `POST /timesheets/{id}/lines`)
  - Requires earnings rate ID (Ordinary Time, Time & Half, Double Time)
  - Requires payroll calendar ID matching the week
  - Posted as timesheet lines with `number_of_units` (hours)

- **Leave:** Employee Leave API (`POST /employees/{id}/leave`)
  - Requires leave type ID (Annual Leave, Sick Leave, Other, Unpaid)
  - Posted as EmployeeLeave with LeavePeriod objects
  - Periods auto-approved with `period_status="Approved"`

This differs from original plan which assumed single Timesheets API for all time entries.

## Implementation Approach

1. **Leave Identification**: `Job.get_leave_type()` method pattern-matches job name to determine leave type
2. **Entry Categorization**: `PayrollSyncService._categorize_entries()` splits CostLines into leave vs work
3. **Work Posting**: Maps `CostLine.meta['wage_rate_multiplier']` → earnings rate ID, posts via Timesheets API
4. **Leave Posting**: Groups consecutive leave days by type, posts via Leave API
5. **Configuration**: CompanyDefaults stores mappings for leave type IDs and earnings rate IDs

## Implementation Details

### 1. Database Migration (COMPLETE)
**File:** `apps/workflow/migrations/0170_companydefaults_xero_annual_leave_earnings_rate_id_and_more.py`

Added fields to CompanyDefaults:
- `xero_annual_leave_type_id` - Xero leave type ID for annual leave
- `xero_sick_leave_type_id` - Xero leave type ID for sick leave
- `xero_other_leave_type_id` - Xero leave type ID for other leave
- `xero_unpaid_leave_type_id` - Xero leave type ID for unpaid leave
- `xero_ordinary_earnings_rate_id` - Earnings rate ID for 1.0x ordinary time
- `xero_time_half_earnings_rate_id` - Earnings rate ID for 1.5x overtime
- `xero_double_time_earnings_rate_id` - Earnings rate ID for 2.0x double time

Updated XeroToken default scope to include payroll permissions.

### 2. Xero Payroll API Client (COMPLETE)
**File:** `apps/workflow/api/xero/payroll.py`

Uses `xero_python.payrollnz` (NZ region).

**Implemented functions:**
- `get_employees() -> List[Employee]` - Fetch Xero Payroll employees
- `get_leave_types() -> List[Dict]` - Fetch available leave types
- `get_earnings_rates() -> List[Dict]` - Fetch earnings rates for work time
- `get_payroll_calendars() -> List[Dict]` - Fetch payroll calendar periods
- `find_payroll_calendar_for_week(week_start_date: date) -> str` - Find calendar ID for week
- `post_timesheet(employee_id: UUID, week_start_date: date, timesheet_lines: List[Dict]) -> Timesheet` - Submit work hours
- `create_employee_leave(employee_id: UUID, leave_type_id: str, start_date: date, end_date: date, hours_per_day: float, description: str) -> str` - Submit leave

**Important:** Uses `LeavePeriod` objects (not `EmployeeLeaveperiod`).

### 3. Leave Type Identification (COMPLETE)
**File:** `apps/job/models/job.py:624`

Implemented as `Job.get_leave_type()` method:
```python
def get_leave_type(self) -> str:
    """
    Returns: "annual", "sick", "other", "unpaid", or "N/A"
    """
```

Pattern matches job name against known leave job names.

### 4. Payroll Posting Service (COMPLETE)
**File:** `apps/timesheet/services/payroll_sync.py`

Main service class with methods:
- `post_week_to_xero(staff_id: UUID, week_start_date: date) -> Dict` - Main entry point
- `_categorize_entries(entries: List[CostLine]) -> tuple[List, List]` - Split leave vs work
- `_map_work_entries(entries: List[CostLine], company_defaults) -> List[Dict]` - Map to timesheet lines
- `_post_leave_entries(employee_id: UUID, entries: List[CostLine], company_defaults) -> List[str]` - Post leave, group consecutive days

**Return dict includes:**
- `success`, `xero_timesheet_id`, `xero_leave_ids`, `entries_posted`, `leave_hours`, `work_hours`, `errors`

### 5. Management Commands (COMPLETE)
**File:** `apps/workflow/management/commands/interact_with_xero.py`

Added flags:
- `--payroll-employees` - List Xero employees
- `--payroll-rates` - List earnings rates
- `--payroll-calendars` - List payroll calendars
- `--payroll-leave-types` - List leave types
- `--configure-payroll` - Interactive config for leave type IDs + earnings rate IDs
- `--link-staff` - Link staff to Xero employees by email

### 6. REST API Endpoints (NOT IMPLEMENTED)

No REST API endpoints created. Service layer only accessible via Python code.

**To implement in future:**
- `POST /api/timesheet/post-week-to-xero/` endpoint
- Response serialization
- Request validation

### 7. Jobs API Enhancement (NOT IMPLEMENTED)

`leave_type` field not added to API responses.

**To implement in future:**
- Add `leave_type` to job serializer
- Frontend can then filter/display leave jobs appropriately

## Data Flow

```
User enters hours → CostLine (kind='time', meta={wage_rate_multiplier, staff_id})
                           ↓
                   Job.get_leave_type()
                   (pattern match job name)
                           ↓
         ┌─────────────────┴──────────────┐
         ↓                                ↓
    Leave CostLine                   Work CostLine
    (job returns annual/            (job returns "N/A")
     sick/other/unpaid)
         ↓                                ↓
         └─────────────────┬──────────────┘
                           ↓
          Call PayrollSyncService.post_week_to_xero()
                           ↓
              _categorize_entries()
              (split by leave type)
                           ↓
         ┌─────────────────┴──────────────┐
         ↓                                ↓
   _post_leave_entries()           _map_work_entries()
   Group consecutive days          Map multiplier → earnings_rate_id
         ↓                                ↓
   Xero Leave API                  Xero Timesheets API
   POST /employees/{id}/leave      POST /timesheets
   (LeavePeriod objects)           POST /timesheets/{id}/lines
         ↓                                ↓
   Returns leave_ids               Returns timesheet_id
         └─────────────────┬──────────────┘
                           ↓
                  Return combined result
              {success, xero_timesheet_id,
               xero_leave_ids, hours, errors}
```

## Testing Status

### Tested

- API connectivity verified (Xero API accepts request format)
- Configuration retrieval (fetched 15 leave types, 15 earnings rates from Xero)
- CompanyDefaults mapping configured correctly
- Import correctness (`LeavePeriod` class works)

### Not Tested - Blocked on Xero Demo Company Configuration

**Cannot complete end-to-end testing** due to Xero demo company issues:

1. **Employee Leave Setup Missing**
   - Error: "Need to complete the Leave set-up for this employee before viewing, configuring and requesting leave"
   - Demo employees not configured for leave entitlements in Xero Payroll
   - Blocks: `create_employee_leave()` end-to-end testing

2. **Outdated Payroll Calendars**
   - Only 2023 calendar periods exist (Weekly: Jul 10-16, 2023; Monthly: Aug 2023)
   - No current/valid payroll periods
   - Blocks: `post_timesheet()` for work hours

3. **No Test Data**
   - No CostLine entries matching 2023 calendar periods in database

**To unblock testing:**
- Configure leave entitlements for demo employees in Xero Payroll settings
- Create payroll calendar period for current dates (November 2025)
- Re-run: `PayrollSyncService.post_week_to_xero()`

### Unit Tests

Not implemented. Recommend adding:
- `Job.get_leave_type()` pattern matching tests
- `_categorize_entries()` leave vs work splitting
- `_map_work_entries()` rate multiplier → earnings rate ID mapping
- `_post_leave_entries()` consecutive day grouping logic

## Remaining Work to Complete Feature

### Critical - Required for Feature Completion

1. **Complete Backend Testing**
   - Fix Xero demo company configuration (employee leave setup, current payroll calendars)
   - End-to-end test `PayrollSyncService.post_week_to_xero()` with both work hours and leave
   - Test consecutive day grouping for leave
   - Test all rate multipliers (1.0x, 1.5x, 2.0x)
   - Add unit tests for business logic

2. **REST API Endpoints** (NOT IMPLEMENTED)
   - `POST /api/timesheet/post-week-to-xero/`
   - Request validation (staff_id, week_start_date must be Monday)
   - Response serialization
   - Permission checks (staff can only post their own, managers can post for team)

3. **Jobs API Enhancement** (NOT IMPLEMENTED)
   - Add `leave_type` field to job serializer
   - Required for frontend to filter leave jobs

4. **Frontend Implementation** (NOT IMPLEMENTED)
   - "Post Week to Xero" button in timesheet view
   - Display posting status/results
   - Error handling and user feedback
   - Loading states during posting

### Important - Should Implement Before Production

5. **Duplicate Posting Prevention**
   - Add tracking field to CostLine or create new PostingRecord model
   - Prevent re-posting same week's entries
   - UI indication of already-posted weeks

6. **Production Configuration**
   - Populate `Staff.xero_user_id` for all production staff
   - Use `--link-staff` command, verify matches
   - Configure leave type IDs and earnings rate IDs via `--configure-payroll`

### Post-Launch

7. **IMS Deprecation**
   - Parallel run period (both systems)
   - Verify accuracy against IMS exports
   - Remove IMS export functionality once confident

8. **Enhancements**
   - Leave balance queries from Xero
   - Bulk posting for multiple staff
   - Audit trail improvements

## Rollout Plan Status

| Step | Status | Notes |
|------|--------|-------|
| 1. Implement backend changes | COMPLETE | Service layer done, tested partially |
| 2. Test with demo Xero Payroll | BLOCKED | Demo company config issues |
| 3. Implement REST API endpoints | NOT STARTED | Required for frontend |
| 4. Implement frontend UI | NOT STARTED | Blocked on REST API |
| 5. Populate Staff.xero_user_id | NOT STARTED | Production deployment task |
| 6. Parallel run with IMS | NOT STARTED | Verification phase |
| 7. Full cutover to Xero Payroll | NOT STARTED | After verification |
| 8. Deprecate IMS integration | NOT STARTED | Final cleanup |

## Security Considerations

- Xero Payroll API requires elevated permissions (scope updated in migration 0170)
- OAuth token refresh handles new scopes automatically
- Service layer validates: staff has xero_user_id, week_start is Monday
- REST API layer must validate: staff_id permissions, date inputs
- Defensive programming: fail early on missing xero_user_id

## Dependencies

- `xero-python` library (already in use) - SATISFIED
- Xero Payroll API access - CONFIGURED (demo environment)
- Staff.xero_user_id populated - NOT DONE (production deployment requirement)
- Production Xero Payroll properly configured - NOT VERIFIED
