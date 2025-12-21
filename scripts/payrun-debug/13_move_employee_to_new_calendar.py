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


def main():
    dry_run = "--execute" not in sys.argv

    print("=== Move Employees to Weekly 2025 Calendar ===")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    # Get calendars
    calendars = get_payroll_calendars()
    old_weekly = next((c for c in calendars if c["name"] == "Weekly"), None)
    weekly_2025 = next((c for c in calendars if "2025" in c["name"]), None)

    if not weekly_2025:
        print("ERROR: No Weekly 2025 calendar found!")
        return

    print(
        f"Old calendar: {old_weekly['name'] if old_weekly else 'N/A'} ({old_weekly['id'][:8] if old_weekly else 'N/A'}...)"
    )
    print(f"New calendar: {weekly_2025['name']} ({weekly_2025['id'][:8]}...)")

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

            if current_cal == weekly_2025["id"]:
                print("   Already on Weekly 2025")
                skipped += 1
                continue

            print(f"   Current calendar: {current_cal[:8]}...")
            print(f"   Will move to: {weekly_2025['id'][:8]}...")

            if dry_run:
                print("   [DRY RUN] Would update")
                moved += 1
                continue

            # Try to update
            updated_emp = Employee(payroll_calendar_id=weekly_2025["id"])

            try:
                update_response = payroll_api.update_employee(
                    xero_tenant_id=tenant_id,
                    employee_id=staff.xero_user_id,
                    employee=updated_emp,
                )
                if update_response and update_response.employee:
                    new_cal = str(update_response.employee.payroll_calendar_id)
                    if new_cal == weekly_2025["id"]:
                        print("   SUCCESS - moved to Weekly 2025")
                        moved += 1
                    else:
                        print(f"   PARTIAL - calendar is now {new_cal[:8]}...")
                        errors += 1
                else:
                    print("   ERROR: Update returned empty response")
                    errors += 1
            except Exception as e:
                print(f"   ERROR updating: {e}")
                errors += 1

        except Exception as e:
            print(f"   ERROR: {e}")
            errors += 1

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"  Moved: {moved}")
    print(f"  Skipped (already on Weekly 2025): {skipped}")
    print(f"  Errors: {errors}")

    if dry_run and moved > 0:
        print(f"\nRun with --execute to actually move {moved} employee(s)")


if __name__ == "__main__":
    main()
