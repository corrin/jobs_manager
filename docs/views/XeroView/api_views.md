# Xero API Views

## Business Purpose
Provides REST API endpoints for Xero error tracking and monitoring. Supports debugging and troubleshooting of Xero integration issues with paginated access to error logs and detailed error information.

## Views

### XeroErrorListAPIView
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Class-based view (ListAPIView)
**URL**: `/workflow/api/xero/errors/`

#### What it does
- Lists all Xero integration errors with pagination
- Provides chronological error history for debugging
- Supports API-based error monitoring and reporting
- Returns structured error data for frontend consumption

#### Parameters
- Standard pagination parameters (page, limit)
- Ordering by timestamp (newest first)

#### Returns
- **200 OK**: Paginated list of Xero errors with serialized data
- **500 Internal Server Error**: Error retrieval failures

#### Integration
- XeroError model for error storage and tracking
- XeroErrorSerializer for consistent API response format
- FiftyPerPagePagination for manageable result sets
- Timestamp-based ordering for chronological error tracking

### XeroErrorDetailAPIView
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Class-based view (RetrieveAPIView)
**URL**: `/workflow/api/xero/errors/<int:pk>/`

#### What it does
- Retrieves detailed information for specific Xero errors
- Provides comprehensive error context and stack traces
- Supports detailed debugging and error analysis
- Returns complete error record with all available details

#### Parameters
- `pk`: Primary key of XeroError record (path parameter)

#### Returns
- **200 OK**: Detailed error information with full context
- **404 Not Found**: Error record not found
- **500 Internal Server Error**: Error detail retrieval failures

#### Integration
- XeroError model for detailed error record access
- XeroErrorSerializer for structured error data presentation
- Complete error context including timestamps, messages, and traces
- Support for error analysis and debugging workflows

## Error Data Structure

### XeroError Model Fields
- **timestamp**: When the error occurred
- **error_type**: Classification of error (authentication, API, validation, etc.)
- **message**: Human-readable error description
- **details**: Technical error details and context
- **stack_trace**: Full stack trace for debugging
- **xero_entity**: Affected Xero entity (invoice, contact, etc.)
- **local_record_id**: Related local system record
- **xero_response**: Raw Xero API response data

### Serialization
- Complete error context for debugging
- Timestamp formatting for consistent display
- Structured error categorization
- Related record identification

## Error Handling
- **404 Not Found**: Specific error records not found
- **500 Internal Server Error**: API system failures or database errors
- Comprehensive logging for API endpoint monitoring
- Graceful degradation for error tracking system failures

## Integration Points
- Xero synchronization services for error logging
- Document management views for error context
- Frontend error monitoring and alerting systems
- Debugging and troubleshooting workflows

## Usage Patterns
- Error monitoring dashboards
- Integration health checking
- Debugging specific sync failures
- Historical error analysis and trending
- Support team troubleshooting workflows
