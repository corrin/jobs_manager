#!/usr/bin/env python
"""Test the fail-early validation for timesheet posting."""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from apps.workflow.api.xero.payroll import (
    _earnings_rate_cache,
    ensure_earnings_rate_cache,
    get_earnings_rate_id_by_name,
)
from apps.workflow.models import CompanyDefaults

print("Testing fail-early validation for timesheet posting\n")

# Step 1: Pre-fetch earnings rates
print("1. Pre-fetching earnings rates from Xero...")
ensure_earnings_rate_cache()
print(f"   Cached {len(_earnings_rate_cache)} earnings rates:")
for name, rate_id in sorted(_earnings_rate_cache.items()):
    print(f"   - {name}: {rate_id}")

# Step 2: Get company defaults
print("\n2. Getting company defaults...")
company = CompanyDefaults.get_instance()
print(f"   Ordinary Time rate name: {company.xero_ordinary_earnings_rate_name}")
print(f"   Time and a Half rate name: {company.xero_time_half_earnings_rate_name}")
print(f"   Double Time rate name: {company.xero_double_time_earnings_rate_name}")

# Step 3: Validate all required rates exist
print("\n3. Validating required rates exist in Xero...")
required_rates = [
    company.xero_ordinary_earnings_rate_name,
    company.xero_time_half_earnings_rate_name,
    company.xero_double_time_earnings_rate_name,
]
all_valid = True
for rate_name in required_rates:
    if rate_name in _earnings_rate_cache:
        print(f"   ✓ '{rate_name}' found")
    else:
        print(f"   ✗ '{rate_name}' NOT FOUND")
        all_valid = False

if all_valid:
    print("\n✓ All required earnings rates are valid!")
else:
    print("\n✗ Some earnings rates are missing - posting would fail early")
    sys.exit(1)

# Step 4: Test lookup function
print("\n4. Testing get_earnings_rate_id_by_name()...")
for rate_name in required_rates:
    rate_id = get_earnings_rate_id_by_name(rate_name)
    print(f"   '{rate_name}' -> {rate_id}")

print("\n✓ Fail-early validation test passed!")
