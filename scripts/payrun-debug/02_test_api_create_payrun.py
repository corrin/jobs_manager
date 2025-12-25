#!/usr/bin/env python
"""
Test creating a pay run via the API endpoint (same path as frontend).

This tests the full stack including the view at:
  apps/timesheet/views/api.py - CreatePayRunAPIView
"""

import os
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.timesheet.views.api import CreatePayRunAPIView
from apps.workflow.models import XeroPayRun


def main():
    week_start = date(2025, 12, 15)

    print(f"=== Testing API pay run creation for {week_start} ===\n")

    # Check local state before
    before_count = XeroPayRun.objects.filter(period_start_date=week_start).count()
    print(f"Local records BEFORE: {before_count}")

    # Create a fake request
    User = get_user_model()
    user = User.objects.first()
    if not user:
        print("ERROR: No user found for authentication")
        return

    print(f"Using user: {user.email}")

    factory = RequestFactory()
    request = factory.post(
        "/timesheets/api/payroll/create-pay-run/",
        data={"week_start_date": "2025-12-15"},
        content_type="application/json",
    )
    request.user = user

    # Call the view
    print("\nCalling CreatePayRunAPIView.post()...")
    view = CreatePayRunAPIView.as_view()
    response = view(request)

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")

    # Check local state after
    after_count = XeroPayRun.objects.filter(period_start_date=week_start).count()
    print(f"\nLocal records AFTER: {after_count}")

    if after_count > before_count:
        print("BUG: Local record was created even though Xero failed!")
        for r in XeroPayRun.objects.filter(period_start_date=week_start):
            print(f"  Bad record: xero_id={r.xero_id}, status={r.pay_run_status}")
    elif after_count == before_count:
        print("OK: No local record created")

    # Check if error message is good
    if response.status_code == 409:
        print("\nGot 409 as expected")
        if "error" in response.data:
            print(f"Error message: {response.data['error'][:100]}")
    elif response.status_code == 201:
        print("\nWARNING: Got 201 - pay run was created (unexpected)")
    else:
        print(f"\nUnexpected status code: {response.status_code}")


if __name__ == "__main__":
    main()
