"""Xero Payroll NZ API Integration."""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import Address, Employee, Timesheet, TimesheetLine

from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.services.error_persistence import persist_and_raise

logger = logging.getLogger("xero.payroll")

# Monkeypatch for Xero Python NZ Payroll API (dev-only, does not affect PROD)
# Problem: when fetching employees, we get an error because the SDK expects all employees to have date of birth,
# but the default contractors of Demo Company don't have date of birth, and the REST API doesn't allow PUTTING dateOfBirth for contractors.
# Result: we can't GET employees and we can't PUT contractors to fix that.
# The monkeypatch below aims to fix that by allowing Employee objects to have None as date of birth.


def _safe_date_of_birth(self, value):
    self._date_of_birth = value


Employee.date_of_birth = Employee.date_of_birth.setter(_safe_date_of_birth)


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
        persist_and_raise(exc)


def create_payroll_employee(employee_data: Dict[str, Any]) -> Employee:
    """
    Create a payroll employee in Xero.

    Args:
        employee_data: Dict containing first_name, last_name, date_of_birth, and address data.

    Returns:
        Newly created Employee object.
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    required_fields = ("first_name", "last_name", "date_of_birth", "address")
    for field in required_fields:
        if not employee_data.get(field):
            raise ValueError(f"{field} is required to create a Xero payroll employee")

    address_data = employee_data["address"]
    address_required_fields = ("address_line1", "city", "post_code")
    for field in address_required_fields:
        if not address_data.get(field):
            raise ValueError(
                f"{field} is required inside the address payload for payroll employees"
            )

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info(
            "Creating Xero Payroll employee for %s %s",
            employee_data.get("first_name"),
            employee_data.get("last_name"),
        )

        address = Address(
            address_line1=address_data["address_line1"],
            address_line2=address_data.get("address_line2"),
            city=address_data["city"],
            suburb=address_data.get("suburb"),
            country_name=address_data.get("country_name"),
            post_code=address_data["post_code"],
        )

        employee = Employee(
            first_name=employee_data["first_name"],
            last_name=employee_data["last_name"],
            date_of_birth=employee_data["date_of_birth"],
            address=address,
            email=employee_data.get("email"),
            phone_number=employee_data.get("phone_number"),
            start_date=employee_data.get("start_date"),
            engagement_type=employee_data.get("engagement_type"),
            gender=employee_data.get("gender"),
            job_title=employee_data.get("job_title"),
        )

        response = payroll_api.create_employee(
            xero_tenant_id=tenant_id,
            employee=employee,
        )

        if not response or not response.employee:
            raise Exception("Failed to create payroll employee in Xero")

        created_employee = response.employee
        logger.info(
            "Created Xero Payroll employee %s (%s %s)",
            created_employee.employee_id,
            created_employee.first_name,
            created_employee.last_name,
        )
        return created_employee
    except Exception as exc:
        logger.error(
            "Failed to create Xero Payroll employee %s %s: %s",
            employee_data.get("first_name"),
            employee_data.get("last_name"),
            exc,
            exc_info=True,
        )
        persist_and_raise(
            exc,
            additional_context={
                "operation": "create_payroll_employee",
                "email": employee_data.get("email"),
            },
        )


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
        persist_and_raise(exc)


def get_pay_runs() -> List[Dict[str, Any]]:
    """
    Get list of Xero Payroll pay runs.

    Returns:
        List of pay run dictionaries with details

    Raises:
        Exception: If API call fails
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info("Fetching Xero Payroll pay runs")
        response = payroll_api.get_pay_runs(xero_tenant_id=tenant_id)

        pay_runs = []
        if response and response.pay_runs:
            for pr in response.pay_runs:
                pay_runs.append(
                    {
                        "pay_run_id": str(pr.pay_run_id) if pr.pay_run_id else None,
                        "payroll_calendar_id": str(pr.payroll_calendar_id)
                        if pr.payroll_calendar_id
                        else None,
                        "period_start_date": pr.period_start_date,
                        "period_end_date": pr.period_end_date,
                        "payment_date": pr.payment_date,
                        "pay_run_status": pr.pay_run_status,
                        "pay_run_type": pr.pay_run_type,
                    }
                )

        logger.info(f"Retrieved {len(pay_runs)} pay runs from Xero Payroll")
        return pay_runs
    except Exception as exc:
        logger.error(f"Failed to get Xero Payroll pay runs: {exc}", exc_info=True)
        persist_and_raise(exc)


