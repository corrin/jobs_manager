#!/usr/bin/env python
"""
Test script for KPI Service functionality

This script allows direct testing of the KPI calendar service without
needing to run the full web server. Useful for debugging KPI calculation issues.

Usage:
    python scripts/test_kpi_service.py [year] [month]

Examples:
    python scripts/test_kpi_service.py  # Tests current month
    python scripts/test_kpi_service.py 2025 6  # Tests June 2025
"""

import os
import sys
import traceback
from datetime import date

import django

from apps.accounting.services import KPIService

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings.local")
django.setup()


def test_kpi_calendar(year=None, month=None):
    """Test the KPI calendar service directly"""
    if year is None:
        year = date.today().year
    if month is None:
        month = date.today().month

    try:
        print(f"Testing KPI calendar for {year}-{month:02d}...")
        result = KPIService.get_calendar_data(year, month)

        calendar_data = result.get("calendar_data", {})
        monthly_totals = result.get("monthly_totals", {})

        print(f"\n✓ Success! Got {len(calendar_data)} days of data")
        print("\nMonthly summary:")
        print(f"  - Working days: {monthly_totals.get('working_days', 0)}")
        print(f"  - Billable hours: {monthly_totals.get('billable_hours', 0):.1f}")
        print(f"  - Total hours: {monthly_totals.get('total_hours', 0):.1f}")
        print(f"  - Gross profit: ${monthly_totals.get('gross_profit', 0):.2f}")

        return True
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Parse command line arguments
    args = sys.argv[1:]
    year = int(args[0]) if len(args) > 0 else None
    month = int(args[1]) if len(args) > 1 else None

    success = test_kpi_calendar(year, month)
    sys.exit(0 if success else 1)
