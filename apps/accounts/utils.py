import logging
import uuid

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def get_excluded_staff(apps_registry=None) -> list[str]:
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
            "id", "ims_payroll_id"
        )

        for staff_id, ims_payroll_id in staff_with_ids:
            if not is_valid_uuid(str(ims_payroll_id)):
                excluded.append(str(staff_id))

        logger.info(f"Successfully retrieved {len(excluded)} excluded staff.")
    except Exception as e:
        logger.warning(f"Unable to access Staff model: {e}. No staff will be excluded.")
        # Return empty list when Staff model can't be accessed

    return excluded


def is_valid_uuid(val):
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False
