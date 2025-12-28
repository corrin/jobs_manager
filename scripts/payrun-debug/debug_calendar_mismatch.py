#!/usr/bin/env python
"""Comprehensive debug for: "The timesheet dates don't match any of the pay period dates"

This script investigates ALL possible causes of this Xero error.
"""

import os
import sys
from datetime import date

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from xero_python.payrollnz import PayrollNzApi

from apps.accounts.models import Staff
from apps.workflow.api.xero.payroll import get_employees, get_payroll_calendars
from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.models import XeroPayRun

# Employee IDs from the logs
FAILING_EMPLOYEE_ID = "8645c4de-89f8-4284-a3cb-81c27ce08822"
SUCCESS_EMPLOYEE_ID = "c9a044ef-0235-4d84-aa0a-dd3aa2e8f95c"

# Week that failed
WEEK_START = date(2025, 8, 4)
WEEK_END = date(2025, 8, 10)


def get_employee_employment(employee_id):
    """Fetch employment details for an employee."""
    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)
    try:
        response = payroll_api.get_employments(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
        )
        return response.employments if response else []
    except Exception as e:
        print(f"    Error fetching employment: {e}")
        return []


def get_employee_salary_and_wages(employee_id):
    """Fetch salary/wage details for an employee."""
    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)
    try:
        response = payroll_api.get_employee_salary_and_wages(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
        )
        return response.salary_and_wages if response else []
    except Exception as e:
        print(f"    Error fetching salary/wages: {e}")
        return []


def get_pay_runs_from_xero():
    """Fetch all pay runs from Xero."""
    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)
    try:
        response = payroll_api.get_pay_runs(xero_tenant_id=tenant_id)
        return response.pay_runs if response else []
    except Exception as e:
        print(f"    Error fetching pay runs: {e}")
        return []


def get_pay_run_details(pay_run_id):
    """Fetch detailed pay run info including employees."""
    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)
    try:
        response = payroll_api.get_pay_run(
            xero_tenant_id=tenant_id,
            pay_run_id=pay_run_id,
        )
        return response.pay_run if response else None
    except Exception as e:
        print(f"    Error fetching pay run details: {e}")
        return None


def find_employee_by_id(employees, employee_id):
    """Find employee by ID in list."""
    for emp in employees:
        if str(emp.employee_id) == employee_id:
            return emp
    return None


def print_employee_details(emp, label, calendar_lookup):
    """Print comprehensive employee details."""
    print(f"\n{label}:")
    print(f"  ID: {emp.employee_id}")
    print(f"  Name: {emp.first_name} {emp.last_name}")
    print(f"  Email: {emp.email}")
    print(f"  Job Title: {emp.job_title}")

    # Calendar
    cal_id = str(emp.payroll_calendar_id) if emp.payroll_calendar_id else None
    cal_name = calendar_lookup.get(cal_id, "NONE") if cal_id else "NONE"
    print(f"  Payroll Calendar: {cal_name} ({cal_id})")

    # Dates
    print(f"  Start Date: {emp.start_date}")
    print(f"  End Date: {emp.end_date}")

    # Employment details
    print("  Employment:")
    employments = get_employee_employment(str(emp.employee_id))
    if employments:
        for e in employments:
            print(f"    - Payroll Calendar ID: {e.payroll_calendar_id}")
            print(f"    - Start Date: {e.start_date}")
            print(f"    - Engagement Type: {e.engagement_type}")
    else:
        print("    NO EMPLOYMENT RECORDS!")

    # Salary/wages
    print("  Salary/Wages:")
    wages = get_employee_salary_and_wages(str(emp.employee_id))
    if wages:
        for w in wages:
            print(f"    - ID: {w.salary_and_wages_id}")
            print(f"    - Status: {getattr(w, 'status', 'N/A')}")
            print(f"    - Effective From: {getattr(w, 'effective_from', 'N/A')}")
    else:
        print("    NO SALARY/WAGE RECORDS!")


