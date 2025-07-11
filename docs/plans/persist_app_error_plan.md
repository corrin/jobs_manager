# Enhanced Error Persistence System Plan

## Current State Analysis

### Existing Implementation Issues

The current `persist_app_error` function in `apps/workflow/services/error_persistence.py` has several limitations:

1. **Lasagne Function**: It's a wrapper that adds no value - simply calls `AppError.objects.create()` with basic parameters
2. **Limited Context**: Only captures exception message and stack trace, missing crucial business context
3. **No Categorization**: No way to filter errors by app section, function name, or severity
4. **Poor Frontend Support**: Limited filtering capabilities for error analysis and debugging

### Current Architecture

```python
def persist_app_error(exc: Exception):
    """Create and save a generic ``AppError`` instance."""
    AppError.objects.create(
        message=str(exc),
        data={"trace": traceback.format_exc()},
    )
```

**AppError Model Structure:**
```python
class AppError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    data = models.JSONField(blank=True, null=True)
```

### Current Usage Patterns

The function is used across multiple apps:
- **Accounting Services**: Job aging calculations, KPI calculations
- **Xero Sync**: API synchronization processes
- **API Views**: Error handling in REST endpoints
- **General Error Handling**: Throughout the application

## Proposed Enhancement

### 1. Enhanced AppError Model

Add contextual fields to support better error categorization and filtering:

```python
class AppError(models.Model):
    # Existing fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    data = models.JSONField(blank=True, null=True)
    
    # Code location fields for filtering
    app = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'workflow', 'accounting'
    file = models.CharField(max_length=200, blank=True, null=True)  # e.g., 'services.py', 'xero/sync.py'
    function = models.CharField(max_length=100, blank=True, null=True)  # e.g., 'get_job_aging_data'
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='ERROR')
    
    # Commonly filtered business context (separate fields)
    job_id = models.UUIDField(blank=True, null=True)  # Most common filter
    user_id = models.UUIDField(blank=True, null=True)  # Common for user-specific errors
    
    # Error resolution tracking
    resolved = models.BooleanField(default=False)  # Error resolution status
    resolved_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, blank=True, null=True)  # Staff who resolved the error
    resolved_timestamp = models.DateTimeField(blank=True, null=True)  # When error was resolved
    
    def mark_resolved(self, staff_member):
        """Mark this error as resolved by the given staff member."""
        from django.utils import timezone  # MAKE SURE THIS GOES AT THE TOP OF THE FILE
        self.resolved = True
        self.resolved_by = staff_member
        self.resolved_timestamp = timezone.now()
        self.save()
    
    # Additional context stored in JSON (flexible, not directly filterable)
    # This would include: staff_id, entity_type, entity_id, request_path, etc.
```

**Severity Choices:**
- `CRITICAL`: System-breaking errors that stop core functionality
- `ERROR`: Standard errors that affect functionality
- `WARNING`: Non-critical issues that don't stop processing
- `INFO`: Informational messages for debugging

### 2. Enhance persist_app_error Function

Keep the existing `persist_app_error` function name but enhance it with contextual parameters:

```python
def persist_app_error(
    exception: Exception,
    app: str = None,
    file: str = None,
    function: str = None,
    severity: str = 'ERROR',
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
```

**Migration Strategy**: The function maintains backward compatibility - existing calls like `persist_app_error(exc)` continue to work, while new calls can add context parameters.

### 4. Business Context Strategy

**Direct Filter Fields**: Only `job_id` and `user_id` as separate fields since these are the most commonly filtered business entities.

**JSON Context**: Everything else goes in the `data` JSON field for flexibility:
- `staff_id`: ID of staff member involved
- `entity_type`: Type of business entity (Job, Client, PurchaseOrder, etc.)
- `entity_id`: ID of the specific entity
- `request_path`: URL path where error occurred
- `request_method`: HTTP method (GET, POST, etc.)
- `xero_entity_id`: Xero-specific entity references
- `sync_operation`: Type of sync operation (contact_sync, invoice_sync, etc.)

