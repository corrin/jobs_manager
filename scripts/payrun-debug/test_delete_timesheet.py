#!/usr/bin/env python
"""Test what actually happens when we call delete_timesheet."""

import os
import sys
import time
import traceback

sys.path.insert(0, "/home/corrin/src/jobs_manager")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")

import django

django.setup()

from datetime import date

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Timesheet, TimesheetLine

from apps.workflow.api.xero.payroll import get_earnings_rates, get_employees
from apps.workflow.api.xero.xero import api_client, get_tenant_id

tenant_id = get_tenant_id()
payroll_api = PayrollNzApi(api_client)

# Use the Draft pay run from DB
payroll_calendar_id = "5815f970-31cf-46d7-a65f-aac3a4bb66b9"
week_start = date(2025, 8, 3)
week_end = date(2025, 8, 9)

print(f"Using pay run period: {week_start} to {week_end}")
print(f"Payroll calendar: {payroll_calendar_id}")

# Get an employee
print("Getting employees...")
employees = get_employees()
employee = employees[0]
employee_id = str(employee.employee_id)
print(f"Using employee: {employee.first_name} {employee.last_name} ({employee_id})")

# Get earnings rates
print("Getting earnings rates...")
rates = get_earnings_rates()
ordinary_rate = next((r for r in rates if "Ordinary" in r["name"]), rates[0])
earnings_rate_id = ordinary_rate["id"]
print(f"Using earnings rate: {ordinary_rate['name']}")

# Create a simple timesheet
print("\nCreating test timesheet...")
test_timesheet = Timesheet(
    employee_id=employee_id,
    payroll_calendar_id=payroll_calendar_id,
    start_date=week_start,
    end_date=week_end,
    timesheet_lines=[
        TimesheetLine(
            date=date(2025, 8, 4),  # Monday
            earnings_rate_id=earnings_rate_id,
            number_of_units=8.0,
        )
    ],
)

create_response = payroll_api.create_timesheet(
    xero_tenant_id=tenant_id,
    timesheet=test_timesheet,
)

if not create_response or not create_response.timesheet:
    print("Failed to create test timesheet!")
    sys.exit(1)

timesheet_id = str(create_response.timesheet.timesheet_id)
print(f"Created timesheet: {timesheet_id}")
print("Waiting 3 seconds...")
time.sleep(3)

print("\n" + "=" * 60)
print("DELETE TIMESHEET TEST")
print("=" * 60 + "\n")

try:
    result = payroll_api.delete_timesheet(
        xero_tenant_id=tenant_id,
        timesheet_id=timesheet_id,
    )
    print("SUCCESS - No exception")
    print(f"Result: {result}")
except ValueError as exc:
    print(f"VALUEERROR: {exc}")
    traceback.print_exc()
except Exception as exc:
    print(f"EXCEPTION: {type(exc).__name__}: {exc}")
    traceback.print_exc()
