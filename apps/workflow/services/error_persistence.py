import traceback

from apps.workflow.exceptions import XeroValidationError
from apps.workflow.models import AppError, XeroError


def persist_xero_error(exc: XeroValidationError):
    """Create and save a ``XeroError`` from the given exception."""
    XeroError.objects.create(
        message=str(exc),
        data={"missing_fields": exc.missing_fields},
        entity=exc.entity,
        reference_id=exc.xero_id,
        kind="Xero",
    )


def persist_app_error(exc: Exception):
    """Create and save a generic ``AppError`` instance."""
    AppError.objects.create(
        message=str(exc),
        data={"trace": traceback.format_exc()},
    )