**API Usage**:
- **Primary Filters**: App, File, Function, Severity, Job ID, User ID, Resolved Status (database-level filtering via API)
- **Secondary Display**: JSON context available in API responses for frontend display
- **Search**: Full-text search across message and JSON context via API endpoints
- **Error Resolution**: Mark errors as resolved with staff assignment and timestamp tracking

### 4. Context Extraction Utilities

Create utility functions to extract context from Django request objects and common business objects:

```python
def extract_request_context(request):
    """Extract context from Django request object."""
    return {
        'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
        'request_path': request.path if hasattr(request, 'path') else None,
        'request_method': request.method if hasattr(request, 'method') else None,
    }

def extract_job_context(job):
    """Extract context from Job object."""
    return {
        'job_id': job.id if job else None,
        'entity_type': 'Job',
        'entity_id': str(job.id) if job else None,
        'business_process': 'Job Management'
    }
```

## Implementation Plan

### Commit 1: Database Foundation (Tasks 1-2) ✅ COMPLETED
- ✅ Create migration for new AppError fields (app, file, function, severity, job_id, user_id)
- ✅ Add database indexes for frequently filtered fields
- ✅ This provides the core data structure needed for everything else

**Implementation Notes:**
- Enhanced AppError model with new fields: app, file, function, severity (using logging constants), job_id, user_id
- Added error resolution tracking: resolved, resolved_by, resolved_timestamp
- Added mark_resolved() and mark_unresolved() methods for error resolution workflow
- Created database indexes for common query patterns: timestamp+severity, resolved+timestamp, app+severity
- Migration created and applied: 0168_enhance_app_error_model.py
- Tested: Successfully created AppError with new fields
- Committed: eeb06c72

```python
# Migration example
class Migration(migrations.Migration):
    dependencies = [
        ('workflow', '0165_app_error_models'),
    ]

    operations = [
        migrations.AddField('AppError', 'app', models.CharField(max_length=50, blank=True, null=True)),
        migrations.AddField('AppError', 'file', models.CharField(max_length=200, blank=True, null=True)),
        migrations.AddField('AppError', 'function', models.CharField(max_length=100, blank=True, null=True)),
        migrations.AddField('AppError', 'severity', models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='ERROR')),
        migrations.AddField('AppError', 'job_id', models.UUIDField(blank=True, null=True)),
        migrations.AddField('AppError', 'user_id', models.UUIDField(blank=True, null=True)),
        migrations.AddField('AppError', 'resolved', models.BooleanField(default=False)),
        migrations.AddField('AppError', 'resolved_by', models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, blank=True, null=True)),
        migrations.AddField('AppError', 'resolved_timestamp', models.DateTimeField(blank=True, null=True)),
        migrations.AddIndex('AppError', ['timestamp', 'severity']),  # Common: recent errors by severity
        migrations.AddIndex('AppError', ['resolved', 'timestamp']),  # Common: unresolved errors chronologically
        migrations.AddIndex('AppError', ['app', 'severity']),  # Common: errors by app section
    ]
```

### Commit 2: Core Service Enhancement (Tasks 3-5) ✅ COMPLETED
- ✅ Context extraction utilities (extract_request_context, extract_job_context)
- ✅ Enhanced persist_app_error function with new parameters
- ✅ Severity/app constants (using logging module constants)
- ✅ This establishes the enhanced API while maintaining backward compatibility

**Implementation Notes:**
- Added extract_request_context() for Django request context (user_id, path, method)
- Added extract_job_context() for Job model context (follows defensive programming - no null checks)
- Enhanced persist_app_error() with parameters: app, file, function, severity, job_id, user_id, additional_context
- Maintains backward compatibility - existing persist_app_error(exc) calls still work
- Uses logging constants directly (logging.ERROR, logging.WARNING, etc.)
- Tested: Successfully created AppError with enhanced contextual information
- Committed: 2a5766f4

### Commit 3: High-Priority Error Handling (Tasks 6-8) ✅ COMPLETED
- ✅ Update Xero sync operations with enhanced error context
- ✅ Update Job Aging Service error handling
- ✅ Update KPI Service error handling (partial - main areas covered)
- ✅ These are the most critical error-prone areas that need immediate improvement

