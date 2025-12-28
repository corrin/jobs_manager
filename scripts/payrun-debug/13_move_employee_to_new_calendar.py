#!/usr/bin/env python
"""
Try to move employees to the new Weekly 2025 calendar.
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Employee

from apps.accounts.models import Staff
from apps.workflow.api.xero.payroll import get_payroll_calendars
from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.models import CompanyDefaults


def main():
    dry_run = "--execute" not in sys.argv

    company = CompanyDefaults.get_instance()
    target_calendar_name = company.xero_payroll_calendar_name

    print(f"=== Move Employees to '{target_calendar_name}' Calendar ===")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    # Get calendars - use exact match since there may be similar names
    calendars = get_payroll_calendars()
    target_calendar = next(
        (c for c in calendars if c["name"] == target_calendar_name),
        None,
    )

    if not target_calendar:
        print(f"ERROR: Calendar '{target_calendar_name}' not found in Xero!")
        print("Available calendars:", [c["name"] for c in calendars])
        return

    print(
        f"Target calendar: {target_calendar['name']} ({target_calendar['id'][:8]}...)"
    )

    # Get staff with xero_user_id
    linked_staff = Staff.objects.filter(
        date_left__isnull=True, xero_user_id__isnull=False
    )

    print(f"\nLinked staff to move: {linked_staff.count()}")

    moved = 0
    skipped = 0
    errors = 0

    for staff in linked_staff:
        print(f"\n--- {staff.first_name} {staff.last_name} ({staff.email}) ---")

        # Get current employee details from Xero
        try:
            response = payroll_api.get_employee(
                xero_tenant_id=tenant_id,
                employee_id=staff.xero_user_id,
            )

            if not response or not response.employee:
                print("   ERROR: Could not get employee from Xero")
                errors += 1
                continue

            emp = response.employee
            current_cal = str(emp.payroll_calendar_id)

            if current_cal == target_calendar["id"]:
                print(f"   Already on {target_calendar['name']}")
                skipped += 1
                continue

            print(f"   Current calendar: {current_cal[:8]}...")
            print(f"   Will move to: {target_calendar['id'][:8]}...")

            if dry_run:
                print("   [DRY RUN] Would update")
                moved += 1
                continue

            # Try to update - must include all required fields
            updated_emp = Employee(
                first_name=emp.first_name,
                last_name=emp.last_name,
                date_of_birth=emp.date_of_birth,
                address=emp.address,
                payroll_calendar_id=target_calendar["id"],
            )

            update_response = payroll_api.update_employee(
                xero_tenant_id=tenant_id,
                employee_id=staff.xero_user_id,
                employee=updated_emp,
            )
            if not update_response or not update_response.employee:
                raise ValueError("Update returned empty response")

            new_cal = str(update_response.employee.payroll_calendar_id)
            if new_cal != target_calendar["id"]:
                raise ValueError(f"Calendar update failed - got {new_cal[:8]}...")

            print(f"   SUCCESS - moved to {target_calendar['name']}")
            moved += 1

        except Exception as e:
            print(f"   ERROR: {e}")
            raise

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"  Moved: {moved}")
    print(f"  Skipped (already on {target_calendar['name']}): {skipped}")
    print(f"  Errors: {errors}")

    if dry_run and moved > 0:
        print(f"\nRun with --execute to actually move {moved} employee(s)")


if __name__ == "__main__":
    main()
