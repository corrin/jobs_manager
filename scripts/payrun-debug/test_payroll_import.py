#!/usr/bin/env python
"""Test that payroll module imports correctly."""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from apps.workflow.api.xero.payroll import _delete_timesheet_safe, post_timesheet

print("Import successful")
print(f"post_timesheet: {post_timesheet}")
print(f"_delete_timesheet_safe: {_delete_timesheet_safe}")
