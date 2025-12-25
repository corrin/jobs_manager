#!/usr/bin/env python
"""
Test creating a pay run for 2025-12-15.

Expected: 409 error because Xero only allows one draft pay run per calendar,
and there's already a 2023-07-10 draft blocking us.

This script tests that:
1. The error is properly raised
2. NO local XeroPayRun record is created on failure
"""

import os
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from apps.workflow.api.xero.payroll import create_pay_run
from apps.workflow.models import XeroPayRun


def main():
    week_start = date(2025, 12, 15)

    print(f"=== Testing pay run creation for {week_start} ===\n")

    # Check local state before
    before_count = XeroPayRun.objects.filter(period_start_date=week_start).count()
    print(f"Local records BEFORE: {before_count}")

    # Try to create pay run
    print(f"\nCalling create_pay_run({week_start})...")
    try:
        pay_run_id = create_pay_run(week_start)
        print(f"SUCCESS: Created pay run {pay_run_id}")
        print("WARNING: This was unexpected - there should be a blocking draft!")
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}")
        print(f"  Message: {str(e)[:200]}")

        # Check if it's the expected 409
        if "only be one draft pay run" in str(e).lower():
            print("  This is the EXPECTED 409 error")
        elif "409" in str(e):
            print("  Got 409 but different message")
        else:
            print("  UNEXPECTED error type")

    # Check local state after
    after_count = XeroPayRun.objects.filter(period_start_date=week_start).count()
    print(f"\nLocal records AFTER: {after_count}")

    if after_count > before_count:
        print("BUG: Local record was created even though Xero failed!")
        # Show the bad record
        for r in XeroPayRun.objects.filter(period_start_date=week_start):
            print(f"  Bad record: xero_id={r.xero_id}, status={r.pay_run_status}")
    elif after_count == before_count:
        print("OK: No local record created (correct behavior)")


if __name__ == "__main__":
    main()
