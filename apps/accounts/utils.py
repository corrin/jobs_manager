import uuid
from typing import Any, List, Optional

from django.contrib.auth import get_user_model


def get_excluded_staff(apps_registry: Optional[Any] = None) -> List[str]:
    """
    Returns a list of staff IDs that should be excluded from the UI.

    This typically includes system users or other special accounts.
    """
    excluded = []

    try:
        if apps_registry:
            Staff = apps_registry.get_model("accounts", "Staff")
        else:
            Staff = get_user_model()

        # Exclude staff members with no valid IMS payroll ID
        staff_with_ids = Staff.objects.filter(is_active=True).values_list(
            "id", "ims_payroll_id", "first_name", "last_name"
        )

        for staff_id, ims_payroll_id, first_name, last_name in staff_with_ids:
            # Check for null/empty first_name
            if not first_name or first_name.strip() == "":
                pass  # No logging

            is_valid = is_valid_uuid(str(ims_payroll_id))
            if not is_valid:
                excluded.append(str(staff_id))
            else:
                pass  # No logging

    except Exception:
        # Return empty list when Staff model can't be accessed
        pass

    return excluded


def is_valid_uuid(val: Any) -> bool:
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False
