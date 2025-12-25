#!/usr/bin/env python
"""
Try to POST (finalize) the old 2023-07-10 draft pay run.

If we can't delete it, maybe we can finalize it to unblock new drafts.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi

from apps.workflow.api.xero.payroll import get_pay_run
from apps.workflow.api.xero.xero import api_client, get_tenant_id


def main():
    print("=== Attempting to finalize old draft pay run ===\n")

    pay_run_id = "141ebf83-a94b-4395-ac2f-8ef11b52dcef"

    # Get current state
    pay_run = get_pay_run(pay_run_id)
    print(f"Pay Run ID: {pay_run.pay_run_id}")
    print(f"Period: {pay_run.period_start_date} to {pay_run.period_end_date}")
    print(f"Status: {pay_run.pay_run_status}")

    if pay_run.pay_run_status != "Draft":
        print(f"\nPay run is not Draft, it's {pay_run.pay_run_status}")
        return

    # Check what methods are available
    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    print("\nAvailable PayrollNzApi methods containing 'pay_run':")
    methods = [m for m in dir(payroll_api) if "pay_run" in m.lower()]
    for m in methods:
        print(f"  {m}")

    # Try update_pay_run to change status
    print("\nTrying to update pay run status to 'Posted'...")
    try:
        from xero_python.payrollnz.models import PayRun

        updated_pay_run = PayRun(
            pay_run_id=pay_run_id,
            pay_run_status="Posted",
        )
        response = payroll_api.update_pay_run(
            xero_tenant_id=tenant_id,
            pay_run_id=pay_run_id,
            pay_run=updated_pay_run,
        )
        print(f"Update response: {response}")
    except Exception as e:
        print(f"Update failed: {e}")


if __name__ == "__main__":
    main()
