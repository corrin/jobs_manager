#!/usr/bin/env python
"""Check configured earnings rates against what's in Xero."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from apps.workflow.api.xero.payroll import get_earnings_rates
from apps.workflow.models import CompanyDefaults


def main():
    c = CompanyDefaults.get_instance()
    print(f"Company: {c.company_name}")
    print(f"Tenant ID: {c.xero_tenant_id}")
    print()

    print("Configured earnings rate names:")
    print(f"  Ordinary (1.0x): {c.xero_ordinary_earnings_rate_name}")
    print(f"  Time half (1.5x): {c.xero_time_half_earnings_rate_name}")
    print(f"  Double (2.0x): {c.xero_double_time_earnings_rate_name}")
    print()

    print("Fetching earnings rates from Xero API...")
    rates = get_earnings_rates()
    print(f"Found {len(rates)} earnings rates:")
    for r in rates:
        print(f"  - {r['name']}")


if __name__ == "__main__":
    main()
