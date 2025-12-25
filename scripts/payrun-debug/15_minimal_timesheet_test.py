#!/usr/bin/env python
"""
Minimal Xero timesheet test.

Run:
    python scripts/payrun-debug/15_minimal_timesheet_test.py
    python scripts/payrun-debug/15_minimal_timesheet_test.py --execute
"""

import logging
import os
import sys
from datetime import date, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Timesheet, TimesheetLine

from apps.accounts.models import Staff
from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.models import CompanyDefaults, XeroPayRun

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    dry_run = "--execute" not in sys.argv
    week_start = date(2025, 8, 4)
    week_end = week_start + timedelta(days=6)
    logger.info(f"Week: {week_start} to {week_end}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    tenant_id = get_tenant_id()
    if not tenant_id:
        logger.error("No tenant_id")
        return
    logger.info(f"tenant_id: {tenant_id[:8]}...")
    defaults = CompanyDefaults.get_instance()
    earnings_rate_id = defaults.xero_ordinary_earnings_rate_id
    if not earnings_rate_id:
        logger.error("No earnings_rate_id configured")
        return
    logger.info(f"earnings_rate_id: {earnings_rate_id[:8]}...")
    try:
        pay_run = XeroPayRun.objects.get(
            period_start_date=week_start,
            period_end_date=week_end,
        )
    except XeroPayRun.DoesNotExist:
        logger.error(f"No XeroPayRun for {week_start} to {week_end}")
        return
    payroll_calendar_id = str(pay_run.payroll_calendar_id)
    logger.info(f"pay_run.xero_id: {pay_run.xero_id}")
    logger.info(f"pay_run.pay_run_status: {pay_run.pay_run_status}")
    logger.info(f"pay_run.payroll_calendar_id: {payroll_calendar_id[:8]}...")
    if pay_run.pay_run_status == "Posted":
        logger.error("Pay run is Posted")
        return
    staff = Staff.objects.filter(
        date_left__isnull=True, xero_user_id__isnull=False
    ).first()
    if not staff:
        logger.error("No staff with xero_user_id")
        return
    employee_id = staff.xero_user_id
    logger.info(f"staff: {staff.first_name} {staff.last_name}")
    logger.info(f"employee_id: {employee_id}")
    payroll_api = PayrollNzApi(api_client)
    filter_str = f"employeeId=={employee_id}"
    logger.info(f"get_timesheets filter={filter_str}")
    timesheets_response = payroll_api.get_timesheets(
        xero_tenant_id=tenant_id,
        filter=filter_str,
        start_date=week_start,
        end_date=week_end,
    )
    existing_timesheet = None
    if timesheets_response and timesheets_response.timesheets:
        for ts in timesheets_response.timesheets:
            ts_start = (
                ts.start_date.date()
                if hasattr(ts.start_date, "date")
                else ts.start_date
            )
            ts_end = ts.end_date.date() if hasattr(ts.end_date, "date") else ts.end_date
            logger.info(
                f"Found timesheet: {ts.timesheet_id} ({ts_start} to {ts_end}) "
                f"status={ts.status}"
            )
            if ts_start == week_start and ts_end == week_end:
                existing_timesheet = ts
    else:
        logger.info("No existing timesheets")
    if existing_timesheet:
        timesheet_id = existing_timesheet.timesheet_id
        logger.info(f"Using existing timesheet: {timesheet_id}")
    else:
        if dry_run:
            logger.info("DRY RUN - would create timesheet")
            return
        logger.info(
            f"create_timesheet employee_id={employee_id} "
            f"payroll_calendar_id={payroll_calendar_id}"
        )
        new_timesheet = Timesheet(
            employee_id=str(employee_id),
            payroll_calendar_id=payroll_calendar_id,
            start_date=week_start,
            end_date=week_end,
        )
        response = payroll_api.create_timesheet(
            xero_tenant_id=tenant_id,
            timesheet=new_timesheet,
        )
        if not response or not response.timesheet:
            logger.error("create_timesheet returned empty")
            return
        timesheet_id = response.timesheet.timesheet_id
        logger.info(f"Created timesheet: {timesheet_id}")
    if dry_run:
        logger.info("DRY RUN - would add line")
        return
    logger.info(
        f"create_timesheet_line date={week_start} "
        f"earnings_rate_id={earnings_rate_id} units=1.0"
    )
    line = TimesheetLine(
        date=week_start,
        earnings_rate_id=earnings_rate_id,
        number_of_units=1.0,
    )
    payroll_api.create_timesheet_line(
        xero_tenant_id=tenant_id,
        timesheet_id=timesheet_id,
        timesheet_line=line,
    )
    logger.info("Added line")
    logger.info("SUCCESS")


if __name__ == "__main__":
    main()
