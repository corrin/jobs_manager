# Error Management and Logging

## 🚨 MANDATORY DEFENSIVE PHILOSOPHY 🚨

### Core Principles

```python
"""
ABSOLUTE RULE: FAIL EARLY, NO FALLBACKS
- Fail early and explicitly
- NEVER use silent fallbacks
- ALWAYS persist errors to the database
- NEVER continue execution after a critical error
"""
```

### Mandatory Error Persistence

```python
# ALWAYS use the error persistence system
from apps.workflow.services.error_persistence import persist_app_error

def risky_operation():
    """Operation that may fail - mandatory pattern."""
    try:
        # Risky operation
        result = external_api_call()
        # Strict validation - fail if criteria not met
        if not result or not result.get('success'):
            raise ValueError(f"API returned invalid result: {result}")
        return result
    except Exception as e:
        # MANDATORY: Persist error to the database
        persist_app_error(e)
        # MANDATORY: Re-raise - NEVER swallow exceptions
        raise
```

## Error Persistence System

### AppError Model

```python
# apps/workflow/models/app_error.py
import uuid
import traceback
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AppError(models.Model):
    """Model to persist ALL application errors."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Error identification
    error_type = models.CharField(max_length=200)  # Exception.__class__.__name__
    error_message = models.TextField()
    error_code = models.CharField(max_length=50, blank=True)
    # Technical context
    traceback = models.TextField()
    module_name = models.CharField(max_length=200)
    function_name = models.CharField(max_length=200)
    line_number = models.IntegerField(null=True)
    # Business context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_data = models.JSONField(default=dict, blank=True)
    # Application context
    job_id = models.UUIDField(null=True, blank=True)
    client_id = models.UUIDField(null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    # Metadata
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical')
        ],
        default='medium'
    )
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = 'workflow_app_error'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['error_type', 'created_at']),
            models.Index(fields=['severity', 'resolved']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['job_id']),
        ]
    def __str__(self):
        return f"{self.error_type}: {self.error_message[:100]}"
```

### Error Persistence Service

```python
# apps/workflow/services/error_persistence.py
import traceback
import inspect
from typing import Optional, Dict, Any
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from apps.workflow.models.app_error import AppError

def persist_app_error(
    exception: Exception,
    request: Optional[HttpRequest] = None,
    context: Optional[Dict[str, Any]] = None,
    severity: str = 'medium'
) -> AppError:
    """
    Persist error to the database.
    MANDATORY to use in ALL except blocks.
    """
    # Extract traceback info
    tb = traceback.extract_tb(exception.__traceback__)
    if tb:
        last_frame = tb[-1]
        module_name = last_frame.filename.split('/')[-1]
        function_name = last_frame.name
        line_number = last_frame.lineno
    else:
        module_name = 'unknown'
        function_name = 'unknown'
        line_number = None
    # Prepare request data
    request_data = {}
    request_path = ''
    request_method = ''
    user = None
    session_key = ''
    if request:
        request_path = request.path
        request_method = request.method
        session_key = request.session.session_key or ''
        # Capture request data (sanitized)
        if hasattr(request, 'data'):
            request_data = sanitize_request_data(request.data)
        elif request.method == 'POST':
            request_data = sanitize_request_data(request.POST.dict())
        elif request.method == 'GET':
            request_data = sanitize_request_data(request.GET.dict())
        # User (if authenticated)
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            user = request.user
    # Extract business context
    job_id = None
    client_id = None
    if context:
        job_id = context.get('job_id')
        client_id = context.get('client_id')
    # Create error record
    app_error = AppError.objects.create(
        error_type=exception.__class__.__name__,
        error_message=str(exception),
        error_code=getattr(exception, 'code', ''),
        traceback=traceback.format_exc(),
        module_name=module_name,
        function_name=function_name,
        line_number=line_number,
        user=user,
        request_path=request_path,
        request_method=request_method,
        request_data=request_data,
        job_id=job_id,
        client_id=client_id,
        session_key=session_key,
        severity=severity
    )
    return app_error

def sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive request data."""
    sensitive_fields = ['password', 'token', 'api_key', 'secret', 'csrf']
    sanitized = {}
    for key, value in data.items():
        if any(field in key.lower() for field in sensitive_fields):
            sanitized[key] = '[REDACTED]'
        else:
            sanitized[key] = str(value)[:500]  # Limit size
    return sanitized
```

## Error Handling Patterns

### Validation Errors

