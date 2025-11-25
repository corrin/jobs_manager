import uuid
from typing import Any, List, Optional

from django.contrib.auth import get_user_model


def get_excluded_staff(
    apps_registry: Optional[Any] = None, *, target_date=None
) -> List[str]:
    """
    Returns a list of staff IDs that should be excluded from the UI.

    Excludes only staff with no working hours configured at all (completely inactive).
    """
    excluded = []

    try:
        if apps_registry:
            Staff = apps_registry.get_model("accounts", "Staff")
        else:
            Staff = get_user_model()

        # Exclude staff members with no working hours at all
        staff_queryset = (
            Staff.objects.active_on_date(target_date)
            if target_date
            else Staff.objects.currently_active()
        )
        staff_with_ids = staff_queryset.values_list(
            "id",
            "ims_payroll_id",
            "first_name",
            "last_name",
            "hours_mon",
            "hours_tue",
            "hours_wed",
            "hours_thu",
            "hours_fri",
            "hours_sat",
            "hours_sun",
        )

        for staff_id, ims_payroll_id, first_name, last_name, *hours in staff_with_ids:
            # Check for null/empty first_name
            if not first_name or first_name.strip() == "":
                pass  # No logging

            # Check if staff has ANY working hours configured (at least one day > 0)
            has_any_working_hours = any((h or 0) > 0 for h in hours)

            if not has_any_working_hours:
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
