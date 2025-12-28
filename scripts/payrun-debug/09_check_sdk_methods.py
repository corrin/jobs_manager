#!/usr/bin/env python
"""Check what methods are available in the PayrollNzApi."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
import django

django.setup()

from xero_python.payrollnz import PayrollNzApi

from apps.workflow.api.xero.xero import api_client


def main():
    payroll_api = PayrollNzApi(api_client)

    print("=== PayrollNzApi Methods ===\n")

    # Group by category
    categories = {
        "employee": [],
        "employment": [],
        "pay_run": [],
        "timesheet": [],
        "calendar": [],
        "salary": [],
        "other": [],
    }

    for method in dir(payroll_api):
        if method.startswith("_"):
            continue

        method_lower = method.lower()
        categorized = False
        for cat in categories:
            if cat in method_lower:
                categories[cat].append(method)
                categorized = True
                break
        if not categorized:
            categories["other"].append(method)

    for cat, methods in categories.items():
        if methods:
            print(f"{cat.upper()}:")
            for m in sorted(methods):
                print(f"  {m}")
            print()


if __name__ == "__main__":
    main()