```python
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

class JobService:
    """Service with strict error handling."""
    @staticmethod
    def create_job(job_data: dict, user, request=None) -> Job:
        """Create job with strict validation."""
        try:
            # Mandatory data validation
            if not job_data.get('name'):
                raise ValidationError("Job name is required")
            if not job_data.get('client_id'):
                raise ValidationError("Client is required")
            # Check if client exists
            try:
                client = Client.objects.get(id=job_data['client_id'])
            except Client.DoesNotExist:
                raise ValidationError(f"Client {job_data['client_id']} not found")
            # Business rule validation
            if client.status != 'active':
                raise ValidationError(f"Client {client.name} is not active")
            # Create job
            job = Job.objects.create(
                name=job_data['name'],
                client=client,
                created_by=user,
                status='draft'
            )
            return job
        except ValidationError as e:
            # Persist validation error
            persist_app_error(
                e,
                request=request,
                context={'client_id': job_data.get('client_id')},
                severity='low'
            )
            raise
        except Exception as e:
            # Persist unexpected error
            persist_app_error(
                e,
                request=request,
                context={'job_data': job_data},
                severity='high'
            )
            raise
```

## Logging System

### Logging Configuration

```python
# settings.py (excerpt)
import os

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "access": {
            "format": "{message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "sql_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/debug_sql.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "xero_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/xero_integration.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "purchase_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/purchase_debug.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "app_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/application.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "scheduler_file": {
            "level": "INFO",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/scheduler.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "ai_extraction_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/ai_extraction.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "ai_chat_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/ai_chat.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "access_file": {
            "level": "INFO",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/access.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "access",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["sql_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "xero": {
            "handlers": ["xero_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "xero_python": {
            "handlers": ["xero_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "workflow": {
            "handlers": ["app_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.purchasing.views": {
            "handlers": ["purchase_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django_apscheduler": {
            "handlers": ["console", "scheduler_file"],
            "level": "INFO",
            "propagate": False,
        },
        "access": {
            "handlers": ["access_file"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.quoting.services.ai_price_extraction": {
            "handlers": ["ai_extraction_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.quoting.services.providers": {
            "handlers": ["ai_extraction_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.job.services.gemini_chat_service": {
            "handlers": ["ai_chat_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.job.services.mcp_chat_service": {
            "handlers": ["ai_chat_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.job.views.job_quote_chat_api": {
            "handlers": ["ai_chat_file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
    "root": {
        "handlers": ["console", "app_file", "mail_admins"],
        "level": "DEBUG",
    },
}
```

### Logging Patterns

```python
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class JobService:
    """Service with structured logging."""
    @staticmethod
    def create_job(job_data: dict, user) -> Job:
        """Create job with full logging."""
        # Log operation start
        logger.info(
            "Starting job creation",
            extra={
                'user_id': user.id,
                'job_name': job_data.get('name'),
                'client_id': job_data.get('client_id'),
                'operation': 'create_job'
            }
        )
        try:
            # Validations...
            job = Job.objects.create(...)
            # Log success
            logger.info(
                "Job created successfully",
                extra={
                    'job_id': job.id,
                    'job_name': job.name,
                    'user_id': user.id,
                    'operation': 'create_job',
                    'status': 'success'
                }
            )
            return job
        except Exception as e:
            # Log error (in addition to persistence)
            logger.error(
                "Error creating job",
                extra={
                    'user_id': user.id,
                    'job_data': job_data,
                    'error_type': e.__class__.__name__,
                    'error_message': str(e),
                    'operation': 'create_job',
                    'status': 'error'
                },
                exc_info=True
            )
            # Persist error and re-raise
            persist_app_error(e)
            raise
```

### Performance Logging

```python
import time
import functools
from django.db import connection

def log_performance(operation_name: str):
    """Decorator for performance logging."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            initial_queries = len(connection.queries)
            try:
                result = func(*args, **kwargs)
                # Log success with metrics
                execution_time = time.time() - start_time
                query_count = len(connection.queries) - initial_queries
                logger.info(
                    f"Operation {operation_name} completed",
                    extra={
                        'operation': operation_name,
                        'execution_time': execution_time,
                        'query_count': query_count,
                        'status': 'success'
                    }
                )
                return result
            except Exception as e:
                # Log error with metrics
                execution_time = time.time() - start_time
                logger.error(
                    f"Error in operation {operation_name}",
                    extra={
                        'operation': operation_name,
                        'execution_time': execution_time,
                        'error_type': e.__class__.__name__,
                        'error_message': str(e),
                        'status': 'error'
                    }
                )
                raise
        return wrapper
    return decorator

# Usage of the decorator
@log_performance('create_cost_set')
def create_cost_set_with_lines(job: Job, cost_data: dict) -> CostSet:
    """Create CostSet with performance logging."""
    # Implementation...
    pass
```

## Related References

- See: [01-architecture-design-patterns.md](./01-architecture-design-patterns.md)
- See: [04-data-handling-persistence.md](./04-data-handling-persistence.md)
- See: [08-security-performance.md](./08-security-performance.md)
