import json
import logging

from apps.workflow.exceptions import XeroValidationError

logger = logging.getLogger("xero")


def validate_required_fields(fields: dict, entity: str, xero_id):
    """Raise XeroValidationError if any value in ``fields`` is ``None``."""
    missing = [name for name, value in fields.items() if value is None]
    if missing:
        raw_json = fields.get("raw_json", {})
        logger.error(
            f"Validation failed for {entity} {xero_id}: "
            f"missing={missing}\nraw_json={json.dumps(raw_json, indent=2, default=str)}"
        )
        raise XeroValidationError(missing, entity, xero_id)
    return fields
