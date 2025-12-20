import uuid
from datetime import date
from typing import Any, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import QuerySet


def get_excluded_staff(
    apps_registry: Optional[Any] = None, *, target_date=None
) -> List[str]:
    """
    Returns a list of staff IDs that should be excluded from the UI.

    Excludes staff without a valid Xero payroll ID (UUID format).
    This filters out developers and admin accounts.

    Note: date_left filtering is handled separately by Staff manager methods
    (active_on_date, currently_active, active_between_dates).
    """
    excluded = []

    try:
        if apps_registry:
            Staff = apps_registry.get_model("accounts", "Staff")
        else:
            Staff = get_user_model()

        staff_queryset = (
            Staff.objects.active_on_date(target_date)
            if target_date
            else Staff.objects.currently_active()
        )

        for staff_id, xero_user_id in staff_queryset.values_list("id", "xero_user_id"):
            if not xero_user_id or not is_valid_uuid(xero_user_id):
                excluded.append(str(staff_id))

    except Exception:
        # Return empty list when Staff model can't be accessed
        pass

    return excluded


def get_displayable_staff(
    *,
    target_date: Optional[date] = None,
    date_range: Optional[Tuple[date, date]] = None,
    order_by: Tuple[str, ...] = ("first_name", "last_name"),
) -> QuerySet:
    """
    Get staff members suitable for display in UI lists.

    Filters applied:
    - Active on the specified date/range (not left per date_left field)
    - Has a valid Xero payroll ID (excludes developers/admins)

    Use this instead of manually combining active filtering + get_excluded_staff().

    Args:
        target_date: Filter for staff active on this specific date
        date_range: Filter for staff active during this date range (start, end)
        order_by: Fields to order by (default: first_name, last_name)

    Returns:
        QuerySet of displayable staff members

    Examples:
        # Current week timesheet
        staff = get_displayable_staff(date_range=(monday, sunday))

        # Specific date view
        staff = get_displayable_staff(target_date=some_date)

        # Currently active staff
        staff = get_displayable_staff()
    """
    Staff = get_user_model()

    # Determine the base queryset and effective date for exclusion checks
    if date_range:
        start_date, end_date = date_range
        queryset = Staff.objects.active_between_dates(start_date, end_date)
        effective_date = start_date
    elif target_date:
        queryset = Staff.objects.active_on_date(target_date)
        effective_date = target_date
    else:
        queryset = Staff.objects.currently_active()
        effective_date = None  # currently_active() uses today internally

    # Exclude developers/admins (no valid Xero payroll ID)
    excluded_staff_ids = get_excluded_staff(target_date=effective_date)
    queryset = queryset.exclude(id__in=excluded_staff_ids)

    # Apply ordering
    if order_by:
        queryset = queryset.order_by(*order_by)

    return queryset


def is_valid_uuid(val: Any) -> bool:
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False
