import logging
import traceback

from apps.workflow.exceptions import XeroValidationError
from apps.workflow.models import AppError, XeroError


def extract_request_context(request):
    """Extract context from Django request object."""
    return {
        'user_id': request.user.id if request.user.is_authenticated else None,
        'request_path': request.path,
        'request_method': request.method,
    }


def extract_job_context(job):
    """Extract context from Job object."""
    return {
        'job_id': job.id,
        'entity_type': 'Job',
        'entity_id': str(job.id),
        'business_process': 'Job Management'
    }


def persist_xero_error(exc: XeroValidationError):
    """Create and save a ``XeroError`` from the given exception."""
    XeroError.objects.create(
        message=str(exc),
        data={"missing_fields": exc.missing_fields},
        entity=exc.entity,
        reference_id=exc.xero_id,
        kind="Xero",
    )


def persist_app_error(
    exception: Exception,
    app: str = None,
    file: str = None,
    function: str = None,
    severity: int = logging.ERROR,
    job_id: str = None,
    user_id: str = None,
    additional_context: dict = None
) -> AppError:
    """Create and save an AppError with enhanced context."""
    context_data = {"trace": traceback.format_exc()}
    if additional_context:
        context_data.update(additional_context)
    
    return AppError.objects.create(
        message=str(exception),
        data=context_data,
        app=app,
        file=file,
        function=function,
        severity=severity,
        job_id=job_id,
        user_id=user_id
    )
