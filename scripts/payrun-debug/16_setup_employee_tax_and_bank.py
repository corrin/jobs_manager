#!/usr/bin/env python
"""
Set up employee payroll details for Demo Company.

This script adds the missing payroll setup for employees so they can be
included in pay runs:
- IRD number (generated with valid checksum using python-stdnum)
- Tax code: M (main employment)
- ESCT rate: 17.5%
- KiwiSaver: active member with 3% employee, 3% employer contributions
- Leave: 160 hours annual leave, 80 hours sick leave per year
- Bank account (pre-validated NZ format)

Run:
    python scripts/payrun-debug/16_setup_employee_tax_and_bank.py
    python scripts/payrun-debug/16_setup_employee_tax_and_bank.py --execute
"""

import logging
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SLEEP_TIME = 3

# Pre-validated bank accounts (ANZ branch 01-0242)
# Verified valid using stdnum.nz.bankaccount
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
    """Generate a valid NZ IRD number with proper checksum.

    Employee number is embedded in the IRD (e.g., employee 1 -> 10-001-0XX).
    Skips numbers where check digit would be 10 (invalid per IRD spec).
    """
    # Format: 10-NNN-0XX where NNN is employee number
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


def setup_employee_tax(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
    ird_number: str,
) -> bool:
    """Set up employee tax details including ESCT rate and KiwiSaver.

    ESCT (Employer Superannuation Contribution Tax) rates for NZ 2025:
    - 10.5% for income up to $16,800
    - 17.5% for income $16,801 - $57,600
    - 30% for income $57,601 - $84,000
    - 33% for income $84,001 - $180,000
    - 39% for income over $180,000

    Using 17.5% as a reasonable default for demo employees.
    KiwiSaver: 3% employee, 3% employer (standard rates).
    """
    try:
        # Xero wants IRD as 9 digits without dashes
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
        logger.error(f"Failed to set tax for {employee_id}: {e}")
        return False


def setup_employee_leave(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
) -> bool:
    """Set up employee leave entitlements.

    NZ standard entitlements:
    - Annual leave: 160 hours per year (4 weeks)
    - Sick leave: 80 hours per year (10 days)
    """
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
        logger.error(f"Failed to set leave for {employee_id}: {e}")
        return False


def setup_employee_bank(
    payroll_api: PayrollNzApi,
    tenant_id: str,
    employee_id: str,
    bank_account_number: str,
) -> bool:
    """Set up employee bank account.

    NZ bank account format: BB-bbbb-AAAAAAA-SSS
    sort_code is bank-branch (BB-bbbb)
    account_number is account-suffix (AAAAAAA-SSS)
    """
    try:
        parts = bank_account_number.split("-")
        if len(parts) != 4:
            raise ValueError(f"Invalid format: {bank_account_number}")
        # Xero wants: sort_code = 6 digits, account_number = full 16 digits (all no dashes)
        sort_code = f"{parts[0]}{parts[1]}"  # BB + bbbb = 6 digits
        account_number = f"{parts[0]}{parts[1]}{parts[2]}{parts[3]}"  # Full 16 digits

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
        logger.error(f"Failed to set bank for {employee_id}: {e}")
        return False


def main():
    dry_run = "--execute" not in sys.argv
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")

    tenant_id = get_tenant_id()
    if not tenant_id:
        logger.error("No tenant_id configured")
        return

    staff_list: List[Staff] = list(
        Staff.objects.filter(date_left__isnull=True, xero_user_id__isnull=False)
    )
    logger.info(f"Found {len(staff_list)} staff with Xero IDs")

    if not staff_list:
        return

    payroll_api = PayrollNzApi(api_client)
    results = {"tax": [0, 0], "leave": [0, 0], "bank": [0, 0]}  # [success, fail]

    for i, staff in enumerate(staff_list):
        ird = generate_ird_number(i + 1)
        bank = get_bank_account(i + 1)
        logger.info(
            f"{staff.first_name} {staff.last_name}: IRD={ird} Bank={bank} "
            f"Xero={staff.xero_user_id[:8]}..."
        )

        if dry_run:
            continue

        # Tax (includes IRD, tax code, ESCT, KiwiSaver)
        if setup_employee_tax(payroll_api, tenant_id, staff.xero_user_id, ird):
            results["tax"][0] += 1
            logger.info(f"  Tax set: IRD={ird} code=M KiwiSaver=3%/3%")
        else:
            results["tax"][1] += 1

        # Leave entitlements (annual 160h, sick 80h)
        if setup_employee_leave(payroll_api, tenant_id, staff.xero_user_id):
            results["leave"][0] += 1
            logger.info("  Leave set: Annual=160h Sick=80h")
        else:
            results["leave"][1] += 1

        # Bank account
        if setup_employee_bank(payroll_api, tenant_id, staff.xero_user_id, bank):
            results["bank"][0] += 1
            logger.info(f"  Bank set: {bank}")
        else:
            results["bank"][1] += 1

    if dry_run:
        logger.info("DRY RUN complete - run with --execute to apply")
    else:
        logger.info(
            f"Results: Tax {results['tax'][0]}/{results['tax'][0]+results['tax'][1]}, "
            f"Leave {results['leave'][0]}/{results['leave'][0]+results['leave'][1]}, "
            f"Bank {results['bank'][0]}/{results['bank'][0]+results['bank'][1]}"
        )


if __name__ == "__main__":
    main()
