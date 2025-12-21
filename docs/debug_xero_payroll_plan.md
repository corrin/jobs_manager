# Xero Payroll Posting Debug Plan

## Rules
- **NO `python -c` or `python manage.py shell -c`** - All scripts must be files
- **All debug scripts go in `scripts/payrun-debug/`** for full audit trail
- Test with ONE staff member first, then expand

## Problem Summary
Posting timesheets to Xero Payroll fails with 500 error. Root causes identified:

1. **Corrupted local data**: Local `XeroPayRun` record had wrong dates (2025-12-15) mapped to a 2023-07-10 Xero pay run ID
2. **Xero constraint**: Only one draft pay run allowed per calendar; existing draft blocks new ones
3. **No validation**: Code doesn't verify the returned Xero ID matches requested dates

## Findings

### What We Discovered
- Local `XeroPayRun` for 2025-12-15 had `xero_id: 141ebf83...` but that ID actually belongs to a 2023-07-10 pay run in Xero
- `payroll_calendar_id` was `None` in the local record (should have been `05cc53fb-3684-4d00-9c4e-9cb3a2b52919`)
- The record was marked `created_locally: True` at `api.py:592`
- Creating a new pay run fails with 409: "There can only be one draft pay run per a calendar"

### Key Files
- `apps/timesheet/views/api.py:568-622` - Creates pay run and local record
- `apps/workflow/api/xero/payroll.py:594-679` - `create_pay_run()` function
- `apps/workflow/api/xero/payroll.py:727-900` - `post_timesheet()` function

## Completed
- [x] Deleted corrupted local XeroPayRun record for 2025-12-15

## TODO

### 1. Test Pay Run Creation Error Handling
- Try to create pay run for Dec 15-21, 2025
- Expected: 409 error "only one draft pay run per calendar" (existing 2023-07-10 draft blocks it)
- **Validate**: Good error message reaches frontend (currently broken - creates bad local data instead)

### 2. Fix Error Reporting to Frontend
**File**: `apps/timesheet/views/api.py`
- Frontend should clearly show 409 error, not silently create corrupted local record
- Investigate how local record got wrong xero_id

### 3. Clear Existing Draft Pay Run
- Post/finalize the 2023-07-10 draft in Xero, OR
- Delete it (if Xero allows)
- This unblocks creating new drafts

### 4. Create Pay Run for Dec 15-21, 2025
- After clearing old draft, create new one
- Validate local record matches Xero data

### 5. Test Posting Timesheet for ONE Staff Member
Staff: `sara12@example.org` (Xero ID `51ea92e3...`)
- 12 time entries, 40 hours

### 6. Test with Multiple Staff
Once single staff works, test with all mapped staff.

## Test Data Available
- Week: 2025-12-15 to 2025-12-21
- 241 time entries total
- 11 staff with Xero mappings
- Staff `sara12@example.org`: 12 entries, 40 hours

## Debug Scripts
All debug scripts in `scripts/payrun-debug/` for audit trail.

Run with:
```bash
python scripts/payrun-debug/debug_xero_payroll.py --week 2025-12-15 --staff-email sara12@example.org
```
