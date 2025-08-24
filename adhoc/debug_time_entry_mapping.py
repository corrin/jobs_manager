#!/usr/bin/env python
"""
Debug script to understand TimeEntryCreateOrUpdate object behavior
"""

import os

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from datetime import datetime

from xero_python.project.models import TimeEntryCreateOrUpdate

print("Testing TimeEntryCreateOrUpdate object...")

# Create a test object like in the mapping function with real task ID
time_entry = TimeEntryCreateOrUpdate(
    description="Test description",
    duration=60,
    date_utc=datetime.now(),
    user_id="ba3ad4d6-6a30-4678-9569-b3d905740c81",
    task_id="f156c76f-49d8-4ebe-a78e-3ecd28366495",  # Real task ID from Job 95549
)

print(f"TimeEntryCreateOrUpdate object created: {time_entry}")
print(f"Type: {type(time_entry)}")

# Check available attributes
print("Available attributes:")
for attr in dir(time_entry):
    if not attr.startswith("_"):
        print(f"  {attr}: {getattr(time_entry, attr, 'N/A')}")

# Test dictionary-style access (this is what's failing)
print("\nTesting dictionary-style access...")
try:
    time_entry["time_id"] = "test-id"
    print("SUCCESS: Dictionary-style assignment worked")
except Exception as e:
    print(f"ERROR: {e}")

# Test attribute assignment
print("\nTesting attribute assignment...")
try:
    time_entry.time_entry_id = "test-id"  # Try the correct attribute name
    print("SUCCESS: time_entry_id attribute assignment worked")
except Exception as e:
    print(f"ERROR setting time_entry_id: {e}")

try:
    time_entry.time_id = "test-id"  # Try the incorrect attribute name
    print("SUCCESS: time_id attribute assignment worked")
except Exception as e:
    print(f"ERROR setting time_id: {e}")
