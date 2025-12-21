"""Xero Payroll NZ API Integration."""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import (
    Address,
    Employee,
    EmployeeWorkingPatternWithWorkingWeeksRequest,
    Employment,
    SalaryAndWage,
    Timesheet,
    TimesheetLine,
    WorkingWeek,
)

from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.exceptions import AlreadyLoggedException
from apps.workflow.services.error_persistence import (
    persist_and_raise,
    persist_app_error,
)

logger = logging.getLogger("xero.payroll")

# Monkeypatch for Xero Python NZ Payroll API (dev-only, does not affect PROD)
# Problem: when fetching employees, we get an error because the SDK expects all employees to have date of birth,
# but the default contractors of Demo Company don't have date of birth, and the REST API doesn't allow PUTTING dateOfBirth for contractors.
# Result: we can't GET employees and we can't PUT contractors to fix that.
# The monkeypatch below aims to fix that by allowing Employee objects to have None as date of birth.


def _safe_date_of_birth(self, value):
    self._date_of_birth = value


Employee.date_of_birth = Employee.date_of_birth.setter(_safe_date_of_birth)


# Monkeypatch SalaryAndWage to accept null annual_salary (SDK bug for hourly employees)
def _safe_annual_salary(self, value):
    self._annual_salary = value


def _safe_status(self, value):
    self._status = value


SalaryAndWage.annual_salary = SalaryAndWage.annual_salary.setter(_safe_annual_salary)
SalaryAndWage.status = SalaryAndWage.status.setter(_safe_status)


# Same issue for Employment.engagement_type - SDK requires it but Demo Company rejects it
def _safe_engagement_type(self, value):
    self._engagement_type = value


