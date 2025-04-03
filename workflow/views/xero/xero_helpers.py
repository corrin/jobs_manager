# workflow/views/xero_helpers.py
import re
from datetime import date

def clean_payload(payload):
    """Remove null fields from payload."""
    if isinstance(payload, dict):
        return {k: clean_payload(v) for k, v in payload.items() if v is not None}
    if isinstance(payload, list):
        return [clean_payload(v) for v in payload if v is not None]
    return payload


def format_date(dt: date) -> str:
    """Formats a date object to YYYY-MM-DD string."""
    if not isinstance(dt, date):
        raise TypeError(f"Expected datetime.date, got {type(dt)}")
    return dt.strftime("%Y-%m-%d")


def convert_to_pascal_case(obj):
    """
    Recursively converts dictionary keys from snake_case to PascalCase.
    Handles keys starting with an underscore.
    """
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            # Handle potential leading underscores before converting
            if key.startswith("_"):
                 pascal_key = "_" + re.sub(r"(?:^|_)(.)", lambda x: x.group(1).upper(), key[1:])
            else:
                 pascal_key = re.sub(r"(?:^|_)(.)", lambda x: x.group(1).upper(), key)
            new_dict[pascal_key] = convert_to_pascal_case(value)
        return new_dict
    elif isinstance(obj, list):
        return [convert_to_pascal_case(item) for item in obj]
    else:
        return obj