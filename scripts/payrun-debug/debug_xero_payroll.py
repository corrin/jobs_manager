#!/usr/bin/env python
"""
Debug script for Xero Payroll integration.

This script systematically tests each part of the payroll posting process
to identify where failures occur.

Run with:
    python scripts/debug_xero_payroll.py

Or for a specific week:
    python scripts/debug_xero_payroll.py --week 2025-12-15

Or for a specific staff member:
    python scripts/debug_xero_payroll.py --staff-email user@example.com
"""

import argparse
import os
import sys
from datetime import date, timedelta
from uuid import UUID

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Timesheet, TimesheetLine

from apps.accounts.models import Staff
from apps.job.models.costing import CostLine
from apps.workflow.api.xero.payroll import (
    _categorize_entries,
    _map_work_entries,
    get_earnings_rate_id_by_name,
    get_earnings_rates,
    get_employees,
    get_pay_runs,
    get_payroll_calendars,
)
from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.models import CompanyDefaults


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_success(msg: str) -> None:
    print(f"  [OK] {msg}")


def print_error(msg: str) -> None:
    print(f"  [ERROR] {msg}")


def print_warning(msg: str) -> None:
    print(f"  [WARN] {msg}")


def print_info(msg: str) -> None:
    print(f"  [INFO] {msg}")


def check_tenant_id() -> str | None:
    """Step 1: Check Xero tenant ID configuration."""
    print_header("Step 1: Checking Xero Tenant ID")

    tenant_id = get_tenant_id()
    if not tenant_id:
        print_error("No Xero tenant ID configured!")
        print_info("Run: python manage.py setup_dev_xero")
        return None

    print_success(f"Tenant ID: {tenant_id}")
    return tenant_id


def check_company_defaults() -> CompanyDefaults | None:
    """Step 2: Check company defaults and payroll configuration."""
    print_header("Step 2: Checking Company Defaults")

    try:
        defaults = CompanyDefaults.get_instance()
    except Exception as e:
        print_error(f"Failed to get CompanyDefaults: {e}")
        return None

    print_success(f"Company: {defaults.company_name}")

    # Check earnings rate names (IDs looked up at runtime)
    rates = [
        ("Ordinary Time (1.0x)", defaults.xero_ordinary_earnings_rate_name),
        ("Time and a Half (1.5x)", defaults.xero_time_half_earnings_rate_name),
        ("Double Time (2.0x)", defaults.xero_double_time_earnings_rate_name),
    ]

    for label, rate_name in rates:
        if rate_name:
            print_success(f"{label}: '{rate_name}'")
        else:
            print_warning(f"{label}: NOT CONFIGURED")

    return defaults


def check_payroll_calendars() -> list:
    """Step 3: Check payroll calendars in Xero."""
    print_header("Step 3: Checking Payroll Calendars")

    try:
        calendars = get_payroll_calendars()
        print_success(f"Found {len(calendars)} payroll calendars")
        for cal in calendars:
            print_info(f"  - {cal['name']} (ID: {cal['id']})")
            print_info(f"    Type: {cal['calendar_type']}")
            print_info(
                f"    Period: {cal['period_start_date']} to {cal['period_end_date']}"
            )
        return calendars
    except Exception as e:
        print_error(f"Failed to get payroll calendars: {e}")
        return []


def check_pay_runs(week_start: date) -> dict | None:
    """Step 4: Check pay runs and find one for the week."""
    print_header(f"Step 4: Checking Pay Runs (week of {week_start})")

    try:
        pay_runs = get_pay_runs()
        print_success(f"Found {len(pay_runs)} pay runs total")

        week_end = week_start + timedelta(days=6)
        matching_run = None

        for pr in pay_runs:
            start = pr.get("period_start_date")
            end = pr.get("period_end_date")
            status = pr.get("pay_run_status")

            # Normalize dates
            if hasattr(start, "date"):
                start = start.date()
            if hasattr(end, "date"):
                end = end.date()

            print_info(f"  - Pay Run: {pr['pay_run_id'][:8]}...")
            print_info(f"    Period: {start} to {end}")
            print_info(f"    Status: {status}")

            if start == week_start and end == week_end:
                matching_run = pr
                print_success("    ^ MATCHES target week!")

        if not matching_run:
            print_warning(f"No pay run found for week {week_start} to {week_end}")
            print_info("Create a pay run in Xero for this period first")

        return matching_run
    except Exception as e:
        print_error(f"Failed to get pay runs: {e}")
        return None