def get_pay_run_for_week(week_start_date: date) -> Optional[Dict[str, Any]]:
    """
    Get a single pay run that matches the provided week.

    Args:
        week_start_date: Monday of the week to search for

    Returns:
        Pay run dictionary if found, otherwise None

    Raises:
    ValueError: If week_start_date is not a Monday
        Exception: If fetching pay runs fails
    """
    if week_start_date.weekday() != 0:
        raise ValueError("week_start_date must be a Monday")

    pay_runs = get_pay_runs()
    week_end_date = week_start_date + timedelta(days=6)

    for pay_run in pay_runs:
        start_date = _coerce_xero_date(pay_run.get("period_start_date"))
        end_date = _coerce_xero_date(pay_run.get("period_end_date"))

        logger.info(
            "Evaluating pay run %s: start=%s end=%s status=%s",
            pay_run.get("pay_run_id"),
            start_date,
            end_date,
            pay_run.get("pay_run_status"),
        )

        if start_date == week_start_date and end_date == week_end_date:
            return pay_run

    logger.info(
        "No pay run matched week %s-%s (checked %s runs)",
        week_start_date,
        week_end_date,
        len(pay_runs),
    )
    return None


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
        persist_and_raise(exc)


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
        persist_and_raise(exc)


def _coerce_xero_date(value: Any) -> Optional[date]:
    """Normalize Xero date or datetime payloads (strings, datetimes, dates) into date objects."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        cleaned = value.replace("Z", "")
        try:
            return datetime.fromisoformat(cleaned).date()
        except ValueError:
            try:
                return date.fromisoformat(cleaned.split("T")[0])
            except ValueError:
                return None
    return value


def create_pay_run(
    week_start_date: date,
    payment_date: date = None,
) -> str:
    """
    Create a new pay run in Xero Payroll for the specified week.

    Args:
        week_start_date: Monday of the week
        payment_date: Optional payment date (defaults to Wednesday after period end)

    Returns:
        Pay run ID (UUID string)

    Raises:
        ValueError: If week_start_date is not a Monday
        Exception: If API call fails or no weekly calendar found
    """
    if week_start_date.weekday() != 0:
        raise ValueError("week_start_date must be a Monday")

    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        # Find weekly payroll calendar
        calendars = get_payroll_calendars()
        weekly_calendar = next(
            (c for c in calendars if "weekly" in c["name"].lower()), None
        )
        if not weekly_calendar:
            raise Exception("No weekly payroll calendar found in Xero")

        payroll_calendar_id = weekly_calendar["id"]
        logger.info(f"Using weekly calendar: {payroll_calendar_id}")

        # Calculate period end (Sunday)
        week_end_date = week_start_date + timedelta(days=6)

        # Default payment date: Wednesday after period end (3 days)
        if not payment_date:
            payment_date = week_end_date + timedelta(days=3)

        logger.info(
            f"Creating pay run for period {week_start_date} to {week_end_date}, "
            f"payment date {payment_date}"
        )

        from xero_python.payrollnz.models import PayRun

        pay_run = PayRun(
            payroll_calendar_id=payroll_calendar_id,
            period_start_date=week_start_date,
            period_end_date=week_end_date,
            payment_date=payment_date,
            pay_run_status="Draft",
            pay_run_type="Scheduled",
        )

        response = payroll_api.create_pay_run(
            xero_tenant_id=tenant_id,
            pay_run=pay_run,
        )

        if not response or not response.pay_run:
            raise Exception("Failed to create pay run")

        pay_run_id = str(response.pay_run.pay_run_id)
        logger.info(f"Successfully created pay run: {pay_run_id}")

        return pay_run_id

    except Exception as exc:
        logger.error(
            f"Failed to create pay run for week {week_start_date}: {exc}", exc_info=True
        )
        persist_and_raise(
            exc,
            additional_context={
                "operation": "create_pay_run",
                "week": str(week_start_date),
            },
        )


def find_payroll_calendar_for_week(week_start_date: date) -> str:
    """
    Find the payroll calendar ID by searching pay runs for the given week.

    Verifies the pay run is in Draft status (not Posted/locked).

    Args:
        week_start_date: Monday of the week

    Returns:
        Payroll calendar ID from the matching pay run

    Raises:
        Exception: If no matching pay run found or pay run is already Posted
    """
    pay_runs = get_pay_runs()

    week_end_date = week_start_date + timedelta(days=6)

    logger.info(
        f"Searching {len(pay_runs)} pay runs for week {week_start_date} to {week_end_date}"
    )

    for pr in pay_runs:
        pr_start = (
            pr["period_start_date"].date()
            if hasattr(pr["period_start_date"], "date")
            else pr["period_start_date"]
        )
        pr_end = (
            pr["period_end_date"].date()
            if hasattr(pr["period_end_date"], "date")
            else pr["period_end_date"]
        )

        # Check if this pay run period exactly matches our week
        if pr_start == week_start_date and pr_end == week_end_date:
            # Check if pay run is locked (already posted/finalized)
            if pr["pay_run_status"] == "Posted":
                raise Exception(
                    f"Pay run for week {week_start_date} to {week_end_date} is already Posted "
                    f"and cannot be modified. Pay run ID: {pr['pay_run_id']}"
                )

            calendar_id = pr["payroll_calendar_id"]
            logger.info(
                f"Found matching pay run: {pr['pay_run_id']} "
                f"(status: {pr['pay_run_status']}) with calendar {calendar_id}"
            )
            return calendar_id

    raise Exception(
        f"No pay run found for week {week_start_date} to {week_end_date}. "
        "Create a pay run in Xero Payroll for this period first."
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
    3. If exists, delete all existing lines to avoid duplicates
    4. If not exists, create fresh timesheet
    5. Add lines individually

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

        # Step 2: If timesheet exists, delete all existing lines (to avoid duplicates)
        if existing_timesheet:
            timesheet_id = existing_timesheet.timesheet_id

            # Fetch full timesheet details to get the lines
            full_timesheet_response = payroll_api.get_timesheet(
                xero_tenant_id=tenant_id,
                timesheet_id=timesheet_id,
            )

            if full_timesheet_response and full_timesheet_response.timesheet:
                full_timesheet = full_timesheet_response.timesheet
                if full_timesheet.timesheet_lines:
                    logger.info(
                        f"Deleting {len(full_timesheet.timesheet_lines)} existing lines "
                        f"from timesheet {timesheet_id}"
                    )
                    for line in full_timesheet.timesheet_lines:
                        try:
                            payroll_api.delete_timesheet_line(
                                xero_tenant_id=tenant_id,
                                timesheet_id=timesheet_id,
                                timesheet_line_id=line.timesheet_line_id,
                            )
                        except ValueError as exc:
                            # Xero API bug: may return malformed data, but delete likely succeeded
                            if "Invalid value for `date`" not in str(exc):
                                raise
                    logger.info(
                        f"Deleted all existing lines from timesheet {timesheet_id}"
                    )
        else:
            # Step 3: Create fresh timesheet if none exists
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
            timesheet_id = existing_timesheet.timesheet_id
            logger.info(f"Created new timesheet: {timesheet_id}")

        # Step 4: Add lines individually to the timesheet
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
        persist_and_raise(
            exc,
            additional_context={
                "operation": "post_timesheet",
                "employee_id": str(employee_id),
                "week_start_date": week_start_date.isoformat(),
            },
        )


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
        persist_and_raise(
            exc,
            additional_context={
                "operation": "create_employee_leave",
                "employee_id": str(employee_id),
                "leave_type_id": leave_type_id,
            },
        )
