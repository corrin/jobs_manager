import logging
import uuid
from typing import Any, List, Optional

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


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

        logger.info(
            "get_excluded_staff called - checking staff with invalid IMS payroll IDs"
        )

        # Exclude staff members with no valid IMS payroll ID
        staff_with_ids = Staff.objects.filter(is_active=True).values_list(
            "id", "ims_payroll_id", "first_name", "last_name"
        )

        logger.info(f"Found {len(staff_with_ids)} active staff members to check")

        for staff_id, ims_payroll_id, first_name, last_name in staff_with_ids:
            # Check for null/empty first_name
            if not first_name or first_name.strip() == "":
                logger.warning(
                    f"WARNING: Staff with null/empty first_name found: ID={staff_id}, first_name='{first_name}', last_name='{last_name}', ims_id={ims_payroll_id}"
                )

            is_valid = is_valid_uuid(str(ims_payroll_id))
            if not is_valid:
                excluded.append(str(staff_id))
                logger.info(
                    f"  - Excluding {first_name} {last_name} (ID: {staff_id}, IMS: {ims_payroll_id}) - invalid UUID"
                )
            else:
                logger.info(
                    f"  - Including {first_name} {last_name} (ID: {staff_id}, IMS: {ims_payroll_id}) - valid UUID"
                )

        logger.info(
            f"Successfully retrieved {len(excluded)} excluded staff (out of {len(staff_with_ids)} total active)."
        )
    except Exception as e:
        logger.warning(f"Unable to access Staff model: {e}. No staff will be excluded.")
        # Return empty list when Staff model can't be accessed

    return excluded


def is_valid_uuid(val: Any) -> bool:
    """Check if string is a valid UUID."""
    try:
        result = uuid.UUID(str(val))
        logger.info(f"is_valid_uuid({val}) -> True (parsed as {result})")
        return True
    except (ValueError, AttributeError) as e:
        logger.info(f"is_valid_uuid({val}) -> False (error: {e})")
        return False