def check_earnings_rates() -> list:
    """Step 5: Check earnings rates in Xero."""
    print_header("Step 5: Checking Earnings Rates")

    try:
        rates = get_earnings_rates()
        print_success(f"Found {len(rates)} earnings rates")
        for rate in rates:
            print_info(f"  - {rate['name']}")
            print_info(f"    ID: {rate['id']}")
            print_info(
                f"    Type: {rate['earnings_type']}, Rate Type: {rate['rate_type']}"
            )
        return rates
    except Exception as e:
        print_error(f"Failed to get earnings rates: {e}")
        return []


def check_xero_employees() -> list:
    """Step 6: Check employees in Xero Payroll."""
    print_header("Step 6: Checking Xero Payroll Employees")

    try:
        employees = get_employees()
        print_success(f"Found {len(employees)} employees in Xero Payroll")
        for emp in employees:
            print_info(f"  - {emp.first_name} {emp.last_name}")
            print_info(f"    ID: {emp.employee_id}")
            print_info(f"    Email: {emp.email or 'N/A'}")
        return employees
    except Exception as e:
        print_error(f"Failed to get Xero employees: {e}")
        return []


def check_local_staff() -> list:
    """Step 7: Check local staff and their Xero mappings."""
    print_header("Step 7: Checking Local Staff -> Xero Mapping")

    staff_list = Staff.objects.filter(is_active=True)
    print_success(f"Found {staff_list.count()} active local staff")

    mapped = []
    unmapped = []

    for staff in staff_list:
        if staff.xero_user_id:
            mapped.append(staff)
            print_success(f"  {staff.email} -> {staff.xero_user_id}")
        else:
            unmapped.append(staff)
            print_warning(f"  {staff.email} -> NOT MAPPED")

    if unmapped:
        print_info(f"\n{len(unmapped)} staff members not mapped to Xero.")
        print_info("Sync with: python manage.py seed_xero_from_database")

    return mapped


def check_time_entries(staff: Staff, week_start: date) -> list:
    """Step 8: Check time entries for a staff member."""
    print_header(f"Step 8: Checking Time Entries for {staff.email}")

    week_end = week_start + timedelta(days=6)

    time_entries = CostLine.objects.filter(
        kind="time",
        accounting_date__gte=week_start,
        accounting_date__lte=week_end,
    ).select_related("cost_set__job")

    # Filter to entries for this staff
    staff_entries = [
        entry for entry in time_entries if entry.meta.get("staff_id") == str(staff.id)
    ]

    print_success(f"Found {len(staff_entries)} time entries for {staff.email}")

    for entry in staff_entries[:10]:  # Limit to 10 for display
        job = entry.cost_set.job
        print_info(f"  - Date: {entry.accounting_date}")
        print_info(f"    Job: {job.job_number} - {job.name[:30]}")
        print_info(f"    Hours: {entry.quantity}")
        print_info(
            f"    Rate multiplier: {entry.meta.get('wage_rate_multiplier', 1.0)}"
        )
        print_info(f"    Billable: {entry.meta.get('is_billable', True)}")

    if len(staff_entries) > 10:
        print_info(f"  ... and {len(staff_entries) - 10} more")

    return staff_entries


