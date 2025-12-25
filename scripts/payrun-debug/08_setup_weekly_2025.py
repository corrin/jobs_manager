#!/usr/bin/env python
"""
Set up the new Weekly 2025 calendar:
1. Find the new calendar ID
2. Show which employees need to move
3. Move employees to the new calendar
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi

from apps.workflow.api.xero.payroll import get_employees, get_payroll_calendars
from apps.workflow.api.xero.xero import api_client, get_tenant_id


def main():
    print("=== Setup Weekly 2025 Calendar ===\n")

    # Step 1: Find calendars
    print("1. Payroll Calendars:")
    calendars = get_payroll_calendars()
    weekly_2025 = None
    for cal in calendars:
        print(f"   - {cal['name']} (ID: {cal['id']})")
        print(f"     Type: {cal['calendar_type']}")
        print(f"     Period: {cal['period_start_date']} to {cal['period_end_date']}")
        if "2025" in cal["name"]:
            weekly_2025 = cal

    if not weekly_2025:
        print("\n   ERROR: No 'Weekly 2025' calendar found!")
        print("   Please create it in Xero first.")
        return

    print(f"\n   Found Weekly 2025: {weekly_2025['id']}")

    # Step 2: Get employees and their current calendars
    print("\n2. Employees and their calendars:")
    employees = get_employees()

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    needs_move = []
    for emp in employees:
        # Get employment details to find calendar
        try:
            emp_response = payroll_api.get_employments(
                xero_tenant_id=tenant_id,
                employee_id=str(emp.employee_id),
            )
            if emp_response and emp_response.employments:
                for employment in emp_response.employments:
                    cal_id = str(employment.payroll_calendar_id)
                    cal_name = next(
                        (c["name"] for c in calendars if c["id"] == cal_id), "Unknown"
                    )
                    if cal_id != weekly_2025["id"]:
                        needs_move.append(
                            {
                                "employee_id": str(emp.employee_id),
                                "name": f"{emp.first_name} {emp.last_name}",
                                "current_calendar": cal_name,
                            }
                        )
                        print(
                            f"   {emp.first_name} {emp.last_name}: {cal_name} -> needs move"
                        )
                    else:
                        print(f"   {emp.first_name} {emp.last_name}: {cal_name} (OK)")
        except Exception as e:
            print(f"   {emp.first_name} {emp.last_name}: Error - {e}")

    print("\n3. Summary:")
    print(f"   Total employees: {len(employees)}")
    print(f"   Need to move: {len(needs_move)}")

    if not needs_move:
        print("   All employees already on Weekly 2025!")
        return

    print("\n4. Moving employees to Weekly 2025...")
    print("   NOTE: This may require updating employment records via API")
    print("   or may need to be done in Xero UI.")

    # Check if we can update employment
    print("\n   Checking API capabilities...")
    methods = [m for m in dir(payroll_api) if "employment" in m.lower()]
    print(f"   Employment methods: {methods}")


if __name__ == "__main__":
    main()
