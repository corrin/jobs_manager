#!/usr/bin/env python
"""
Try to delete the old draft pay run using raw REST API.

The SDK doesn't expose delete/update for pay runs, but the API might support it.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

import requests

from apps.workflow.api.xero.xero import get_tenant_id
from apps.workflow.models import XeroToken


def get_access_token():
    """Get a valid access token."""
    # The api_client handles token refresh automatically
    # Just need to trigger a call to ensure it's fresh
    from apps.workflow.api.xero.payroll import get_pay_runs

    get_pay_runs()  # This refreshes token if needed

    token = XeroToken.objects.first()
    if not token:
        raise Exception("No Xero token found")

    return token.access_token


def main():
    pay_run_id = "141ebf83-a94b-4395-ac2f-8ef11b52dcef"
    tenant_id = get_tenant_id()
    access_token = get_access_token()

    # NZ Payroll uses different base URL
    base_url = "https://api.xero.com/payroll.xro/2.0/nz"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Xero-Tenant-Id": tenant_id,
        "Content-Type": "application/json",
    }

    print(f"=== Attempting raw API operations on pay run {pay_run_id} ===\n")

    # Try DELETE
    print("1. Trying DELETE...")
    url = f"{base_url}/PayRuns/{pay_run_id}"
    resp = requests.delete(url, headers=headers)
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   Response: {resp.text[:500]}")
    else:
        print("   SUCCESS!")
        return

    # Try PUT to change status
    print("\n2. Trying PUT to set status to 'Posted'...")
    payload = {
        "payRunId": pay_run_id,
        "payRunStatus": "Posted",
    }
    resp = requests.put(url, headers=headers, json=payload)
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   Response: {resp.text[:500]}")
    else:
        print("   SUCCESS!")
        return

    print("\n3. Checking available actions in Xero docs...")
    print("   The Xero Payroll NZ API may not support deleting pay runs.")
    print("   You may need to delete it manually in the Xero UI:")
    print("   https://go.xero.com/payroll/payruns")


if __name__ == "__main__":
    main()
