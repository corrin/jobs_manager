# Xero Payroll Posting Debug Plan

## Rules
- **NO `python -c` or `python manage.py shell -c`** - All scripts must be files
- **All debug scripts go in `scripts/payrun-debug/`** for full audit trail
- Test with ONE staff member first, then expand
- **Xero is master** for pay runs - never create local record without Xero confirmation

## Current State (2025-12-23)

### Calendars
- Old calendar: "Weekly" (`05cc53fb-3684-4d00-9c4e-9cb3a2b52919`) - stuck at 2023
- New calendar: "Weekly TESTING" (`6f47b805-083c-4873-8ece-1af573053f5c`) - starts Aug 2025

### Employees
- All 11 employees DELETED from Xero (manual step done)
- Local Staff records need xero_user_id cleared and employees recreated

### Code Changes Made
- `apps/workflow/api/xero/payroll.py` - Prefers "2025" or "TESTING" calendar
- `apps/workflow/models/company_defaults.py` - Added `xero_payroll_calendar_id` field
- `apps/timesheet/services/payroll_employee_sync.py`:
  - Now reads calendar ID from CompanyDefaults.xero_payroll_calendar_id (configurable)
  - Now reads earnings rate from CompanyDefaults.xero_ordinary_earnings_rate_id (configurable)
  - **Fixed rate limit issue**: No longer calls Xero APIs per-employee for lookup data

### Configuration Required
Before running sync, CompanyDefaults must have:
- `xero_payroll_calendar_id` = "6f47b805-083c-4873-8ece-1af573053f5c" (Weekly TESTING)
- `xero_ordinary_earnings_rate_id` = (need to look up from Xero)

---

## Next Steps

### Step 1: Delete Employees in Xero UI (MANUAL)
Go to: https://go.xero.com/payroll/employees

Delete these 11 employees:
- Scott Brown, Andrew Dickerson, Maria Duke, Derrick Johnson
- Thomas Lyons, Christopher Mejia, Kimberly Sellers, Justin Simpson
- Daniel Sims, Paul Stevens, Randy Trujillo

### Step 2: Clear Local Links
```bash
python scripts/payrun-debug/10_reset_employees_for_new_calendar.py --clear-links
```

### Step 3: Recreate Employees on Weekly 2025
```bash
python manage.py sync_payroll_employees --create
```

### Step 4: Advance Calendar to Dec 2025
Create ~18 pay runs to advance from Aug 2025 to Dec 2025.
Each pay run must be POSTED in Xero UI to advance the calendar.

### Step 5: Test Timesheet Posting
1. Create pay run for target week (Dec 15-21, 2025)
2. Test posting timesheet for ONE staff member: `sara12@example.org`
3. Test posting timesheet for multiple staff

---

## Completed

- [x] Identified corrupted local XeroPayRun record (wrong xero_id)
- [x] Deleted corrupted local record
- [x] Tested 409 error handling - working correctly
- [x] Deleted old 2023-07-10 draft pay run (manual in Xero UI)
- [x] Created "Weekly 2025" calendar in Xero
- [x] Updated code to prefer "Weekly 2025" calendar
- [x] Tested update_employee for calendar change - **DOES NOT WORK** (silently ignores)
- [x] Confirmed delete_employee not available in SDK

---

## Xero Payroll NZ API Limitations

| Operation | API Support | Alternative |
|-----------|-------------|-------------|
| Delete pay run | NO | Manual in Xero UI |
| Delete employee | NO | Manual in Xero UI |
| Update employee calendar | NO (silently ignores) | Delete & recreate |
| Update pay run status | NO | Manual in Xero UI |
| Get employment records | NO (method missing) | Use get_employee |

---

## Key Files

| File | Lines | Description |
|------|-------|-------------|
| `apps/timesheet/views/api.py` | 568-622 | CreatePayRunAPIView |
| `apps/timesheet/views/api.py` | 625-705 | PayRunForWeekAPIView |
| `apps/workflow/api/xero/payroll.py` | 594-679 | `create_pay_run()` |
| `apps/workflow/api/xero/payroll.py` | 727-900 | `post_timesheet()` |
| `apps/workflow/api/xero/payroll.py` | 1135-1293 | `post_staff_week_to_xero()` |
| `apps/timesheet/services/payroll_employee_sync.py` | 216-241 | `_get_weekly_calendar_id()` |

---

## Debug Scripts

All in `scripts/payrun-debug/`:

| Script | Purpose |
|--------|---------|
| `01_test_create_payrun.py` | Test low-level pay run creation |
| `02_test_api_create_payrun.py` | Test API endpoint |
| `05_raw_api_delete_draft.py` | Attempted raw API delete (failed) |
| `07_create_payruns_to_current.py` | Script to advance calendar |
| `08_setup_weekly_2025.py` | Check new calendar setup |
| `09_check_sdk_methods.py` | List SDK methods |
| `10_reset_employees_for_new_calendar.py` | Clear local links for migration |
| `11_check_employment_update.py` | Check employment API capabilities |
| `12_inspect_employee_details.py` | Get full employee details |
| `13_move_employee_to_new_calendar.py` | Attempted bulk move (failed) |
| `14_test_move_one_employee.py` | Test single employee update (failed) |
| `debug_xero_payroll.py` | Full diagnostic script |

---

## Original Bug Investigation

### Finding: NOT REPRODUCIBLE
The corrupted local record issue could not be reproduced. Current code correctly:
- Returns 409 on conflict when Xero already has a pay run
- Does NOT create local record when Xero API fails
- Keeps Xero and local in sync

### Root Cause (Suspected)
The corrupted record likely came from an earlier version of the code or manual intervention.
