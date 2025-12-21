#!/usr/bin/env python
"""
Reset employees to use the new Weekly 2025 calendar.

Steps:
1. Show local Staff records with xero_user_id
2. Clear xero_user_id from local records
3. Use sync command to recreate employees in Xero on new calendar
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from apps.accounts.models import Staff
from apps.workflow.api.xero.payroll import get_employees, get_payroll_calendars


def main():
    print("=== Reset Employees for Weekly 2025 Calendar ===\n")

    # Step 1: Show local Staff with xero_user_id
    print("1. Local Staff records:")
    active_staff = Staff.objects.filter(date_left__isnull=True)
    print(f"   Total active staff: {active_staff.count()}")

    linked_staff = active_staff.filter(xero_user_id__isnull=False)
    unlinked_staff = active_staff.filter(xero_user_id__isnull=True)

    print(f"   Linked to Xero: {linked_staff.count()}")
    print(f"   Not linked: {unlinked_staff.count()}")

    if linked_staff.exists():
        print("\n   Linked staff:")
        for staff in linked_staff:
            print(f"     - {staff.first_name} {staff.last_name} ({staff.email})")
            print(f"       xero_user_id: {staff.xero_user_id}")

    if unlinked_staff.exists():
        print("\n   Unlinked staff:")
        for staff in unlinked_staff:
            print(f"     - {staff.first_name} {staff.last_name} ({staff.email})")

    # Step 2: Show Xero calendars
    print("\n2. Xero Payroll Calendars:")
    calendars = get_payroll_calendars()
    weekly_2025 = None
    for cal in calendars:
        is_weekly = "WEEKLY" in str(cal.get("calendar_type", "")).upper()
        marker = " <-- WEEKLY" if is_weekly else ""
        print(f"   - {cal['name']} (ID: {cal['id'][:8]}...){marker}")
        if "2025" in cal["name"]:
            weekly_2025 = cal

    if weekly_2025:
        print(f"\n   Target calendar: {weekly_2025['name']} ({weekly_2025['id']})")
    else:
        print("\n   ERROR: No 'Weekly 2025' calendar found!")
        return

    # Step 3: Show Xero employees
    print("\n3. Xero Employees:")
    xero_employees = get_employees()
    print(f"   Total in Xero: {len(xero_employees)}")
    for emp in xero_employees:
        print(f"   - {emp.first_name} {emp.last_name} ({emp.email})")
        print(f"     ID: {emp.employee_id}")

    # Step 4: Instructions
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print(
        """
To reset employees for the new calendar:

1. IN XERO UI: Delete the existing demo employees
   https://go.xero.com/payroll/employees

2. CLEAR LOCAL LINKS: Run this with --clear-links flag

3. UPDATE CODE: Modify _get_weekly_calendar_id() to prefer 'Weekly 2025'

4. RECREATE: Run sync_payroll_employees management command
"""
    )

    # Check for --clear-links flag
    import sys

    if "--clear-links" in sys.argv:
        print("\n>>> Clearing xero_user_id from local Staff records...")
        count = linked_staff.update(xero_user_id=None)
        print(f"    Cleared {count} record(s)")


if __name__ == "__main__":
    main()
