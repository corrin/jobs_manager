# Xero Payroll Integration

**Date:** 2025-11-03
**Updated:** 2025-11-04
**Branch:** `feature/xero-payroll`
**Status:** Backend Complete & Tested - REST API & Frontend Not Implemented

## Overview

Backend service layer for submitting weekly timesheets to Xero Payroll NZ API. Users enter time/leave as CostLine entries, then post entire week to Xero via service call.

**Scope of This PR:**
- Backend service layer and Xero API integration only
- Database migration for Xero Payroll configuration
- Management commands for Xero data retrieval and configuration
- **NOT INCLUDED:** REST API endpoints, frontend UI changes

## Critical Architectural Discovery

**Xero Payroll NZ uses separate APIs and requires explicit pay run creation:**

- **Pay Run Creation:** Must be created BEFORE posting hours
  - `create_pay_run()` - Creates Draft pay run for a week
  - Draft status allows editing, Posted status is locked forever
  - Only one Draft pay run allowed per calendar at a time

- **Work Hours:** Timesheets API (`POST /timesheets`, `POST /timesheets/{id}/lines`)
  - Regular work entries
  - Requires earnings rate ID (Ordinary Time, Time & Half, Double Time)
  - Requires payroll calendar ID matching the week
  - Posted as timesheet lines with `number_of_units` (hours)

- **Annual/Sick Leave:** Employee Leave API (`POST /employees/{id}/leave`)
  - Only for leave types with accruing balances (Annual, Sick)
  - Requires leave type ID
  - Posted as EmployeeLeave with LeavePeriod objects
  - Periods auto-approved with `period_status="Approved"`

- **Unpaid Leave:** Not posted to Xero (no payment, no balance tracking)

**Four-category hour tracking:**
1. Work hours → Timesheets API
2. Other leave hours → Timesheets API (paid, no balance)
3. Annual/Sick hours → Leave API (balanced leave)
4. Unpaid hours → Discarded (not posted)

## Implementation Approach

1. **Pay Run Creation**: `create_pay_run()` creates Draft pay run for week before posting hours
2. **Leave Identification**: `Job.get_leave_type()` method pattern-matches job name to determine leave type
3. **Entry Categorization**: `PayrollSyncService._categorize_entries()` splits CostLines into 3 buckets:
   - Leave API entries (annual, sick)
   - Timesheet entries (work, other leave)
   - Discarded entries (unpaid)
4. **Work Posting**: Maps `CostLine.meta['wage_rate_multiplier']` → earnings rate ID, posts via Timesheets API
5. **Leave Posting**: Groups consecutive leave days by type, posts via Leave API
6. **Duplicate Prevention**: Deletes existing timesheet lines before re-posting (replaces old data)
7. **Lock Detection**: Checks pay run status, fails if already Posted (locked)
8. **Configuration**: CompanyDefaults stores mappings for leave type IDs and earnings rate IDs

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
- `get_pay_runs() -> List[Dict]` - Fetch all pay runs with status
- `create_pay_run(week_start_date: date, payment_date: date = None) -> str` - Create Draft pay run for week
- `find_payroll_calendar_for_week(week_start_date: date) -> str` - Find calendar ID for week, verify Draft status
- `post_timesheet(employee_id: UUID, week_start_date: date, timesheet_lines: List[Dict]) -> Timesheet` - Submit work hours (deletes old lines first)
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
- `_categorize_entries(entries: List[CostLine]) -> tuple[List, List, List]` - Split into 3 buckets (leave API, timesheet, discarded)
- `_map_work_entries(entries: List[CostLine], company_defaults) -> List[Dict]` - Map to timesheet lines
- `_post_leave_entries(employee_id: UUID, entries: List[CostLine], company_defaults) -> List[str]` - Post leave, group consecutive days

**Return dict includes:**
- `success`, `xero_timesheet_id`, `xero_leave_ids`, `entries_posted`, `work_hours`, `other_leave_hours`, `annual_sick_hours`, `unpaid_hours`, `errors`

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

### End-to-End Testing - COMPLETE ✓

Successfully tested full workflow with Tonya Harris (staff_id: 4591546b-8256-4567-89ab-ae35f58e9f43):

1. **Pay Run Creation** ✓
   - Created Draft pay run for Nov 10-16, 2025
   - Payment date: Nov 19, 2025 (Wednesday after period end)
   - Pay run ID: e1c308ab-da45-407f-b1ec-2433e0c6d2fa

2. **Timesheet Posting** ✓
   - Week: Oct 6-12, 2025
   - 22 total entries processed
   - Results breakdown:
     - Work hours: 22h → Posted to Timesheets API
     - Other leave: 3h → Posted to Timesheets API (paid, no balance)
     - Annual/Sick: 3h → Posted to Leave API (2h sick + 1h annual)
     - Unpaid: 12h → Discarded (not posted)

3. **Duplicate Prevention** ✓
   - Re-posting same week deletes old timesheet lines first
   - New lines replace old data (no duplicates)

4. **Lock Detection** ✓
   - `find_payroll_calendar_for_week()` checks pay run status
   - Fails with clear error if pay run is Posted (locked)

5. **Rate Multiplier Mapping** ✓
   - Tested 1.0x, 1.5x, 2.0x wage_rate_multiplier
   - Correctly mapped to Ordinary/Time&Half/Double Time earnings rates

6. **Leave Categorization** ✓
   - All four leave types handled correctly
   - Explicit handling with exception for unknown types

### Unit Tests

Not implemented. Recommend adding:
- `Job.get_leave_type()` pattern matching tests
- `_categorize_entries()` three-bucket splitting
- `_map_work_entries()` rate multiplier → earnings rate ID mapping
- `_post_leave_entries()` consecutive day grouping logic

## Remaining Work to Complete Feature

### Critical - Required for Feature Completion

1. **Complete Backend Testing** ✓ COMPLETE
   - ~~Fix Xero demo company configuration~~ ✓
   - ~~End-to-end test `PayrollSyncService.post_week_to_xero()`~~ ✓
   - ~~Test consecutive day grouping for leave~~ ✓
   - ~~Test all rate multipliers (1.0x, 1.5x, 2.0x)~~ ✓
   - Add unit tests for business logic (optional enhancement)

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

5. **Duplicate Posting Prevention** ✓ COMPLETE
   - ~~Prevent re-posting same week's entries~~ ✓ (deletes old lines before re-posting)
   - UI indication of already-posted weeks (frontend task)
   - Optional: Add PostingRecord model for audit trail (enhancement)

6. **Production Configuration**
   - Populate `Staff.xero_user_id` for all production staff
   - Use `--link-staff` command, verify matches
   - Configure leave type IDs and earnings rate IDs via `--configure-payroll`

### Post-Launch

7. **Enhancements**
   - Leave balance queries from Xero
   - Bulk posting for multiple staff
   - Audit trail improvements

## Rollout Plan Status

| Step | Status | Notes |
|------|--------|-------|
| 1. Implement backend changes | ✓ COMPLETE | Service layer done, fully tested |
| 2. Test with demo Xero Payroll | ✓ COMPLETE | All scenarios tested successfully |
| 3. Implement REST API endpoints | NOT STARTED | Required for frontend |
| 4. Implement frontend UI | NOT STARTED | Blocked on REST API |
| 5. Populate Staff.xero_user_id | NOT STARTED | Production deployment task |
| 6. Full cutover to Xero Payroll | NOT STARTED | After verification |

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
