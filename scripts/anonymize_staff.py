import json
import random


def create_staff_mapping():
    """Create a consistent mapping for a single staff member"""
    first_name = random.choice(
        ["John", "Jane", "Michael", "Sarah", "David", "Emma", "James", "Lisa"]
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
        # IMS data fields
        "FirstNames": first_name,
        "Surname": last_name,
        "PreferredName": preferred_name,
        "EmailAddress": email,
        "BirthDate": f"1990-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "IRDNumber": str(random.randint(10000000, 99999999)),  # 8 digits
        "BankAccount": str(random.randint(100000000000000, 999999999999999)),
        "PostalAddress1": f"{random.randint(1, 999)} Main Street",
        "PostalAddress2": random.choice(
            ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga"]
        ),
        "HomePhone": f"{random.randint(1000000, 9999999)}.0",  # Format: 1234567.0
        # Format: 02123456789
        "HomePhone2": f"02{random.randint(100000000, 999999999)}",
        "KSOptOutBankAccount": str(random.randint(100000000000000, 999999999999999)),
        "KSOptOutBankAccName": f"{first_name} {last_name}",
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

        # Apply mapping to IMS data fields
        if "raw_ims_data" in fields:
            ims_data = fields["raw_ims_data"]
            for field, value in mapping.items():
                if (
                    field in ims_data
                    and ims_data[field] is not None
                    and ims_data[field] != ""
                ):
                    ims_data[field] = value

    # Write the anonymized data to a new file
    with open("workflow/fixtures/staff_anonymized.json", "w", encoding="utf-8") as f:
        json.dump(staff_data, f, indent=2, ensure_ascii=False)

    print(f"Anonymized {len(staff_data)} staff records")
    print("Anonymized data saved to workflow/fixtures/staff_anonymized.json")


if __name__ == "__main__":
    anonymize_staff_data()
