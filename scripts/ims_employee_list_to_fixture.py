import json
import math
import uuid
from pathlib import Path

import pandas as pd


def clean_nan_values(data):
    """Replace NaN values with None for valid JSON."""
    return {
        k: (v if not (isinstance(v, float) and math.isnan(v)) else None)
        for k, v in data.items()
    }


NAMESPACE = uuid.NAMESPACE_DNS


def get_deterministic_uuid_from_ird(ird_number: str) -> str:
    # Use uuid5 to generate a deterministic UUID based on the IRD number
    return str(uuid.uuid5(NAMESPACE, ird_number))


def convert_ims_to_fixtures(input_file: str) -> None:
    fixtures = []
    project_root = Path.cwd()
    fixtures_dir = project_root / "workflow" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_file)

    for _, row in df.iterrows():
        surname = str(row["Surname"]).strip()
        ird = str(row["IRDNumber"]).strip()

        # Generate a UUID for staff based on IRD
        staff_id = get_deterministic_uuid_from_ird(ird)

        fixture = {
            "model": "workflow.staff",
            "pk": staff_id,
            "fields": {
                "email": str(row["EmailAddress"]).strip(),
                "first_name": str(row["FirstNames"]).strip(),
                "ims_payroll_id": str(uuid.uuid4()),  # I need to get VAL to set this
                "last_name": surname,
                "preferred_name": (
                    str(row["PreferredName"]).strip()
                    if pd.notna(row["PreferredName"])
                    else None
                ),
                "wage_rate": str(row["HourlyRate1"]),
                "hours_mon": str(row["HoursPerDay"]),
                "hours_tue": str(row["HoursPerDay"]),
                "hours_wed": str(row["HoursPerDay"]),
                "hours_thu": str(row["HoursPerDay"]),
                "hours_fri": str(row["HoursPerDay"]),
                "hours_sat": "0.00",
                "hours_sun": "0.00",
                "raw_ims_data": clean_nan_values(row.to_dict()),
            },
        }
        fixtures.append(fixture)

    output_file = fixtures_dir / "staff.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)

    print(f"Created {len(fixtures)} staff fixtures in {output_file}")


if __name__ == "__main__":
    input_file = (
        r"C:\Users\User\Downloads\""
        r"Morris Sheetmetal Works 2015 L_employee_list_2024_11_20.txt"
    )
    convert_ims_to_fixtures(input_file)
