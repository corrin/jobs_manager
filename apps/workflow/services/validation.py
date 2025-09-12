from apps.workflow.exceptions import XeroValidationError


def validate_required_fields(fields: dict, entity: str, xero_id):
    """Raise XeroValidationError if any value in ``fields`` is ``None``."""
    missing = [name for name, value in fields.items() if value is None]
    if missing:
        raise XeroValidationError(missing, entity, xero_id)
    return fields
