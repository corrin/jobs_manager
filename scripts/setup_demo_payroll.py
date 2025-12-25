#!/usr/bin/env python
"""
Set up employee payroll details for Demo Company.

This script adds the missing payroll setup for employees so they can be
included in pay runs:
- IRD number (generated with valid checksum)
- Tax code: M (main employment)
- ESCT rate: 17.5%
- KiwiSaver: active member with 3% employee, 3% employer contributions
- Leave: 160 hours annual leave, 80 hours sick leave per year
- Bank account (pre-validated NZ format)

Usage:
    python scripts/setup_demo_payroll.py          # Dry run
    python scripts/setup_demo_payroll.py --execute
"""

import os
import sys
import time
from typing import List

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from stdnum.nz import bankaccount as nz_bankaccount
from stdnum.nz import ird as nz_ird
from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import (
    BankAccount,
    EmployeeLeaveSetup,
    EmployeeTax,
    PaymentMethod,
    TaxCode,
)

from apps.accounts.models import Staff
from apps.workflow.api.xero.xero import api_client, get_tenant_id

SLEEP_TIME = 3

# Pre-validated bank accounts (ANZ branch 01-0242)
VALID_BANK_ACCOUNTS = [
    "01-0242-1588000-000",
    "01-0242-1596000-000",
    "01-0242-1668000-000",
    "01-0242-1676000-000",
    "01-0242-1684000-000",
    "01-0242-1692000-000",
    "01-0242-1748000-000",
    "01-0242-1756000-000",
    "01-0242-1764000-000",
    "01-0242-1772000-000",
]


def generate_ird_number(employee_num: int) -> str:
    """Generate a valid NZ IRD number with proper checksum."""
    base = 1000000 + (employee_num * 100)
    while True:
        base_str = str(base)
        check_digit = nz_ird.calc_check_digit(base_str)
        if check_digit != "10":
            full_ird = base_str + check_digit
            return nz_ird.format(full_ird)
        base += 1


def get_bank_account(index: int) -> str:
    """Get a pre-validated NZ bank account number."""
    account = VALID_BANK_ACCOUNTS[index % len(VALID_BANK_ACCOUNTS)]
    if not nz_bankaccount.is_valid(account):
        raise ValueError(f"Pre-validated bank account failed: {account}")
    return account


def setup_tax(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
    ird_number: str,
) -> bool:
    """Set up employee tax details including KiwiSaver."""
    try:
        ird_clean = ird_number.replace("-", "").zfill(9)
        tax = EmployeeTax(
            ird_number=ird_clean,
            tax_code=TaxCode.M,
            esct_rate_percentage=17.5,
            is_eligible_for_kiwi_saver=True,
            kiwi_saver_contributions="MakeContributions",
            kiwi_saver_employee_contribution_rate_percentage=3.0,
            kiwi_saver_employer_contribution_rate_percentage=3.0,
            kiwi_saver_employer_salary_sacrifice_contribution_rate_percentage=0.0,
        )
        payroll_api.update_employee_tax(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
            employee_tax=tax,
        )
        time.sleep(SLEEP_TIME)
        return True
    except Exception as e:
        print(f"  ERROR Tax: {e}")
        return False


def setup_leave(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
) -> bool:
    """Set up employee leave entitlements."""
    try:
        leave_setup = EmployeeLeaveSetup(
            include_holiday_pay=False,
            holiday_pay_opening_balance=0.0,
            annual_leave_opening_balance=160.0,
            sick_leave_to_accrue_annually=80.0,
            sick_leave_maximum_to_accrue=80.0,
            sick_leave_opening_balance=80.0,
        )
        payroll_api.create_employee_leave_setup(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
            employee_leave_setup=leave_setup,
        )
        time.sleep(SLEEP_TIME)
        return True
    except Exception as e:
        # "Employee leave is already setup" is not an error
        if "already setup" in str(e).lower():
            return True
        print(f"  ERROR Leave: {e}")
        return False


def setup_bank(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
    bank_account_number: str,
) -> bool:
    """Set up employee bank account."""
    try:
        parts = bank_account_number.split("-")
        if len(parts) != 4:
            raise ValueError(f"Invalid format: {bank_account_number}")
        sort_code = f"{parts[0]}{parts[1]}"
        account_number = f"{parts[0]}{parts[1]}{parts[2]}{parts[3]}"

        bank = BankAccount(
            account_name="Wages",
            account_number=account_number,
            sort_code=sort_code,
            calculation_type="Balance",
        )
        payment = PaymentMethod(
            payment_method="Electronically",
            bank_accounts=[bank],
        )
        payroll_api.create_employee_payment_method(
            xero_tenant_id=tenant_id,
            employee_id=employee_id,
            payment_method=payment,
        )
        time.sleep(SLEEP_TIME)
        return True
    except Exception as e:
        print(f"  ERROR Bank: {e}")
        return False


def main():
    execute = "--execute" in sys.argv
    print(f"Mode: {'EXECUTE' if execute else 'DRY RUN'}")

    tenant_id = get_tenant_id()
    if not tenant_id:
        print("ERROR: No tenant_id configured")
        return

    staff_list: List[Staff] = list(
        Staff.objects.filter(date_left__isnull=True, xero_user_id__isnull=False)
    )
    print(f"Found {len(staff_list)} staff with Xero IDs")

    if not staff_list:
        return

    payroll_api = PayrollNzApi(api_client)
    results = {"tax": [0, 0], "leave": [0, 0], "bank": [0, 0]}

    for i, staff in enumerate(staff_list):
        ird = generate_ird_number(i + 1)
        bank = get_bank_account(i + 1)
        print(f"{staff.first_name} {staff.last_name}: IRD={ird} Bank={bank}")

        if not execute:
            continue

        # Tax (includes IRD, tax code, ESCT, KiwiSaver)
        if setup_tax(payroll_api, tenant_id, staff.xero_user_id, ird):
            results["tax"][0] += 1
            print(f"  Tax OK: IRD={ird} KiwiSaver=3%/3%")
        else:
            results["tax"][1] += 1

        # Leave entitlements
        if setup_leave(payroll_api, tenant_id, staff.xero_user_id):
            results["leave"][0] += 1
            print("  Leave OK: Annual=160h Sick=80h")
        else:
            results["leave"][1] += 1

        # Bank account
        if setup_bank(payroll_api, tenant_id, staff.xero_user_id, bank):
            results["bank"][0] += 1
            print(f"  Bank OK: {bank}")
        else:
            results["bank"][1] += 1

    if not execute:
        print("\nDRY RUN complete - run with --execute to apply")
    else:
        print(
            f"\nResults: Tax {results['tax'][0]}/{sum(results['tax'])}, "
            f"Leave {results['leave'][0]}/{sum(results['leave'])}, "
            f"Bank {results['bank'][0]}/{sum(results['bank'])}"
        )


if __name__ == "__main__":
    main()
