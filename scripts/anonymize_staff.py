"""
Anonymize staff fixture data for testing/demo purposes.

Usage:
    python scripts/anonymize_staff.py

Reads workflow/fixtures/staff.json and writes anonymized version to
workflow/fixtures/staff_anonymized.json.
"""

import json
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.accounts.staff_anonymization import create_staff_profile


def anonymize_staff_data():
    # Read the original fixture
    with open("workflow/fixtures/staff.json", "r", encoding="utf-8") as f:
        staff_data = json.load(f)

    # Create a mapping for each staff member
    staff_mappings = {}
    for staff in staff_data:
        # Use the original name as the key to ensure consistency
        original_name = (
            f"{staff['fields'].get('first_name', '')} "
            f"{staff['fields'].get('last_name', '')}"
        )
        staff_mappings[original_name] = create_staff_profile()

    # Anonymize each staff member using their consistent mapping
    for staff in staff_data:
        fields = staff["fields"]
        original_name = f"{fields.get('first_name', '')} {fields.get('last_name', '')}"
        mapping = staff_mappings[original_name]

        # Apply mapping to main staff fields
        for field, value in mapping.items():
            if field in fields:
                fields[field] = value

    # Write the anonymized data to a new file
    with open("workflow/fixtures/staff_anonymized.json", "w", encoding="utf-8") as f:
        json.dump(staff_data, f, indent=2, ensure_ascii=False)

    print(f"Anonymized {len(staff_data)} staff records")
    print("Anonymized data saved to workflow/fixtures/staff_anonymized.json")


if __name__ == "__main__":
    anonymize_staff_data()