**Implementation Notes:**
- Enhanced error persistence service with auto-extraction of caller context (app, file, function)
- Added comprehensive documentation explaining auto-extraction with override capability
- Updated 5 Xero sync error calls with meaningful business context (entity types, IDs, operations)
- Updated 3 Job Aging Service error calls with job context and operation details
- All enhanced calls leverage automatic technical context extraction
- Maintains full backward compatibility with existing persist_app_error(exc) calls
- Tested: Successfully created AppError with job_id and contextual information
- Committed: 8ad30fd0

### Commit 4: Remaining Service Updates (Tasks 9-10)
- Update API views to include request context and user information
- Update remaining service layer error handling with business process context
- This completes the backend implementation

### Commit 5: API Endpoints Enhancement (Tasks 11-12)
- Create AppError API endpoints (serializer, list/detail views, URLs) following existing XeroError pattern
- Add filtering capabilities to AppError API endpoints for frontend consumption
- This provides the user-facing API for error analysis

## Implementation Examples

### Before (Current)
```python
# In job aging service
try:
    job_data = calculate_job_aging()
except Exception as exc:
    logger.error(f"Error calculating job aging: {str(exc)}")
    persist_app_error(exc)  # Minimal context
    return []
```

### After (Enhanced)
```python
# In job aging service
try:
    job_data = calculate_job_aging()
except Exception as exc:
    logger.error(f"Error calculating job aging: {str(exc)}")
    AppError.objects.create(
        message=str(exc),
        data={"trace": traceback.format_exc()},
        app_section='Accounting',
        function_name='get_job_aging_data',
        severity='ERROR',
        business_process='Job Aging Analysis'
    )
    return []
```

### Django View Example
```python
# In API view
try:
    result = service.process_data()
except Exception as exc:
    request_context = extract_request_context(request)
    AppError.objects.create(
        message=str(exc),
        data={"trace": traceback.format_exc()},
        app_section='API',
        function_name='process_data_endpoint',
        severity='ERROR',
        user_id=request_context['user_id'],
        request_path=request_context['request_path']
    )
    return Response({'error': 'Processing failed'}, status=500)
```

## Benefits

### 1. Enhanced Debugging
- **Contextual Information**: Know exactly where errors occurred and under what conditions
- **Business Context**: Understand which jobs, users, or processes are affected
- **Pattern Recognition**: Identify recurring issues in specific areas

### 2. Improved Monitoring
- **App-Level Filtering**: Focus on specific application sections (Xero, Accounting, etc.)
- **Severity-Based Alerts**: Different alert levels for different error types
- **User Impact Analysis**: Track which users are experiencing issues

### 3. Better Error Analysis
- **Trending**: Track error patterns over time
- **Root Cause Analysis**: Better context for debugging
- **Performance Impact**: Identify which processes are failing most frequently

### 4. API Capabilities
- **Advanced Filtering**: Filter by app section, function name, severity via API endpoints
- **Frontend Integration**: Vue.js frontend can consume enhanced error data
- **User-Specific Views**: API endpoints support filtering by user or role

## Migration Strategy

### Backward Compatibility
- All existing `persist_app_error` calls continue to work
- New fields are optional and nullable
- Gradual migration prevents breaking changes

### Testing Approach
- Unit tests for new error creation functions
- Integration tests for context extraction
- Manual testing of error filtering in admin interface

### Rollback Plan
- Database migration can be reversed if needed
- Old `persist_app_error` function can be restored
- New fields can be ignored in rollback scenarios

## Success Metrics

1. **Error Resolution Time**: Reduced time to identify and fix issues
2. **Error Categorization**: 100% of errors have appropriate context
3. **False Positive Reduction**: Better filtering reduces noise in error reports
4. **User Experience**: Improved error handling and reporting

## Commit Timeline

- **Commit 1**: Database foundation (migration + indexes)
- **Commit 2**: Core service enhancement (utilities + enhanced persist_app_error)
- **Commit 3**: High-priority error handling (Xero sync, Job Aging, KPI services)
- **Commit 4**: Remaining service updates (API views + remaining services)
- **Commit 5**: API endpoints enhancement (AppError API following XeroError pattern)

This enhanced error persistence system will provide significantly better debugging capabilities while maintaining backward compatibility and following the defensive programming principles outlined in the project's architecture guidelines.