Employment.engagement_type = Employment.engagement_type.setter(_safe_engagement_type)


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
    Create a payroll employee in Xero with full employment setup.

    Creates the employee record, then sets up:
    - Employment (links to payroll calendar)
    - Working pattern (weekly hours)
    - Salary and wage (hourly rate)

    Args:
        employee_data: Dict containing:
            - first_name, last_name, email (required)
            - date_of_birth, start_date, job_title
            - address (dict with address_line1, city, post_code)
            - payroll_calendar_id (required for employment)
            - ordinary_earnings_rate_id (required for salary)
            - hours_per_week (dict with monday-sunday hours)
            - wage_rate (hourly rate)

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
        employee_id = str(created_employee.employee_id)
        logger.info(
            "Created Xero Payroll employee %s (%s %s)",
            employee_id,
            created_employee.first_name,
            created_employee.last_name,
        )

        # Set up employment (links employee to payroll calendar)
        payroll_calendar_id = employee_data.get("payroll_calendar_id")
        if payroll_calendar_id:
            _create_employment(
                payroll_api,
                tenant_id,
                employee_id,
                payroll_calendar_id,
                employee_data.get("start_date"),
            )

        # Set up salary and wage (hourly rate) - MUST be before working pattern
        hours_per_week = employee_data.get("hours_per_week")
        wage_rate = employee_data.get("wage_rate")
        earnings_rate_id = employee_data.get("ordinary_earnings_rate_id")
        if wage_rate and earnings_rate_id:
            _create_salary_and_wage(
                payroll_api,
                tenant_id,
                employee_id,
                earnings_rate_id,
                wage_rate,
                hours_per_week,
                employee_data.get("start_date"),
            )

        # Set up working pattern (weekly hours) - requires salary to exist first
        if hours_per_week:
            _create_working_pattern(
                payroll_api,
                tenant_id,
                employee_id,
                hours_per_week,
                employee_data.get("start_date"),
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


def _create_employment(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
    payroll_calendar_id: str,
    start_date: Optional[date],
) -> None:
    """Create employment record linking employee to payroll calendar."""
    # engagement_type omitted - Demo Company rejects it, prod may need it later
    employment = Employment(
        payroll_calendar_id=payroll_calendar_id,
        start_date=start_date,
    )
    payroll_api.create_employment(
        xero_tenant_id=tenant_id,
        employee_id=employee_id,
        employment=employment,
    )
    logger.info("Created employment for employee %s", employee_id)


def _create_working_pattern(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
    hours_per_week: Dict[str, float],
    effective_from: Optional[date],
) -> None:
    """Create working pattern with weekly hours."""
    working_week = WorkingWeek(
        monday=hours_per_week.get("monday", 0),
        tuesday=hours_per_week.get("tuesday", 0),
        wednesday=hours_per_week.get("wednesday", 0),
        thursday=hours_per_week.get("thursday", 0),
        friday=hours_per_week.get("friday", 0),
        saturday=hours_per_week.get("saturday", 0),
        sunday=hours_per_week.get("sunday", 0),
    )
    pattern_request = EmployeeWorkingPatternWithWorkingWeeksRequest(
        effective_from=effective_from,
        working_weeks=[working_week],
    )
    payroll_api.create_employee_working_pattern(
        xero_tenant_id=tenant_id,
        employee_id=employee_id,
        employee_working_pattern_with_working_weeks_request=pattern_request,
    )
    total_hours = sum(hours_per_week.values())
    logger.info(
        "Created working pattern for employee %s (%.1f hrs/week)",
        employee_id,
        total_hours,
    )


def _create_salary_and_wage(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
    earnings_rate_id: str,
    hourly_rate: float,
    hours_per_week: Optional[Dict[str, float]],
    effective_from: Optional[date],
) -> None:
    """Create salary and wage record with hourly rate."""
    total_hours = sum(hours_per_week.values()) if hours_per_week else 40.0
    # Calculate working days (days with non-zero hours)
    if hours_per_week:
        working_days = sum(1 for h in hours_per_week.values() if h > 0)
    else:
        working_days = 5  # Default Mon-Fri
    hours_per_day = total_hours / working_days if working_days > 0 else 8.0

    # SDK requires annual_salary and status even for hourly employees (client-side validation bugs)
    # These are not meaningful for hourly but SDK enforces them
    salary_and_wage = SalaryAndWage(
        earnings_rate_id=earnings_rate_id,
        number_of_units_per_week=total_hours,
        number_of_units_per_day=hours_per_day,
        days_per_week=working_days,  # Required by API
        rate_per_unit=hourly_rate,
        annual_salary=0,  # Required by SDK, not meaningful for hourly
        status="Active",  # Required by SDK
        effective_from=effective_from,
        payment_type="Hourly",
    )
    payroll_api.create_employee_salary_and_wage(
        xero_tenant_id=tenant_id,
        employee_id=employee_id,
        salary_and_wage=salary_and_wage,
    )
    logger.info(
        "Created salary for employee %s ($%.2f/hr, %.1f hrs/week)",
        employee_id,
        hourly_rate,
        total_hours,
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
                        "payroll_calendar_id": (
                            str(pr.payroll_calendar_id)
                            if pr.payroll_calendar_id
                            else None
                        ),
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


def get_pay_run(pay_run_id: str):
    """
    Get a single pay run from Xero by ID.

    Args:
        pay_run_id: UUID of the pay run in Xero.

    Returns:
        PayRun object from Xero API, or None if not found.

    Raises:
        Exception: If API call fails.
    """
    if not get_tenant_id():
        raise Exception("No Xero tenant ID configured")

    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info(f"Fetching Xero pay run {pay_run_id}")
        response = payroll_api.get_pay_run(
            xero_tenant_id=tenant_id, pay_run_id=pay_run_id
        )

        if response and response.pay_run:
            return response.pay_run
        return None
    except Exception as exc:
        logger.error(f"Failed to get Xero pay run {pay_run_id}: {exc}", exc_info=True)
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
        # Find weekly payroll calendar (prefer "Weekly 2025" if available)
        calendars = get_payroll_calendars()
        weekly_calendars = [c for c in calendars if "weekly" in c["name"].lower()]
        if not weekly_calendars:
            raise Exception("No weekly payroll calendar found in Xero")

        # Prefer "Weekly 2025" calendar if available
        weekly_calendar = next(
            (c for c in weekly_calendars if "2025" in c["name"]), weekly_calendars[0]
        )
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
    Find the payroll calendar ID by searching local pay runs for the given week.

    Verifies the pay run is in Draft status (not Posted/locked).

    Args:
        week_start_date: Monday of the week

    Returns:
        Payroll calendar ID from the matching pay run

    Raises:
        Exception: If no matching pay run found or pay run is already Posted
    """
    from apps.workflow.models import XeroPayRun

    week_end_date = week_start_date + timedelta(days=6)

    logger.info(
        f"Searching local pay runs for week {week_start_date} to {week_end_date}"
    )

    try:
        pay_run = XeroPayRun.objects.get(
            period_start_date=week_start_date,
            period_end_date=week_end_date,
        )
    except XeroPayRun.DoesNotExist:
        raise Exception(
            f"No pay run found for week {week_start_date} to {week_end_date}. "
            "Create a pay run in Xero Payroll for this period first."
        )

    if pay_run.pay_run_status == "Posted":
        raise Exception(
            f"Pay run for week {week_start_date} to {week_end_date} is already Posted "
            f"and cannot be modified. Pay run ID: {pay_run.xero_id}"
        )

    logger.info(
        f"Found matching pay run: {pay_run.xero_id} "
        f"(status: {pay_run.pay_run_status}) with calendar {pay_run.payroll_calendar_id}"
    )
    return str(pay_run.payroll_calendar_id)


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


# =============================================================================
# Sync-focused API functions
# These return raw Xero objects for use by the sync system
# =============================================================================


def get_pay_runs_for_sync(**kwargs):
    """
    Fetch pay runs from Xero Payroll API for sync purposes.

    Returns raw PayRun objects (not converted to dicts) so they can be
    serialized to raw_json by the sync system.

    Returns:
        Object with .pay_runs attribute containing list of PayRun objects
    """
    tenant_id = kwargs.get("xero_tenant_id") or get_tenant_id()
    if not tenant_id:
        logger.warning("No Xero tenant ID configured for payroll sync")
        return type("obj", (object,), {"pay_runs": []})()

    payroll_api = PayrollNzApi(api_client)

    try:
        logger.info("Fetching Xero pay runs for sync")
        response = payroll_api.get_pay_runs(xero_tenant_id=tenant_id)

        if response and response.pay_runs:
            logger.info(f"Retrieved {len(response.pay_runs)} pay runs for sync")
            return response
        return type("obj", (object,), {"pay_runs": []})()
    except Exception as exc:
        logger.error(f"Failed to get pay runs for sync: {exc}", exc_info=True)
        # Don't raise - let sync continue with empty list
        return type("obj", (object,), {"pay_runs": []})()


def get_pay_slips_for_sync(pay_run_id: str, **kwargs):
    """
    Fetch pay slips for a specific pay run from Xero Payroll API.

    Returns raw PaySlip objects (not converted to dicts) so they can be
    serialized to raw_json by the sync system.

    Args:
        pay_run_id: The Xero pay run ID to fetch slips for

    Returns:
        Object with .pay_slips attribute containing list of PaySlip objects
    """
    tenant_id = kwargs.get("xero_tenant_id") or get_tenant_id()
    if not tenant_id:
        logger.warning("No Xero tenant ID configured for payroll sync")
        return type("obj", (object,), {"pay_slips": []})()

    payroll_api = PayrollNzApi(api_client)

    try:
        logger.debug(f"Fetching pay slips for pay run {pay_run_id}")
        response = payroll_api.get_pay_slips(
            xero_tenant_id=tenant_id, pay_run_id=pay_run_id
        )

        if response and response.pay_slips:
            logger.debug(f"Retrieved {len(response.pay_slips)} pay slips")
            return response
        return type("obj", (object,), {"pay_slips": []})()
    except Exception as exc:
        logger.error(
            f"Failed to get pay slips for pay run {pay_run_id}: {exc}", exc_info=True
        )
        # Don't raise - let sync continue with empty list
        return type("obj", (object,), {"pay_slips": []})()


def get_all_pay_slips_for_sync(**kwargs):
    """
    Fetch ALL pay slips across ALL pay runs from Xero Payroll API.

    This iterates through all pay runs and fetches their pay slips.
    Note: This makes N+1 API calls (1 for pay runs, N for each pay run's slips).

    Returns:
        Object with .pay_slips attribute containing list of all PaySlip objects
    """
    tenant_id = kwargs.get("xero_tenant_id") or get_tenant_id()
    if not tenant_id:
        logger.warning("No Xero tenant ID configured for payroll sync")
        return type("obj", (object,), {"pay_slips": []})()

    payroll_api = PayrollNzApi(api_client)

    try:
        # First get all pay runs
        logger.info("Fetching all pay runs to gather pay slips")
        pay_runs_response = payroll_api.get_pay_runs(xero_tenant_id=tenant_id)

        if not pay_runs_response or not pay_runs_response.pay_runs:
            logger.info("No pay runs found")
            return type("obj", (object,), {"pay_slips": []})()

        all_pay_slips = []
        for pay_run in pay_runs_response.pay_runs:
            pay_run_id = str(pay_run.pay_run_id)
            logger.debug(f"Fetching pay slips for pay run {pay_run_id}")

            try:
                slips_response = payroll_api.get_pay_slips(
                    xero_tenant_id=tenant_id, pay_run_id=pay_run_id
                )
                if slips_response and slips_response.pay_slips:
                    # Add pay_run reference to each slip for context
                    for slip in slips_response.pay_slips:
                        slip._pay_run = pay_run  # Attach parent for transform
                    all_pay_slips.extend(slips_response.pay_slips)
            except Exception as exc:
                logger.warning(
                    f"Failed to get pay slips for pay run {pay_run_id}: {exc}"
                )
                continue

        logger.info(f"Retrieved {len(all_pay_slips)} total pay slips for sync")
        return type("obj", (object,), {"pay_slips": all_pay_slips})()

    except Exception as exc:
        logger.error(f"Failed to get all pay slips for sync: {exc}", exc_info=True)
        return type("obj", (object,), {"pay_slips": []})()


def post_staff_week_to_xero(staff_id: UUID, week_start_date: date) -> Dict[str, Any]:
    """
    Post a week's timesheet to Xero Payroll for a specific staff member.

    Args:
        staff_id: UUID of the staff member
        week_start_date: Monday of the week to post (must be a Monday)

    Returns:
        Dict containing:
            - success (bool): Whether the post was successful
            - xero_timesheet_id (str): Xero timesheet ID if successful
            - entries_posted (int): Number of entries posted
            - work_hours (Decimal): Total work hours
            - other_leave_hours (Decimal): Total other leave hours
            - annual_sick_hours (Decimal): Total annual/sick leave hours
            - unpaid_hours (Decimal): Total unpaid hours (not posted)
            - errors (List[str]): Any errors encountered

    Raises:
        ValueError: If inputs are invalid
        AlreadyLoggedException: If Xero API call fails
    """
    from apps.accounts.models import Staff
    from apps.job.models.costing import CostLine
    from apps.workflow.models import CompanyDefaults

    # Validate inputs
    if week_start_date.weekday() != 0:
        raise ValueError("week_start_date must be a Monday")

    try:
        staff = Staff.objects.get(id=staff_id)
    except Staff.DoesNotExist as exc:
        raise ValueError("Staff member not found") from exc

    if not staff.xero_user_id:
        raise ValueError(
            f"Staff member {staff.email} does not have a xero_user_id configured"
        )

    try:
        # Calculate week end date (Sunday)
        week_end_date = week_start_date + timedelta(days=6)

        logger.info(
            f"Collecting timesheet entries for {staff.email} "
            f"from {week_start_date} to {week_end_date}"
        )

        # Collect time entries for the week
        time_entries = CostLine.objects.filter(
            kind="time",
            accounting_date__gte=week_start_date,
            accounting_date__lte=week_end_date,
        ).select_related("cost_set__job")

        # Filter to entries for this staff
        staff_entries = [
            entry
            for entry in time_entries
            if entry.meta.get("staff_id") == str(staff_id)
        ]

        if not staff_entries:
            logger.warning(
                f"No timesheet entries found for {staff.email} "
                f"in week {week_start_date}"
            )
            return {
                "success": True,
                "xero_timesheet_id": None,
                "entries_posted": 0,
                "work_hours": Decimal("0"),
                "other_leave_hours": Decimal("0"),
                "annual_sick_hours": Decimal("0"),
                "unpaid_hours": Decimal("0"),
                "errors": [],
            }

        # Get company defaults for mappings
        company_defaults = CompanyDefaults.get_instance()

        # Categorize entries into three buckets
        leave_api_entries, timesheet_entries, discarded_entries = _categorize_entries(
            staff_entries
        )

        # Further split timesheet entries into work vs other leave
        work_entries = []
        other_leave_entries = []
        for entry in timesheet_entries:
            job = entry.cost_set.job
            leave_type = job.get_leave_type()
            if leave_type == "other":
                other_leave_entries.append(entry)
            else:
                work_entries.append(entry)

        xero_employee_id = UUID(staff.xero_user_id)
        xero_timesheet_id = None
        leave_ids = []

        # Post timesheet entries (work + other leave)
        if timesheet_entries:
            timesheet_lines = _map_work_entries(timesheet_entries, company_defaults)
            logger.info(f"Posting {len(timesheet_lines)} timesheet entries to Xero")

            timesheet = post_timesheet(
                employee_id=xero_employee_id,
                week_start_date=week_start_date,
                timesheet_lines=timesheet_lines,
            )
            xero_timesheet_id = str(timesheet.timesheet_id)
            logger.info(f"Successfully posted timesheet {xero_timesheet_id}")

        # Post leave entries using Leave API (annual/sick only)
        if leave_api_entries:
            leave_ids = _post_leave_entries(
                xero_employee_id, leave_api_entries, company_defaults
            )
            logger.info(f"Successfully posted {len(leave_ids)} leave records")

        # Calculate hours by all four categories
        work_hours = sum(Decimal(str(entry.quantity)) for entry in work_entries)
        other_leave_hours = sum(
            Decimal(str(entry.quantity)) for entry in other_leave_entries
        )
        annual_sick_hours = sum(
            Decimal(str(entry.quantity)) for entry in leave_api_entries
        )
        unpaid_hours = sum(Decimal(str(entry.quantity)) for entry in discarded_entries)

        return {
            "success": True,
            "xero_timesheet_id": xero_timesheet_id,
            "xero_leave_ids": leave_ids,
            "entries_posted": len(staff_entries),
            "work_hours": work_hours,
            "other_leave_hours": other_leave_hours,
            "annual_sick_hours": annual_sick_hours,
            "unpaid_hours": unpaid_hours,
            "errors": [],
        }

    except AlreadyLoggedException:
        raise
    except Exception as exc:
        logger.error(
            f"Failed to post timesheet for staff {staff_id}: {exc}", exc_info=True
        )
        app_error = persist_app_error(
            exc,
            additional_context={
                "staff_id": str(staff_id),
                "week_start_date": week_start_date.isoformat(),
            },
        )
        raise AlreadyLoggedException(exc, app_error.id)


def _categorize_entries(entries: List) -> tuple:
    """
    Categorize cost line entries for Xero posting.

    Args:
        entries: List of CostLine entries to categorize

    Returns:
        Tuple of (leave_api_entries, timesheet_entries, discarded_entries)
        - leave_api_entries: Annual/Sick leave (has balances, use Leave API)
        - timesheet_entries: Work + Other leave (paid hours, use Timesheets API)
        - discarded_entries: Unpaid leave (not posted to Xero)
    """
    leave_api_entries = []  # Annual, Sick (Leave API)
    timesheet_entries = []  # Work, Other Leave (Timesheets API)
    discarded_entries = []  # Unpaid (not posted)

    for entry in entries:
        job = entry.cost_set.job
        leave_type = job.get_leave_type()

        if leave_type == "annual":
            leave_api_entries.append(entry)
        elif leave_type == "sick":
            leave_api_entries.append(entry)
        elif leave_type == "other":
            # Other leave is paid but has no balance - post as timesheet
            timesheet_entries.append(entry)
        elif leave_type == "unpaid":
            # Unpaid leave - don't post to Xero
            discarded_entries.append(entry)
        elif leave_type == "N/A":
            # Regular work hours
            timesheet_entries.append(entry)
        else:
            raise ValueError(
                f"Unknown leave type '{leave_type}' for job {job.job_number}. "
                "Expected: annual, sick, other, unpaid, or N/A"
            )

    return leave_api_entries, timesheet_entries, discarded_entries


def _map_work_entries(entries: List, company_defaults) -> List[Dict[str, Any]]:
    """
    Map work CostLine entries to Xero Payroll timesheet lines format.

    Args:
        entries: List of work CostLine entries
        company_defaults: CompanyDefaults instance with earnings rate mappings

    Returns:
        List of timesheet line dictionaries for Xero API
    """
    timesheet_lines = []

    for entry in entries:
        rate_multiplier = entry.meta.get("wage_rate_multiplier", 1.0)

        # Map rate_multiplier to earnings rate field
        rate_mapping = {
            2.0: ("xero_double_time_earnings_rate_id", "Double time"),
            1.5: ("xero_time_half_earnings_rate_id", "Time and a half"),
            1.0: ("xero_ordinary_earnings_rate_id", "Ordinary time"),
        }

        field_name, rate_name = rate_mapping.get(
            rate_multiplier, ("xero_ordinary_earnings_rate_id", "Ordinary time")
        )
        earnings_rate_id = getattr(company_defaults, field_name)

        if not earnings_rate_id:
            raise ValueError(
                f"{rate_name} earnings rate not configured. "
                "Run: python manage.py interact_with_xero --configure-payroll"
            )

        timesheet_lines.append(
            {
                "date": entry.accounting_date,
                "earnings_rate_id": earnings_rate_id,
                "number_of_units": float(entry.quantity),
            }
        )

    return timesheet_lines


def _post_leave_entries(
    employee_id: UUID,
    entries: List,
    company_defaults,
) -> List[str]:
    """
    Post leave CostLine entries to Xero using the Leave API.

    Groups consecutive days of the same leave type together.

    Args:
        employee_id: Xero employee ID
        entries: List of leave CostLine entries
        company_defaults: CompanyDefaults instance with leave type ID mappings

    Returns:
        List of leave IDs created in Xero
    """
    # Map leave type to leave_type_id field
    leave_mapping = {
        "annual": ("xero_annual_leave_type_id", "Annual leave"),
        "sick": ("xero_sick_leave_type_id", "Sick leave"),
        "other": ("xero_other_leave_type_id", "Other leave"),
        "unpaid": ("xero_unpaid_leave_type_id", "Unpaid leave"),
    }

    # Group entries by leave type and sort by date
    grouped = defaultdict(list)
    for entry in entries:
        job = entry.cost_set.job
        leave_type = job.get_leave_type()

        if leave_type not in leave_mapping:
            raise ValueError(f"Unknown leave type: {leave_type}")

        grouped[leave_type].append(entry)

    # Sort each group by date
    for leave_type in grouped:
        grouped[leave_type].sort(key=lambda e: e.accounting_date)

    leave_ids = []

    # Process each leave type
    for leave_type, type_entries in grouped.items():
        field_name, leave_name = leave_mapping[leave_type]
        leave_type_id = getattr(company_defaults, field_name)

        if not leave_type_id:
            raise ValueError(
                f"{leave_name} type ID not configured. "
                "Run: python manage.py interact_with_xero --configure-payroll"
            )

        # Group consecutive days together
        if not type_entries:
            continue

        current_start = type_entries[0].accounting_date
        current_end = type_entries[0].accounting_date
        current_hours = float(type_entries[0].quantity)

        for i in range(1, len(type_entries)):
            entry = type_entries[i]
            expected_next = current_end + timedelta(days=1)

            # Check if consecutive and same hours per day
            if (
                entry.accounting_date == expected_next
                and abs(float(entry.quantity) - current_hours) < 0.01
            ):
                # Extend current range
                current_end = entry.accounting_date
            else:
                # Create leave for current range
                leave_id = create_employee_leave(
                    employee_id=employee_id,
                    leave_type_id=leave_type_id,
                    start_date=current_start,
                    end_date=current_end,
                    hours_per_day=current_hours,
                    description=f"{leave_name}",
                )
                leave_ids.append(leave_id)

                # Start new range
                current_start = entry.accounting_date
                current_end = entry.accounting_date
                current_hours = float(entry.quantity)

        # Create leave for final range
        leave_id = create_employee_leave(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=current_start,
            end_date=current_end,
            hours_per_day=current_hours,
            description=f"{leave_name}",
        )
        leave_ids.append(leave_id)

    return leave_ids
