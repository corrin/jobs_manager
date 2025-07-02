# Quote Import View Documentation

## Business Purpose
Manages external pricing data integration for jobbing shop quote generation. Originally supported Excel file imports, now evolved to Google Sheets integration for real-time quote synchronization. Enables importing detailed cost breakdowns from external spreadsheets into the job costing system, supporting accurate pricing and estimation workflows.

Note the spreadsheet uses a different data model to the app

## Views

### QuoteImportPreviewView (DEPRECATED)
**File**: `apps/job/views/quote_import_views.py`
**Type**: Class-based view (APIView with authentication)
**URL**: `/jobs/<job_id>/quote/import/preview/`

#### What it does
- **DEPRECATED**: Returns HTTP 410 Gone status with migration guidance
- Originally provided preview functionality for Excel quote imports
- Directs users to Google Sheets integration endpoints

#### Parameters
- `job_id`: Job UUID (path parameter)

#### Returns
- **410 Gone**: Deprecation notice with alternative endpoint information

### QuoteImportView (DEPRECATED)
**File**: `apps/job/views/quote_import_views.py`
**Type**: Class-based view (APIView with authentication)
**URL**: `/jobs/<job_id>/quote/import/`

#### What it does
- **DEPRECATED**: Returns HTTP 410 Gone status with migration guidance
- Originally handled Excel quote file imports
- Directs users to Google Sheets integration endpoints

#### Parameters
- `job_id`: Job UUID (path parameter)

#### Returns
- **410 Gone**: Deprecation notice with alternative endpoint information

### QuoteImportStatusView
**File**: `apps/job/views/quote_import_views.py`
**Type**: Class-based view (APIView with authentication)
**URL**: `/jobs/<job_id>/quote/status/`

#### What it does
- Retrieves current quote import status for a job
- Provides latest quote information and revision details
- Shows whether job has quote data and summary information

#### Parameters
- `job_id`: Job UUID (path parameter)

#### Returns
- **200 OK**: Job quote status with CostSet data if available
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Quote status retrieval failures

#### Integration
- Uses Job.get_latest("quote") for current quote data
- Integrates with CostSetSerializer for consistent API responses
- No direct Xero integration (internal quote status tracking)

## Modern Google Sheets Integration

### link_quote_sheet
**File**: `apps/job/views/quote_sync_views.py`
**Type**: Function-based view (API view with authentication)
**URL**: `/jobs/rest/jobs/<uuid:pk>/quote/link/`

#### What it does
- Links job to Google Sheets quote template
- Creates or connects to existing quote spreadsheet
- Enables real-time quote data synchronization

#### Parameters
- `pk`: Job UUID (path parameter)
- `template_url`: Optional Google Sheets template URL (JSON body)

#### Returns
- **200 OK**: Sheet URL, sheet ID, and job ID
- **400 Bad Request**: Service errors or invalid parameters
- **404 Not Found**: Job not found

### preview_quote
**File**: `apps/job/views/quote_sync_views.py`
**Type**: Function-based view (API view with authentication)
**URL**: `/jobs/rest/jobs/<uuid:pk>/quote/preview/`

#### What it does
- Previews quote changes from linked Google Sheet
- Shows potential cost line modifications without applying them
- Enables review before importing quote data

#### Parameters
- `pk`: Job UUID (path parameter)

#### Returns
- **200 OK**: Preview data with proposed changes
- **400 Bad Request**: Preview generation errors
- **404 Not Found**: Job not found

### apply_quote
**File**: `apps/job/views/quote_sync_views.py`
**Type**: Function-based view (API view with authentication)
**URL**: `/jobs/rest/jobs/<uuid:pk>/quote/apply/`

#### What it does
- Applies quote changes from linked Google Sheet
- Creates new CostSet with imported quote data
- Provides detailed change tracking (additions, updates, deletions)

#### Parameters
- `pk`: Job UUID (path parameter)

#### Returns
- **200 OK**: Success status with CostSet data and change details
- **400 Bad Request**: Application errors or invalid data
- **404 Not Found**: Job not found

## Error Handling
- **400 Bad Request**: Invalid parameters or service errors
- **404 Not Found**: Job not found
- **410 Gone**: Deprecated Excel import endpoints
- **500 Internal Server Error**: Unexpected errors with comprehensive logging
- Proper error propagation from service layer to API responses

## Related Views
- Job costing views for quote data integration
- CostSet management for quote storage
- Google Sheets service for external data synchronization
- Quote submission views for customer-facing quote presentation