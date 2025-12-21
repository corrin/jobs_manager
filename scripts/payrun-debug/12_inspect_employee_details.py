#!/usr/bin/env python
"""
Get full employee details to see if calendar info is available.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi

from apps.workflow.api.xero.xero import api_client, get_tenant_id


def main():
    print("=== Inspect Employee Details ===\n")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    # Paul Stevens employee ID
    employee_id = "51ea92e3-0d1d-446a-b7a9-0e4083362d98"

    print(f"Getting full details for employee {employee_id[:8]}...\n")

    try:
        response = payroll_api.get_employee(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
        )

        if response and response.employee:
            emp = response.employee
            print("Employee object attributes:")
            for attr in sorted(dir(emp)):
                if not attr.startswith("_"):
                    try:
                        val = getattr(emp, attr)
                        if not callable(val):
                            # Truncate long values
                            val_str = str(val)
                            if len(val_str) > 100:
                                val_str = val_str[:100] + "..."
                            print(f"  {attr}: {val_str}")
                    except Exception:
                        pass

            # Specifically look for calendar-related fields
            print("\n\nCalendar/Employment related:")
            for attr in [
                "payroll_calendar_id",
                "employment",
                "employments",
                "calendar_id",
                "pay_calendar",
            ]:
                if hasattr(emp, attr):
                    print(f"  {attr}: {getattr(emp, attr)}")
                else:
                    print(f"  {attr}: NOT FOUND")

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
