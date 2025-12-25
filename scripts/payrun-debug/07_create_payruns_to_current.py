#!/usr/bin/env python
"""
Create pay runs from the current Xero calendar position up to a target date.

The Xero Demo Company calendar is stuck at July 2023. We need to create
~130 weekly pay runs to catch up to December 2025.

Each pay run advances the calendar to the next week period.
"""

import os
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi
from xero_python.payrollnz.models import PayRun

from apps.workflow.api.xero.payroll import get_pay_runs, get_payroll_calendars
from apps.workflow.api.xero.xero import api_client, get_tenant_id


def get_latest_weekly_period():
    """Get the current period dates from the weekly calendar."""
    calendars = get_payroll_calendars()
    weekly = next((c for c in calendars if "weekly" in c["name"].lower()), None)
    if not weekly:
        raise Exception("No weekly calendar found")

    start = weekly["period_start_date"]
    end = weekly["period_end_date"]

    # Normalize to date objects
    if hasattr(start, "date"):
        start = start.date()
    if hasattr(end, "date"):
        end = end.date()

    return weekly["id"], start, end


def create_and_post_payrun(calendar_id: str, dry_run: bool = True):
    """Create a pay run and immediately post it to advance the calendar."""
    tenant_id = get_tenant_id()
    payroll_api = PayrollNzApi(api_client)

    # Create draft pay run
    pay_run = PayRun(
        payroll_calendar_id=calendar_id,
        pay_run_status="Draft",
        pay_run_type="Scheduled",
    )

    if dry_run:
        print("    [DRY RUN] Would create pay run")
        return None

    response = payroll_api.create_pay_run(
        xero_tenant_id=tenant_id,
        pay_run=pay_run,
    )

    if not response or not response.pay_run:
        raise Exception("Failed to create pay run")

    pay_run_id = str(response.pay_run.pay_run_id)
    period_start = response.pay_run.period_start_date
    period_end = response.pay_run.period_end_date

    print(f"    Created: {pay_run_id[:8]}... ({period_start} to {period_end})")

    # Post the pay run to finalize it (this advances the calendar)
    # Note: We need to update status to Posted
    # Actually, the SDK doesn't have update_pay_run...
    # We may need to do this differently

    return pay_run_id


def main():
    target_date = date(2025, 12, 15)
    dry_run = True  # Set to False to actually create pay runs

    print("=== Create Pay Runs to Catch Up Calendar ===\n")
    print(f"Target date: {target_date}")
    print(f"Dry run: {dry_run}\n")

    # Get current calendar position
    calendar_id, current_start, current_end = get_latest_weekly_period()
    print(f"Weekly calendar ID: {calendar_id}")
    print(f"Current period: {current_start} to {current_end}")

    # Calculate how many weeks we need
    weeks_needed = (target_date - current_start).days // 7
    print(f"Weeks to create: {weeks_needed}")

    if weeks_needed <= 0:
        print("Calendar is already at or past target date!")
        return

    if weeks_needed > 150:
        print(f"WARNING: That's a lot of pay runs ({weeks_needed})")
        print("Consider if this is correct.")

    print(f"\nThis will create {weeks_needed} pay runs.")
    print("Each must be POSTED to advance the calendar.\n")

    # Problem: We can't post pay runs via API (no update_pay_run method)
    # The user will need to post each one manually, OR we find another way

    print("ISSUE: Xero Payroll NZ API doesn't support updating pay run status.")
    print("Each draft must be posted manually in Xero UI to advance calendar.")
    print("")
    print("Alternative approaches:")
    print("1. Post each one manually in Xero UI (tedious)")
    print("2. Check if there's a way to create already-posted pay runs")
    print("3. Use a different test approach (match existing 2023 dates)")

    # Let's check what pay runs already exist
    print("\n--- Existing pay runs ---")
    existing = get_pay_runs()
    posted_count = sum(1 for pr in existing if pr.get("pay_run_status") == "Posted")
    draft_count = sum(1 for pr in existing if pr.get("pay_run_status") == "Draft")
    print(f"Total: {len(existing)} (Posted: {posted_count}, Draft: {draft_count})")

    # Show most recent
    if existing:
        latest = max(existing, key=lambda x: x.get("period_end_date") or date.min)
        print(
            f"Latest: {latest.get('period_start_date')} to {latest.get('period_end_date')} ({latest.get('pay_run_status')})"
        )


if __name__ == "__main__":
    main()