def categorize_and_map_entries(entries: list, defaults: CompanyDefaults) -> list:
    """Step 9: Categorize and map entries to timesheet lines."""
    print_header("Step 9: Categorizing and Mapping Entries")

    if not entries:
        print_warning("No entries to categorize")
        return []

    try:
        leave_api_entries, timesheet_entries, discarded_entries = _categorize_entries(
            entries
        )
        print_success(f"Leave API entries: {len(leave_api_entries)}")
        print_success(f"Timesheet entries: {len(timesheet_entries)}")
        print_success(f"Discarded entries: {len(discarded_entries)}")

        if not timesheet_entries:
            print_warning("No timesheet entries to map")
            return []

        timesheet_lines = _map_work_entries(timesheet_entries, defaults)
        print_success(f"Mapped to {len(timesheet_lines)} timesheet lines")

        for i, line in enumerate(timesheet_lines[:5]):
            print_info(f"  Line {i+1}:")
            print_info(f"    Date: {line['date']}")
            print_info(f"    Earnings Rate ID: {line['earnings_rate_id']}")
            print_info(f"    Hours: {line['number_of_units']}")

        if len(timesheet_lines) > 5:
            print_info(f"  ... and {len(timesheet_lines) - 5} more")

        return timesheet_lines

    except Exception as e:
        print_error(f"Failed to categorize/map entries: {e}")
        import traceback

        traceback.print_exc()
        return []


def check_existing_timesheet(employee_id: UUID, week_start: date) -> dict | None:
    """Step 10: Check for existing timesheet in Xero."""
    print_header("Step 10: Checking for Existing Timesheet")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)
    week_end = week_start + timedelta(days=6)

    try:
        filter_str = f"employeeId=={employee_id}"
        print_info(f"Querying timesheets with filter: {filter_str}")
        print_info(f"Date range: {week_start} to {week_end}")

        response = payroll_api.get_timesheets(
            xero_tenant_id=tenant_id,
            filter=filter_str,
            start_date=week_start,
            end_date=week_end,
        )

        if response and response.timesheets:
            print_success(f"Found {len(response.timesheets)} timesheets")
            for ts in response.timesheets:
                ts_start = (
                    ts.start_date.date()
                    if hasattr(ts.start_date, "date")
                    else ts.start_date
                )
                ts_end = (
                    ts.end_date.date() if hasattr(ts.end_date, "date") else ts.end_date
                )
                print_info(f"  - Timesheet ID: {ts.timesheet_id}")
                print_info(f"    Period: {ts_start} to {ts_end}")
                print_info(f"    Status: {ts.status}")
                if ts.timesheet_lines:
                    print_info(f"    Lines: {len(ts.timesheet_lines)}")

                if ts_start == week_start and ts_end == week_end:
                    print_success("    ^ This matches our target week!")
                    return {"timesheet_id": str(ts.timesheet_id), "status": ts.status}
        else:
            print_info("No existing timesheets found for this employee/week")

        return None

    except Exception as e:
        print_error(f"Failed to check existing timesheets: {e}")
        import traceback

        traceback.print_exc()
        return None


def try_create_minimal_timesheet(
    employee_id: UUID,
    week_start: date,
    payroll_calendar_id: str,
    earnings_rate_id: str,
) -> bool:
    """Step 11: Try to create a minimal timesheet with one line."""
    print_header("Step 11: Creating Minimal Test Timesheet")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)
    week_end = week_start + timedelta(days=6)

    print_info(f"Employee ID: {employee_id}")
    print_info(f"Payroll Calendar ID: {payroll_calendar_id}")
    print_info(f"Week: {week_start} to {week_end}")
    print_info(f"Earnings Rate ID: {earnings_rate_id}")

    # Create minimal timesheet
    try:
        print_info("Creating timesheet (no lines)...")
        new_timesheet = Timesheet(
            employee_id=str(employee_id),
            payroll_calendar_id=payroll_calendar_id,
            start_date=week_start,
            end_date=week_end,
        )

        print_info(f"Timesheet object: employee_id={new_timesheet.employee_id}")
        print_info(f"  payroll_calendar_id={new_timesheet.payroll_calendar_id}")
        print_info(f"  start_date={new_timesheet.start_date}")
        print_info(f"  end_date={new_timesheet.end_date}")

        create_response = payroll_api.create_timesheet(
            xero_tenant_id=tenant_id,
            timesheet=new_timesheet,
        )

        if create_response and create_response.timesheet:
            timesheet_id = create_response.timesheet.timesheet_id
            print_success(f"Timesheet created: {timesheet_id}")

            # Try adding a minimal line
            print_info("Adding a single test line for 1 hour...")
            test_line = TimesheetLine(
                date=week_start,  # Monday
                earnings_rate_id=earnings_rate_id,
                number_of_units=1.0,
            )

            payroll_api.create_timesheet_line(
                xero_tenant_id=tenant_id,
                timesheet_id=timesheet_id,
                timesheet_line=test_line,
            )

            print_success("Test line added successfully!")
            return True
        else:
            print_error("Failed to create timesheet - no response")
            return False

    except Exception as e:
        print_error(f"Failed to create timesheet: {e}")

        # Parse error details
        error_str = str(e)
        if "500" in error_str:
            print_error("Xero returned 500 Internal Server Error")
            print_info("This usually means:")
            print_info("  1. Invalid employee_id (employee not in Xero Payroll)")
            print_info(
                "  2. Employee missing employment setup (not linked to calendar)"
            )
            print_info("  3. Employee missing salary/wage setup")
            print_info("  4. Invalid payroll_calendar_id")
            print_info("  5. Week dates don't align with pay run period")

        import traceback

        traceback.print_exc()
        return False


