#!/usr/bin/env python
"""
Test delete_timesheet with a REAL timesheet (one with valid lines).

Purpose: Determine if the SDK deserialization bug occurs with valid timesheets
or only with empty/malformed Demo Company data.

This script:
1. Creates a timesheet with valid lines (date, earnings_rate_id, number_of_units)
2. Verifies the timesheet was created correctly
3. Deletes the timesheet (WITHOUT monkeypatch protection)
4. Reports whether the SDK bug occurs

All operations are logged for audit purposes.
"""

import logging
import os
import sys
import time
import traceback
from datetime import date

# Setup path
sys.path.insert(0, "/home/corrin/src/jobs_manager")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")

# Configure logging BEFORE Django setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

import django

django.setup()

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Timesheet, TimesheetLine

from apps.workflow.api.xero.payroll import (
    get_earnings_rates,
    get_employees,
    get_payroll_calendars,
)
from apps.workflow.api.xero.xero import api_client, get_tenant_id


def main():
    logger.info("=" * 60)
    logger.info("TEST: delete_timesheet with valid timesheet lines")
    logger.info("=" * 60)

    # Get tenant
    tenant_id = get_tenant_id()
    logger.info(f"Xero tenant ID: {tenant_id}")

    payroll_api = PayrollNzApi(api_client)

    # Step 1: Get employee
    logger.info("Fetching employees...")
    employees = get_employees()
    employee = employees[0]
    employee_id = str(employee.employee_id)
    logger.info(f"Using employee: {employee.first_name} {employee.last_name}")
    logger.info(f"Employee ID: {employee_id}")

    # Step 2: Get payroll calendar with a usable period
    logger.info("Fetching payroll calendars...")
    calendars = get_payroll_calendars()
    calendar = next((c for c in calendars if "TESTING" in c["name"]), calendars[0])
    calendar_id = calendar["id"]
    logger.info(f"Using calendar: {calendar['name']}")
    logger.info(f"Calendar ID: {calendar_id}")
    logger.info(
        f"Calendar period: {calendar['period_start_date']} to {calendar['period_end_date']}"
    )

    # Step 3: Get earnings rate
    logger.info("Fetching earnings rates...")
    rates = get_earnings_rates()
    ordinary_rate = next((r for r in rates if "Ordinary" in r["name"]), rates[0])
    earnings_rate_id = ordinary_rate["id"]
    logger.info(f"Using earnings rate: {ordinary_rate['name']}")
    logger.info(f"Earnings rate ID: {earnings_rate_id}")

    # Step 4: Define timesheet period (must match calendar)
    # Using dates within the Weekly TESTING calendar period
    start_date = date(2025, 8, 4)  # Monday
    end_date = date(2025, 8, 10)  # Sunday
    logger.info(f"Timesheet period: {start_date} to {end_date}")

    # Step 5: Create timesheet WITH VALID LINES
    logger.info("-" * 40)
    logger.info("CREATING TIMESHEET WITH VALID LINES")
    logger.info("-" * 40)

    line1_date = date(2025, 8, 4)
    line1_units = 8.0
    line2_date = date(2025, 8, 5)
    line2_units = 7.5

    logger.info(
        f"Line 1: date={line1_date}, earnings_rate_id={earnings_rate_id}, units={line1_units}"
    )
    logger.info(
        f"Line 2: date={line2_date}, earnings_rate_id={earnings_rate_id}, units={line2_units}"
    )

    timesheet = Timesheet(
        employee_id=employee_id,
        payroll_calendar_id=calendar_id,
        start_date=start_date,
        end_date=end_date,
        timesheet_lines=[
            TimesheetLine(
                date=line1_date,
                earnings_rate_id=earnings_rate_id,
                number_of_units=line1_units,
            ),
            TimesheetLine(
                date=line2_date,
                earnings_rate_id=earnings_rate_id,
                number_of_units=line2_units,
            ),
        ],
    )

    logger.info("Calling payroll_api.create_timesheet()...")
    create_response = payroll_api.create_timesheet(
        xero_tenant_id=tenant_id,
        timesheet=timesheet,
    )

    if not create_response or not create_response.timesheet:
        logger.error("Failed to create timesheet - no response")
        return 1

    created_timesheet = create_response.timesheet
    timesheet_id = str(created_timesheet.timesheet_id)

    logger.info(f"SUCCESS: Created timesheet {timesheet_id}")
    logger.info(f"Status: {created_timesheet.status}")
    logger.info(f"Total hours: {created_timesheet.total_hours}")
    logger.info(
        f"Lines in response: {len(created_timesheet.timesheet_lines) if created_timesheet.timesheet_lines else 0}"
    )

    if created_timesheet.timesheet_lines:
        for i, line in enumerate(created_timesheet.timesheet_lines):
            logger.info(
                f"  Line {i+1}: date={line.date}, rate_id={line.earnings_rate_id}, units={line.number_of_units}"
            )

    # Step 6: Wait before delete
    logger.info("Waiting 3 seconds before delete...")
    time.sleep(3)

    # Step 7: DELETE the timesheet (this is the test)
    logger.info("-" * 40)
    logger.info("DELETING TIMESHEET (testing SDK deserialization)")
    logger.info("-" * 40)
    logger.info(f"Calling payroll_api.delete_timesheet(timesheet_id={timesheet_id})")

    try:
        delete_response = payroll_api.delete_timesheet(
            xero_tenant_id=tenant_id,
            timesheet_id=timesheet_id,
        )
        logger.info("SUCCESS: delete_timesheet completed without exception")
        logger.info(f"Response type: {type(delete_response)}")
        logger.info(f"Response: {delete_response}")

    except ValueError as exc:
        logger.error("VALUEERROR EXCEPTION CAUGHT")
        logger.error(f"Exception message: {exc}")
        logger.error("Full traceback:")
        traceback.print_exc()

        # Check if this is the known SDK bug
        if "must not be `None`" in str(exc):
            logger.error("")
            logger.error("=" * 60)
            logger.error("CONFIRMED: SDK bug occurs with VALID timesheets too")
            logger.error("The monkeypatch IS required for production")
            logger.error("=" * 60)
            return 2
        else:
            logger.error("Unknown ValueError - not the expected SDK bug")
            return 3

    except Exception as exc:
        logger.error(f"UNEXPECTED EXCEPTION: {type(exc).__name__}")
        logger.error(f"Message: {exc}")
        traceback.print_exc()
        return 4

    # Step 8: Verify deletion
    logger.info("-" * 40)
    logger.info("VERIFYING DELETION")
    logger.info("-" * 40)

    verify_response = payroll_api.get_timesheets(xero_tenant_id=tenant_id)
    still_exists = any(
        str(ts.timesheet_id) == timesheet_id
        for ts in (verify_response.timesheets or [])
    )

    if still_exists:
        logger.error(f"UNEXPECTED: Timesheet {timesheet_id} still exists after delete")
        return 5
    else:
        logger.info(f"CONFIRMED: Timesheet {timesheet_id} no longer exists")

    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST COMPLETE: No SDK bug with valid timesheets")
    logger.info("Monkeypatch may NOT be needed if we always create valid lines")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
