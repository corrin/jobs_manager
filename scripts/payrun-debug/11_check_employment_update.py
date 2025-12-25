#!/usr/bin/env python
"""
Check if we can update employee employment records (calendar assignment).

The employment record contains payroll_calendar_id. We need to see if
the API supports updating this.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi

from apps.workflow.api.xero.payroll import get_employees, get_payroll_calendars
from apps.workflow.api.xero.xero import api_client, get_tenant_id


def main():
    print("=== Check Employment Update Capability ===\n")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    # Get calendars
    calendars = get_payroll_calendars()
    weekly_2025 = next((c for c in calendars if "2025" in c["name"]), None)
    if not weekly_2025:
        print("ERROR: No Weekly 2025 calendar found!")
        return

    print(f"Target calendar: {weekly_2025['name']} ({weekly_2025['id']})")

    # Check available employment methods
    print("\n1. Available employment methods in SDK:")
    methods = [m for m in dir(payroll_api) if "employment" in m.lower()]
    for m in sorted(methods):
        print(f"   - {m}")

    # Get a test employee - Paul Stevens (sara12@example.org)
    print("\n2. Getting test employee (Paul Stevens)...")
    employees = get_employees()
    paul = next((e for e in employees if e.email == "sara12@example.org"), None)
    if not paul:
        print("   ERROR: Could not find Paul Stevens")
        return

    print(f"   Found: {paul.first_name} {paul.last_name} (ID: {paul.employee_id})")

    # Try to get employment record
    print("\n3. Getting employment record...")
    try:
        emp_response = payroll_api.get_employments(
            xero_tenant_id=tenant_id,
            employee_id=str(paul.employee_id),
        )
        if emp_response and emp_response.employments:
            for employment in emp_response.employments:
                print(f"   Employment ID: {employment.employment_id}")
                print(f"   Calendar ID: {employment.payroll_calendar_id}")
                # Find calendar name
                cal_name = next(
                    (
                        c["name"]
                        for c in calendars
                        if c["id"] == str(employment.payroll_calendar_id)
                    ),
                    "Unknown",
                )
                print(f"   Calendar Name: {cal_name}")
                print(f"   Start Date: {employment.start_date}")
        else:
            print("   No employment records found")
    except Exception as e:
        print(f"   ERROR getting employment: {e}")

    # Check if update_employment exists
    print("\n4. Checking for update capability...")
    if hasattr(payroll_api, "update_employment"):
        print("   update_employment EXISTS - we might be able to update!")
    else:
        print("   update_employment NOT FOUND")

    if hasattr(payroll_api, "create_employment"):
        print("   create_employment EXISTS")

    # List other potentially useful methods
    print("\n5. All employee/employment related methods:")
    for m in sorted(dir(payroll_api)):
        if any(kw in m.lower() for kw in ["employ", "calendar"]):
            if not m.startswith("_"):
                print(f"   - {m}")


if __name__ == "__main__":
    main()
