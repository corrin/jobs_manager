"""Xero Payroll NZ API Integration."""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List
from uuid import UUID

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Employee, Timesheet, TimesheetLine

from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger("xero.payroll")


def get_employees() -> List[Employee]:
    """
    Get list of Xero Payroll employees.

    Returns:
        List of Employee objects from Xero

    Raises:
        Exception: If API call fails
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info("Fetching Xero Payroll employees")
        response = payroll_api.get_employees(xero_tenant_id=tenant_id)
        employees = response.employees if response.employees else []
        logger.info(f"Retrieved {len(employees)} employees from Xero Payroll")
        return employees
    except Exception as exc:
        logger.error(f"Failed to get Xero Payroll employees: {exc}", exc_info=True)
        persist_app_error(exc)
        raise


def get_payroll_calendars() -> List[Dict[str, Any]]:
    """
    Get list of Xero Payroll calendars.

    Returns:
        List of payroll calendar dictionaries

    Raises:
        Exception: If API call fails
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info("Fetching Xero Payroll calendars")
        response = payroll_api.get_pay_run_calendars(xero_tenant_id=tenant_id)

        calendars = []
        if response and response.pay_run_calendars:
            for cal in response.pay_run_calendars:
                calendars.append(
                    {
                        "id": cal.payroll_calendar_id,
                        "name": cal.name,
                        "calendar_type": cal.calendar_type,
                        "period_start_date": cal.period_start_date,
                        "period_end_date": cal.period_end_date,
                        "payment_date": cal.payment_date,
                    }
                )

        logger.info(f"Retrieved {len(calendars)} payroll calendars from Xero")
        return calendars
    except Exception as exc:
        logger.error(f"Failed to get Xero Payroll calendars: {exc}", exc_info=True)
        persist_app_error(exc)
        raise


def get_leave_types() -> List[Dict[str, Any]]:
    """
    Get list of Xero Payroll leave types.

    Returns:
        List of leave types with their IDs and names

    Raises:
        Exception: If API call fails
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info("Fetching Xero Payroll leave types")
        response = payroll_api.get_leave_types(xero_tenant_id=tenant_id)

        leave_types = []
        if response and response.leave_types:
            for lt in response.leave_types:
                leave_types.append(
                    {
                        "id": lt.leave_type_id,
                        "name": lt.name,
                    }
                )

        logger.info(f"Retrieved {len(leave_types)} leave types from Xero Payroll")
        return leave_types
    except Exception as exc:
        logger.error(f"Failed to get Xero Payroll leave types: {exc}", exc_info=True)
        persist_app_error(exc)
        raise


def get_earnings_rates() -> List[Dict[str, Any]]:
    """
    Get list of Xero Payroll earnings rates.

    Returns:
        List of earnings rates with their IDs, names, and types

    Raises:
        Exception: If API call fails
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info("Fetching Xero Payroll earnings rates")
        response = payroll_api.get_earnings_rates(xero_tenant_id=tenant_id)

        earnings_rates = []
        if response and response.earnings_rates:
            for rate in response.earnings_rates:
                earnings_rates.append(
                    {
                        "id": rate.earnings_rate_id,
                        "name": rate.name,
                        "earnings_type": rate.earnings_type,
                        "rate_type": rate.rate_type,
                        "type_of_units": rate.type_of_units,
                    }
                )

        logger.info(f"Retrieved {len(earnings_rates)} earnings rates from Xero Payroll")
        return earnings_rates
    except Exception as exc:
        logger.error(f"Failed to get Xero Payroll earnings rates: {exc}", exc_info=True)
        persist_app_error(exc)
        raise


def find_payroll_calendar_for_week(week_start_date: date) -> str:
    """
    Find the payroll calendar ID that matches the given week.

    Args:
        week_start_date: Monday of the week

    Returns:
        Payroll calendar ID

    Raises:
        Exception: If no matching calendar found
    """
    calendars = get_payroll_calendars()

    week_end_date = week_start_date + timedelta(days=6)

    for cal in calendars:
        cal_start = (
            cal["period_start_date"].date()
            if hasattr(cal["period_start_date"], "date")
            else cal["period_start_date"]
        )
        cal_end = (
            cal["period_end_date"].date()
            if hasattr(cal["period_end_date"], "date")
            else cal["period_end_date"]
        )

        # Check if our week falls within this calendar period
        if cal_start <= week_start_date <= cal_end:
            logger.info(f"Found matching calendar: {cal['name']} ({cal['id']})")
            return cal["id"]

    raise Exception(
        f"No payroll calendar found for week {week_start_date} to {week_end_date}. "
        "Check Xero Payroll calendar configuration."
    )


