# API Design Standards

## RESTful Principles

### URL and Resource Conventions

```python
# Resources - plural nouns
/api/jobs/                    # List of jobs
/api/jobs/{id}/               # Specific job
/api/clients/                 # List of clients
/api/purchase-orders/         # Purchase orders (kebab-case for compounds)

# Nested sub-resources
/api/jobs/{job_id}/cost-sets/           # Cost sets for a job
/api/jobs/{job_id}/events/              # Events for a job
/api/cost-sets/{id}/cost-lines/         # Cost lines for a cost set

# Specific actions - use verbs only when necessary
/api/jobs/{id}/accept-quote/            # POST - accept quote
/api/jobs/{id}/toggle-complex-mode/     # POST - toggle complex mode
/api/xero/sync/                         # POST - start sync
```

### Standardized HTTP Methods

```python
# GET - Retrieve data
GET /api/jobs/                    # List all jobs
GET /api/jobs/{id}/               # Get specific job

# POST - Create new resources
POST /api/jobs/                   # Create new job
POST /api/jobs/{id}/events/       # Add event to job

# PUT - Update entire resource
PUT /api/jobs/{id}/               # Update entire job

# PATCH - Partial update
PATCH /api/jobs/{id}/             # Update specific fields

# DELETE - Remove resource
DELETE /api/jobs/{id}/            # Delete job
```

## HTTP Status Codes

### Standard Status Usage

```python
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

class JobCreateApiView(APIView):
    def post(self, request):
        try:
            job = JobService.create_job(request.data, request.user)
            serializer = JobSerializer(job)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class JobDeleteApiView(APIView):
    def delete(self, request, pk):
        try:
            result = JobService.delete_job(pk, request.user)
            return Response(result, status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

### Mandatory Status Codes

- **200 OK** - Success for GET, PUT, PATCH
- **201 Created** - Resource created successfully
- **204 No Content** - Success for DELETE
- **400 Bad Request** - Invalid data or validation error
- **401 Unauthorized** - Not authenticated
- **403 Forbidden** - Not authorized for this action
- **404 Not Found** - Resource not found
- **409 Conflict** - State conflict (e.g., job already accepted)
- **422 Unprocessable Entity** - Business validation error
- **500 Internal Server Error** - Internal server error

## Payload Structure

### Standard Response Format

```python
# Success response - single resource
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Gate Fabrication",
    "status": "in_progress",
    "client": {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "name": "ABC Client Ltd."
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T14:20:00Z"
}

# Paginated list response
{
    "count": 150,
    "next": "http://api.example.com/jobs/?page=3",
    "previous": "http://api.example.com/jobs/?page=1",
    "results": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Job 1",
            // ... other fields
        }
    ]
}

# Error response
{
    "error": "Job name is required",
    "details": {
        "name": ["This field is required"],
        "client_id": ["Client not found"]
    },
    "code": "VALIDATION_ERROR"
}
```

### Request Validation

```python
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

class JobCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=True)
    client_id = serializers.UUIDField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Name cannot be empty")
        return value.strip()
    def validate_client_id(self, value):
        if not Client.objects.filter(id=value).exists():
            raise ValidationError("Client not found")
        return value
    def validate(self, attrs):
        # Cross-field validation
        if attrs.get('priority') == 'urgent' and not attrs.get('due_date'):
            raise ValidationError({
                'due_date': 'Due date is required for urgent jobs'
            })
        return attrs
```

## Authentication and Authorization

### Authentication Patterns

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "jobs_manager.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# JWT settings (SIMPLE_JWT)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIMS": "token_type",
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_SECURE": use_secure_cookies(),
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": "Lax",
    "AUTH_COOKIE_DOMAIN": get_cookie_domain(),
    "REFRESH_COOKIE": "refresh_token",
    "REFRESH_COOKIE_SECURE": use_secure_cookies(),
    "REFRESH_COOKIE_HTTP_ONLY": True,
    "REFRESH_COOKIE_SAMESITE": "Lax",
}

# ViewSet implementation
from rest_framework.permissions import IsAuthenticated

class JobViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    # ...
```

