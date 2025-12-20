import json
import random


def create_staff_mapping():
    """Create a consistent mapping for a single staff member"""
    first_name = random.choice(
        ["John", "Anthony", "Phillip", "Doug", "David", "Fred", "James", "Bill"]
    )
    last_name = random.choice(
        ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    )
    preferred_name = random.choice(
        ["John", "Jane", "Mike", "Sara", "Dave", "Em", "Jim", "Liz"]
    )
    email = f"{first_name.lower()}.{last_name.lower()}@example.com"

    return {
        # Main staff fields
        "first_name": first_name,
        "last_name": last_name,
        "preferred_name": preferred_name,
        "email": email,
    }


def anonymize_staff_data():
    # Read the original fixture
    with open("workflow/fixtures/staff.json", "r", encoding="utf-8") as f:
        staff_data = json.load(f)

    # Create a mapping for each staff member
    staff_mappings = {}
    for staff in staff_data:
        # Use the original name as the key to ensure consistency
        original_name = f"{staff['fields'].get('first_name', '')} {staff['fields'].get('last_name', '')}"
        staff_mappings[original_name] = create_staff_mapping()

    # Anonymize each staff member using their consistent mapping
    for staff in staff_data:
        fields = staff["fields"]
        original_name = f"{fields.get('first_name', '')} {fields.get('last_name', '')}"
        mapping = staff_mappings[original_name]

        # Apply mapping to main staff fields
        for field, value in mapping.items():
            if field in fields and fields[field] is not None and fields[field] != "":
                fields[field] = value

    # Write the anonymized data to a new file
    with open("workflow/fixtures/staff_anonymized.json", "w", encoding="utf-8") as f:
        json.dump(staff_data, f, indent=2, ensure_ascii=False)

    print(f"Anonymized {len(staff_data)} staff records")
    print("Anonymized data saved to workflow/fixtures/staff_anonymized.json")


if __name__ == "__main__":
    anonymize_staff_data()