def main():
    print("=" * 70)
    print("COMPREHENSIVE DEBUG: Timesheet dates don't match pay period dates")
    print("=" * 70)
    print(f"\nFailing Employee ID: {FAILING_EMPLOYEE_ID}")
    print(f"Week: {WEEK_START} to {WEEK_END}")
    print()

    # 1. Get all payroll calendars
    print("1. FETCHING PAYROLL CALENDARS...")
    calendars = get_payroll_calendars()
    calendar_lookup = {cal["id"]: cal["name"] for cal in calendars}
    for cal in calendars:
        print(f"   - {cal['name']}: {cal['id']}")

    # 2. Fetch employees
    print("\n2. FETCHING EMPLOYEES FROM XERO...")
    employees = get_employees()
    print(f"   Found {len(employees)} employees")

    failing_emp = find_employee_by_id(employees, FAILING_EMPLOYEE_ID)
    success_emp = find_employee_by_id(employees, SUCCESS_EMPLOYEE_ID)

    if not failing_emp:
        print(f"\n   ERROR: Failing employee {FAILING_EMPLOYEE_ID} not found!")
        return

    # 3. Print employee details
    print("\n3. EMPLOYEE DETAILS:")
    print_employee_details(failing_emp, "FAILING EMPLOYEE", calendar_lookup)
    if success_emp:
        print_employee_details(
            success_emp, "SUCCESSFUL EMPLOYEE (for comparison)", calendar_lookup
        )

    # 4. Local pay run
    print("\n4. LOCAL PAY RUN (from database):")
    try:
        pay_run = XeroPayRun.objects.get(
            period_start_date=WEEK_START,
            period_end_date=WEEK_END,
        )
        print(f"   Pay Run ID: {pay_run.xero_pay_run_id}")
        print(f"   Calendar ID: {pay_run.payroll_calendar_id}")
        print(
            f"   Calendar Name: {calendar_lookup.get(pay_run.payroll_calendar_id, 'UNKNOWN')}"
        )
        print(f"   Period: {pay_run.period_start_date} to {pay_run.period_end_date}")
        print(f"   Status: {pay_run.status}")
    except XeroPayRun.DoesNotExist:
        print(f"   ERROR: No pay run found for {WEEK_START} to {WEEK_END}")
        pay_run = None

    # 5. Pay runs from Xero
    print("\n5. PAY RUNS FROM XERO (for this calendar):")
    xero_pay_runs = get_pay_runs_from_xero()
    if pay_run:
        matching_runs = [
            pr
            for pr in xero_pay_runs
            if str(pr.payroll_calendar_id) == pay_run.payroll_calendar_id
        ]
        for pr in matching_runs[-5:]:  # Last 5
            start = (
                pr.period_start_date.date()
                if hasattr(pr.period_start_date, "date")
                else pr.period_start_date
            )
            end = (
                pr.period_end_date.date()
                if hasattr(pr.period_end_date, "date")
                else pr.period_end_date
            )
            marker = " <<<" if start == WEEK_START else ""
            print(f"   - {start} to {end} (status: {pr.pay_run_status}){marker}")

    # 6. Check if employee is in the pay run
    print("\n6. CHECKING IF EMPLOYEE IS IN PAY RUN...")
    if pay_run:
        pay_run_detail = get_pay_run_details(pay_run.xero_pay_run_id)
        if pay_run_detail and pay_run_detail.pay_slips:
            employee_ids_in_run = [
                str(ps.employee_id) for ps in pay_run_detail.pay_slips
            ]
            print(f"   Pay run has {len(employee_ids_in_run)} employees")
            if FAILING_EMPLOYEE_ID in employee_ids_in_run:
                print("   ✓ Failing employee IS in pay run")
            else:
                print("   ✗ Failing employee NOT in pay run!")
            if SUCCESS_EMPLOYEE_ID in employee_ids_in_run:
                print("   ✓ Successful employee IS in pay run")
            else:
                print("   ? Successful employee NOT in pay run")
        else:
            print("   No pay slips in pay run yet (normal for Draft)")

    # 7. Local staff record
    print("\n7. LOCAL STAFF RECORD:")
    try:
        staff = Staff.objects.get(xero_user_id=FAILING_EMPLOYEE_ID)
        print(f"   Staff ID: {staff.id}")
        print(f"   Email: {staff.email}")
        print(f"   Created: {staff.created_at}")
        print(f"   Date Left: {staff.date_left}")
    except Staff.DoesNotExist:
        print(f"   ERROR: No staff record with xero_user_id={FAILING_EMPLOYEE_ID}")

    # 8. Diagnosis
    print("\n" + "=" * 70)
    print("DIAGNOSIS:")
    print("=" * 70)

    issues_found = []

    failing_cal = (
        str(failing_emp.payroll_calendar_id)
        if failing_emp.payroll_calendar_id
        else None
    )
    pay_run_cal = pay_run.payroll_calendar_id if pay_run else None

    # Check 1: Calendar mismatch
    if failing_cal and pay_run_cal and failing_cal != pay_run_cal:
        issues_found.append(
            f"CALENDAR MISMATCH: Employee on '{calendar_lookup.get(failing_cal)}' "
            f"but pay run uses '{calendar_lookup.get(pay_run_cal)}'"
        )
    elif not failing_cal:
        issues_found.append("NO CALENDAR: Employee has no payroll calendar assigned")

    # Check 2: Start date after pay period
    if failing_emp.start_date:
        start = (
            failing_emp.start_date.date()
            if hasattr(failing_emp.start_date, "date")
            else failing_emp.start_date
        )
        if start > WEEK_END:
            issues_found.append(
                f"START DATE: Employee starts {start}, after pay period ends {WEEK_END}"
            )

    # Check 3: End date before pay period
    if failing_emp.end_date:
        end = (
            failing_emp.end_date.date()
            if hasattr(failing_emp.end_date, "date")
            else failing_emp.end_date
        )
        if end < WEEK_START:
            issues_found.append(
                f"TERMINATED: Employee ended {end}, before pay period starts {WEEK_START}"
            )

    # Check 4: No employment record
    employments = get_employee_employment(str(failing_emp.employee_id))
    if not employments:
        issues_found.append("NO EMPLOYMENT: Employee has no employment records in Xero")

    # Check 5: Employment calendar mismatch
    if employments:
        emp_cal = (
            str(employments[0].payroll_calendar_id)
            if employments[0].payroll_calendar_id
            else None
        )
        if emp_cal and pay_run_cal and emp_cal != pay_run_cal:
            issues_found.append(
                "EMPLOYMENT CALENDAR MISMATCH: Employment record uses different calendar"
            )

    # Check 6: Compare with successful employee
    if success_emp and failing_emp:
        success_cal = (
            str(success_emp.payroll_calendar_id)
            if success_emp.payroll_calendar_id
            else None
        )
        if success_cal != failing_cal:
            issues_found.append(
                f"DIFFERS FROM SUCCESS: Successful employee on '{calendar_lookup.get(success_cal)}' "
                f"but failing employee on '{calendar_lookup.get(failing_cal)}'"
            )

    if issues_found:
        print("\nISSUES FOUND:")
        for i, issue in enumerate(issues_found, 1):
            print(f"  {i}. {issue}")
    else:
        print("\nNO OBVIOUS ISSUES FOUND")
        print("\nPossible hidden causes:")
        print("  - Pay period in Xero may have different dates than expected")
        print("  - Employee may have been added after pay run was created")
        print("  - There may be a timing issue with Xero's pay period alignment")


if __name__ == "__main__":
    main()