### Custom Permissions

```python
from rest_framework.permissions import BasePermission

class CanDeleteJob(BasePermission):
    """Permission to delete jobs."""
    def has_object_permission(self, request, view, obj):
        # Only creator or admin can delete
        return (
            request.user.is_office_staff or
            obj.created_by == request.user
        )

class CanModifyJob(BasePermission):
    """Permission to modify jobs."""
    def has_object_permission(self, request, view, obj):
        # Cannot modify archived jobs
        if obj.status == 'archived':
            return False
        # Check if user has access to the job
        return obj.people.filter(id=request.user.staff_profile.id).exists()
```

## Pagination

<!-- Pagination is not globally enforced. Most endpoints use APIView and return either full lists or custom paginated responses as needed. If pagination is required, use DRF's PageNumberPagination or custom logic per endpoint. -->

## Filtering and Search

### Filter Implementation

<!-- Filtering and search are implemented per APIView as needed. If using DRF filters, add DjangoFilterBackend, SearchFilter, or OrderingFilter to the specific APIView or use custom query logic. -->

### Custom Filters

```python
import django_filters
from django_filters import rest_framework as filters

class JobFilter(filters.FilterSet):
    # Date range filter
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    # Custom filter
    has_costs = filters.BooleanFilter(method='filter_has_costs')
    def filter_has_costs(self, queryset, name, value):
        if value:
            return queryset.filter(cost_sets__cost_lines__isnull=False).distinct()
        return queryset.filter(cost_sets__cost_lines__isnull=True).distinct()
    class Meta:
        model = Job
        fields = ['status', 'client', 'priority']
```

## Serialization

### Serializer Patterns

<!-- Serializers are defined per endpoint. Use ModelSerializer or Serializer as appropriate for each APIView. -->

### Nested Serializers

<!-- Nested serializers are used as needed per endpoint. See the implementation in each APIView for details. -->

## API Error Handling

### Custom Exception Handler

```python
from rest_framework.views import exception_handler
from rest_framework.response import Response
from apps.workflow.services.error_persistence import persist_app_error

def custom_exception_handler(exc, context):
    """Custom exception handler with error persistence."""
    # Persist error in the database
    persist_app_error(exc)
    # Get DRF's default response
    response = exception_handler(exc, context)
    if response is not None:
        custom_response_data = {
            'error': 'An error occurred while processing your request',
            'details': response.data,
            'status_code': response.status_code
        }
        # Add specific context for different error types
        if response.status_code == 400:
            custom_response_data['error'] = 'Invalid data provided'
        elif response.status_code == 404:
            custom_response_data['error'] = 'Resource not found'
        elif response.status_code == 403:
            custom_response_data['error'] = 'Permission denied'
        response.data = custom_response_data
    return response

# settings.py
# REST_FRAMEWORK = {
#     'EXCEPTION_HANDLER': 'apps.api.exceptions.custom_exception_handler'
# }
```

## API Documentation

### drf-spectacular Configuration

```python
# settings.py
SPECTACULAR_SETTINGS = {
    'TITLE': 'Jobs Manager API',
    'DESCRIPTION': 'API for Morris Sheetmetal job management system',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v[0-9]',
}

# Documentation in ViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(
        summary="List jobs",
        description="Returns a paginated list of all jobs with optional filters"
    ),
    create=extend_schema(
        summary="Create job",
        description="Creates a new job with provided data"
    ),
    retrieve=extend_schema(
        summary="Get job",
        description="Returns full details of a specific job"
    )
)
class JobViewSet(ModelViewSet):
    pass
```

## Related References

- See: [01-architecture-design-patterns.md](./01-architecture-design-patterns.md)
- See: [02-code-organization-structure.md](./02-code-organization-structure.md)
- See: [06-error-management-logging.md](./06-error-management-logging.md)
- See: [08-security-performance.md](./08-security-performance.md)
