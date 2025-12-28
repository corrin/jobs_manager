#!/usr/bin/env python
"""
Delete the old 2023-07-10 draft pay run that's blocking new ones.

Xero only allows one draft pay run per calendar.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi

from apps.workflow.api.xero.payroll import get_pay_runs
from apps.workflow.api.xero.xero import api_client, get_tenant_id


def main():
    print("=== Finding and deleting old draft pay run ===\n")

    # Get all pay runs
    pay_runs = get_pay_runs()

    # Find draft pay runs
    drafts = [pr for pr in pay_runs if pr.get("status") == "Draft"]

    print(f"Found {len(drafts)} draft pay run(s):")
    for pr in drafts:
        print(f"  ID: {pr['id']}")
        print(f"  Period: {pr['period_start']} to {pr['period_end']}")
        print(f"  Status: {pr['status']}")
        print()

    if not drafts:
        print("No draft pay runs to delete!")
        return

    # Delete the draft(s)
    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    for pr in drafts:
        pay_run_id = pr["id"]
        print(f"Attempting to delete pay run {pay_run_id}...")

        try:
            # Try to delete - note: Xero may not allow this
            # We might need to "revert" it instead
            payroll_api.delete_pay_run(
                xero_tenant_id=tenant_id,
                pay_run_id=pay_run_id,
            )
            print("  Deleted successfully!")
        except AttributeError:
            print("  delete_pay_run not available in SDK")
            print("  Trying revert_pay_run...")
            try:
                payroll_api.revert_pay_run(
                    xero_tenant_id=tenant_id,
                    pay_run_id=pay_run_id,
                )
                print("  Reverted successfully!")
            except Exception as e:
                print(f"  Revert failed: {e}")
                print("\n  May need to handle this in Xero UI directly")
        except Exception as e:
            print(f"  Delete failed: {e}")
            print("\n  May need to handle this in Xero UI directly")


if __name__ == "__main__":
    main()