def verify_employee_setup(employee_id: UUID) -> dict:
    """Step 12: Verify employee has proper employment and salary setup."""
    print_header("Step 12: Verifying Employee Setup in Xero")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    result = {
        "employee_found": False,
        "has_employment": False,
        "has_salary": False,
        "calendar_id": None,
    }

    try:
        # Get employee details
        print_info(f"Fetching employee details for {employee_id}...")
        response = payroll_api.get_employee(
            xero_tenant_id=tenant_id,
            employee_id=str(employee_id),
        )

        if not response or not response.employee:
            print_error("Employee not found in Xero Payroll!")
            return result

        emp = response.employee
        result["employee_found"] = True
        print_success(f"Found: {emp.first_name} {emp.last_name}")
        print_info(f"  Email: {emp.email}")
        print_info(f"  Date of Birth: {emp.date_of_birth}")
        print_info(f"  Start Date: {emp.start_date}")

        # Check employment
        print_info("\nChecking employment setup...")
        try:
            emp_response = payroll_api.get_employments(
                xero_tenant_id=tenant_id,
                employee_id=str(employee_id),
            )
            if emp_response and emp_response.employments:
                result["has_employment"] = True
                for employment in emp_response.employments:
                    print_success("  Employment found!")
                    print_info(f"    Calendar ID: {employment.payroll_calendar_id}")
                    print_info(f"    Start Date: {employment.start_date}")
                    result["calendar_id"] = str(employment.payroll_calendar_id)
            else:
                print_warning("  No employment record found!")
                print_info("  Employee must be linked to a payroll calendar.")
        except Exception as e:
            print_error(f"  Failed to get employment: {e}")

        # Check salary/wage
        print_info("\nChecking salary/wage setup...")
        try:
            salary_response = payroll_api.get_employee_salary_and_wages(
                xero_tenant_id=tenant_id,
                employee_id=str(employee_id),
            )
            if salary_response and salary_response.salary_and_wages:
                result["has_salary"] = True
                for sw in salary_response.salary_and_wages:
                    print_success("  Salary/Wage found!")
                    print_info(f"    Earnings Rate ID: {sw.earnings_rate_id}")
                    print_info(f"    Rate per unit: {sw.rate_per_unit}")
                    print_info(f"    Payment type: {sw.payment_type}")
                    print_info(f"    Status: {sw.status}")
            else:
                print_warning("  No salary/wage record found!")
                print_info(
                    "  Employee must have a salary/wage for timesheet submission."
                )
        except Exception as e:
            print_error(f"  Failed to get salary/wage: {e}")

        return result

    except Exception as e:
        print_error(f"Failed to verify employee: {e}")
        import traceback

        traceback.print_exc()
        return result