def post_timesheet(
    employee_id: UUID,
    week_start_date: date,
    timesheet_lines: List[Dict[str, Any]],
) -> Timesheet:
    """
    Post a weekly timesheet to Xero Payroll following Xero's workflow:
    1. Find the payroll calendar for this week
    2. Check if timesheet exists for employee + week
    3. If not, create empty timesheet
    4. Add lines individually

    Args:
        employee_id: Xero employee ID (UUID)
        week_start_date: Monday of the week (date)
        timesheet_lines: List of timesheet line entries
            Each dict should contain:
            - date (date): Date for this entry
            - earnings_rate_id (str): Xero earnings rate ID
            - number_of_units (float): Hours

    Returns:
        Timesheet object (existing or newly created)

    Raises:
        Exception: If API call fails or validation fails
    """
    # Validation
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    if not employee_id:
        raise Exception("employee_id is required")

    if not week_start_date:
        raise Exception("week_start_date is required")

    if week_start_date.weekday() != 0:  # Monday = 0
        raise Exception("week_start_date must be a Monday")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info(
            f"Processing timesheet for employee {employee_id}, week starting {week_start_date}"
        )

        # Find the payroll calendar for this week
        payroll_calendar_id = find_payroll_calendar_for_week(week_start_date)

        # Calculate week end date (Sunday)
        week_end_date = week_start_date + timedelta(days=6)

        # Step 1: Check if timesheet already exists
        logger.info(f"Checking for existing timesheet for week {week_start_date}")
        filter_str = f"employeeId=={employee_id}"
        timesheets_response = payroll_api.get_timesheets(
            xero_tenant_id=tenant_id,
            filter=filter_str,
            start_date=week_start_date,
            end_date=week_end_date,
        )

        existing_timesheet = None
        if timesheets_response and timesheets_response.timesheets:
            # Find timesheet matching our week
            for ts in timesheets_response.timesheets:
                if (
                    ts.start_date.date() == week_start_date
                    and ts.end_date.date() == week_end_date
                ):
                    existing_timesheet = ts
                    logger.info(f"Found existing timesheet: {ts.timesheet_id}")
                    break

        # Step 2: Create timesheet if it doesn't exist
        if not existing_timesheet:
            logger.info("Creating new timesheet")
            new_timesheet = Timesheet(
                employee_id=str(employee_id),
                payroll_calendar_id=payroll_calendar_id,
                start_date=week_start_date,
                end_date=week_end_date,
            )

            create_response = payroll_api.create_timesheet(
                xero_tenant_id=tenant_id,
                timesheet=new_timesheet,
            )

            if not create_response or not create_response.timesheet:
                raise Exception("Failed to create timesheet")

            existing_timesheet = create_response.timesheet
            logger.info(f"Created new timesheet: {existing_timesheet.timesheet_id}")

        # Step 3: Add lines individually
        timesheet_id = existing_timesheet.timesheet_id
        logger.info(f"Adding {len(timesheet_lines)} lines to timesheet {timesheet_id}")

        for line_data in timesheet_lines:
            line = TimesheetLine(
                date=line_data["date"],
                earnings_rate_id=line_data["earnings_rate_id"],
                number_of_units=line_data["number_of_units"],
            )

            payroll_api.create_timesheet_line(
                xero_tenant_id=tenant_id,
                timesheet_id=timesheet_id,
                timesheet_line=line,
            )

        # Fetch final timesheet to return
        final_response = payroll_api.get_timesheet(
            xero_tenant_id=tenant_id,
            timesheet_id=timesheet_id,
        )

        if not final_response or not final_response.timesheet:
            raise Exception("Failed to retrieve final timesheet")

        logger.info(
            f"Successfully posted {len(timesheet_lines)} lines to timesheet {timesheet_id}"
        )

        return final_response.timesheet

    except Exception as exc:
        logger.error(
            f"Failed to post timesheet for employee {employee_id}: {exc}",
            exc_info=True,
        )
        persist_app_error(exc)
        raise


def create_employee_leave(
    employee_id: UUID,
    leave_type_id: str,
    start_date: date,
    end_date: date,
    hours_per_day: float,
    description: str = "",
) -> str:
    """
    Create an employee leave record in Xero Payroll.

    Args:
        employee_id: Xero employee ID (UUID)
        leave_type_id: Xero leave type ID (str UUID)
        start_date: First day of leave
        end_date: Last day of leave (inclusive)
        hours_per_day: Hours per day for this leave
        description: Optional description of the leave

    Returns:
        Leave ID (UUID string) from Xero

    Raises:
        Exception: If API call fails or validation fails
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    if not employee_id:
        raise Exception("employee_id is required")

    if not leave_type_id:
        raise Exception("leave_type_id is required")

    if not start_date or not end_date:
        raise Exception("start_date and end_date are required")

    if end_date < start_date:
        raise Exception("end_date cannot be before start_date")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info(
            f"Creating leave for employee {employee_id}: "
            f"{start_date} to {end_date} ({hours_per_day}h/day)"
        )

        # Build leave periods for each day
        from xero_python.payrollnz.models import EmployeeLeave, LeavePeriod

        periods = []
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends (Xero will handle this based on employee's schedule)
            periods.append(
                LeavePeriod(
                    period_start_date=current_date,
                    period_end_date=current_date,
                    number_of_units=hours_per_day,
                    period_status="Approved",  # Auto-approve for our use case
                )
            )
            current_date += timedelta(days=1)

        employee_leave = EmployeeLeave(
            leave_type_id=leave_type_id,
            description=description or f"Leave from {start_date} to {end_date}",
            start_date=start_date,
            end_date=end_date,
            periods=periods,
        )

        response = payroll_api.create_employee_leave(
            xero_tenant_id=tenant_id,
            employee_id=str(employee_id),
            employee_leave=employee_leave,
        )

        if not response or not response.leave:
            raise Exception("Failed to create employee leave")

        leave_id = response.leave.leave_id
        logger.info(f"Successfully created leave record: {leave_id}")

        return str(leave_id)

    except Exception as exc:
        logger.error(
            f"Failed to create leave for employee {employee_id}: {exc}",
            exc_info=True,
        )
        persist_app_error(exc)
        raise
