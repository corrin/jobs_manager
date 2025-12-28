#!/usr/bin/env python
"""
Test moving ONE employee to Weekly 2025 calendar.
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Employee

from apps.workflow.api.xero.payroll import get_payroll_calendars
from apps.workflow.api.xero.xero import api_client, get_tenant_id


def main():
    dry_run = "--execute" not in sys.argv

    print("=== Test Move ONE Employee to Weekly 2025 ===")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    # Paul Stevens
    employee_id = "51ea92e3-0d1d-446a-b7a9-0e4083362d98"
    employee_name = "Paul Stevens"

    # Get calendars
    calendars = get_payroll_calendars()
    weekly_2025 = next((c for c in calendars if "2025" in c["name"]), None)

    if not weekly_2025:
        print("ERROR: No Weekly 2025 calendar found!")
        return

    print(f"Target calendar: {weekly_2025['name']} ({weekly_2025['id']})")

    # Get current employee details
    print(f"\nGetting {employee_name}...")
    response = payroll_api.get_employee(
        xero_tenant_id=tenant_id,
        employee_id=employee_id,
    )

    if not response or not response.employee:
        print("ERROR: Could not get employee")
        return

    emp = response.employee
    print(f"Current calendar: {emp.payroll_calendar_id}")

    if str(emp.payroll_calendar_id) == weekly_2025["id"]:
        print("Already on Weekly 2025!")
        return

    if dry_run:
        print("\n[DRY RUN] Would update to Weekly 2025")
        print("Run with --execute to actually update")
        return

    print("\nUpdating to Weekly 2025...")

    # Create update payload - copy all required fields from existing employee
    updated_emp = Employee(
        first_name=emp.first_name,
        last_name=emp.last_name,
        date_of_birth=emp.date_of_birth,
        address=emp.address,  # Already an Address object
        payroll_calendar_id=weekly_2025["id"],
    )

    try:
        update_response = payroll_api.update_employee(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
            employee=updated_emp,
        )

        if update_response and update_response.employee:
            new_cal = str(update_response.employee.payroll_calendar_id)
            print(f"New calendar: {new_cal}")
            if new_cal == weekly_2025["id"]:
                print("SUCCESS!")
            else:
                print("FAILED - calendar not changed")
        else:
            print("ERROR: Empty response from update")

    except Exception as e:
        print(f"ERROR: {e}")

        # Check if employee still has old calendar
        check = payroll_api.get_employee(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
        )
        if check and check.employee:
            print(f"Employee calendar is now: {check.employee.payroll_calendar_id}")


if __name__ == "__main__":
    main()