def run_debug(week_start: date, staff_email: str | None = None) -> None:
    """Run the complete debug sequence."""
    print("\n" + "=" * 60)
    print(" XERO PAYROLL DEBUG SCRIPT")
    print(f" Target Week: {week_start} to {week_start + timedelta(days=6)}")
    if staff_email:
        print(f" Target Staff: {staff_email}")
    print("=" * 60)

    # Step 1: Tenant ID
    tenant_id = check_tenant_id()
    if not tenant_id:
        return

    # Step 2: Company defaults
    defaults = check_company_defaults()
    if not defaults:
        return

    # Step 3: Payroll calendars
    check_payroll_calendars()

    # Step 4: Pay runs
    check_pay_runs(week_start)

    # Step 5: Earnings rates
    check_earnings_rates()

    # Step 6: Xero employees
    check_xero_employees()

    # Step 7: Local staff
    mapped_staff = check_local_staff()

    if not mapped_staff:
        print_error("No staff mapped to Xero - cannot continue")
        return

    # Select a staff member
    if staff_email:
        target_staff = next(
            (s for s in mapped_staff if s.email.lower() == staff_email.lower()), None
        )
        if not target_staff:
            print_error(f"Staff member {staff_email} not found or not mapped to Xero")
            return
    else:
        # Use first mapped staff
        target_staff = mapped_staff[0]
        print_info(f"\nUsing first mapped staff: {target_staff.email}")

    # Step 8: Time entries
    entries = check_time_entries(target_staff, week_start)

    # Step 9: Categorize and map
    categorize_and_map_entries(entries, defaults)

    employee_id = UUID(target_staff.xero_user_id)

    # Step 10: Check existing timesheet
    existing = check_existing_timesheet(employee_id, week_start)

    # Step 12: Verify employee setup (do this before trying to create)
    employee_status = verify_employee_setup(employee_id)

    if not employee_status["has_employment"]:
        print_error("\nCannot proceed: Employee has no employment record in Xero")
        print_info("The employee must be linked to a payroll calendar first.")
        print_info("This can be done in Xero Payroll web interface or via API.")
        return

    if not employee_status["has_salary"]:
        print_error("\nCannot proceed: Employee has no salary/wage record in Xero")
        print_info("The employee must have a salary/wage setup first.")
        return

    # Step 11: Try minimal timesheet
    if not existing:
        payroll_calendar_id = employee_status.get("calendar_id")
        if not payroll_calendar_id:
            print_error("Could not determine payroll calendar ID for employee")
            return

        rate_name = defaults.xero_ordinary_earnings_rate_name
        if not rate_name:
            print_error("Ordinary earnings rate name not configured")
            return
        earnings_rate_id = get_earnings_rate_id_by_name(rate_name)

        success = try_create_minimal_timesheet(
            employee_id=employee_id,
            week_start=week_start,
            payroll_calendar_id=payroll_calendar_id,
            earnings_rate_id=earnings_rate_id,
        )

        if success:
            print_success("\nMinimal timesheet created successfully!")
            print_info("The issue is likely in the data being sent, not connectivity.")
        else:
            print_error("\nFailed to create minimal timesheet")
            print_info("Check the error details above for clues.")
    else:
        print_info("\nTimesheet already exists for this week - skipping creation test")

    print("\n" + "=" * 60)
    print(" DEBUG COMPLETE")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Debug Xero Payroll integration")
    parser.add_argument(
        "--week",
        type=str,
        default=None,
        help="Week start date (Monday) in YYYY-MM-DD format. Default: 2025-12-15",
    )
    parser.add_argument(
        "--staff-email",
        type=str,
        default=None,
        help="Email of specific staff member to test",
    )

    args = parser.parse_args()

    if args.week:
        week_start = date.fromisoformat(args.week)
    else:
        # Default to 2025-12-15 as mentioned
        week_start = date(2025, 12, 15)

    # Validate it's a Monday
    if week_start.weekday() != 0:
        print(f"Error: {week_start} is not a Monday!")
        print(f"  (It's a {week_start.strftime('%A')})")
        # Find the previous Monday
        days_since_monday = week_start.weekday()
        monday = week_start - timedelta(days=days_since_monday)
        print(f"  Did you mean {monday}?")
        sys.exit(1)

    run_debug(week_start, args.staff_email)


if __name__ == "__main__":
    main()
