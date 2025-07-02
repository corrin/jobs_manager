# Xero Synchronization Views

## Business Purpose
Manages data synchronization between jobbing shop system and Xero accounting platform. Handles real-time sync monitoring, background task management, and progress tracking for bidirectional data flow.

## Views

### stream_xero_sync
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view (Server-Sent Events)
**URL**: `/workflow/xero/sync/stream/`

#### What it does
- Provides real-time Server-Sent Events stream for sync progress
- Streams live updates from background sync tasks
- Handles authentication validation before streaming
- Manages sync completion and error events

#### Parameters
- No parameters required

#### Returns
- **200 OK**: SSE stream with JSON-formatted sync events
- **401 Unauthorized**: Invalid Xero token with redirect instructions

#### Integration
- Uses generate_xero_sync_events() for event generation
- XeroSyncService for task management and message polling
- Cache-based sync lock management
- Comprehensive error handling with graceful stream termination

### xero_sync_progress_page
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view
**URL**: `/workflow/xero/sync/progress/`

#### What it does
- Displays sync progress page with real-time updates
- Provides user interface for monitoring sync operations
- Validates authentication before showing progress interface

#### Parameters
- No parameters required

#### Returns
- **200 OK**: Sync progress template with XERO_ENTITIES context
- **302 Redirect**: To authentication if token invalid

#### Integration
- Template-based interface for sync monitoring
- XERO_ENTITIES configuration for entity tracking
- Authentication validation with fallback redirects

### get_xero_sync_info
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/sync/info/`

#### What it does
- Provides current sync status and last sync timestamps
- Returns comprehensive sync information for all Xero entities
- Includes sync lock status for progress indication

#### Parameters
- No parameters required

#### Returns
- **200 OK**: JSON with last sync times and current sync status
- **401 Unauthorized**: Invalid Xero token with authentication redirect flag
- **500 Internal Server Error**: Sync info retrieval failures

#### Integration
- Queries last sync times across all entity types (accounts, contacts, invoices, etc.)
- Cache-based sync lock status checking
- Comprehensive entity coverage including Stock/Items

### start_xero_sync
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/sync/start/`

#### What it does
- Initiates background Xero sync task
- Validates authentication before starting sync
- Returns task ID for progress tracking

#### Parameters
- No parameters required

#### Returns
- **200 OK**: JSON with task ID and sync status
- **401 Unauthorized**: Invalid Xero token
- **500 Internal Server Error**: Sync initiation failures

#### Integration
- XeroSyncService.start_sync() for task management
- Background task coordination with scheduler
- Task ID generation for progress tracking

### trigger_xero_sync
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view (POST only) with CSRF exemption
**URL**: `/workflow/xero/sync/trigger/`

#### What it does
- Manual "Sync Now" endpoint for user-initiated sync
- Ensures authentication before triggering sync
- Returns task information for frontend SSE connection

#### Parameters
- No parameters required (POST endpoint)

#### Returns
- **200 OK**: JSON with task ID and start status
- **400 Bad Request**: Unable to start sync
- **401 Unauthorized**: Authentication required

#### Integration
- ensure_xero_authentication() for auth validation
- XeroSyncService integration for task management
- Frontend coordination for SSE stream connection

### refresh_xero_data
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/refresh/`

#### What it does
- Legacy endpoint for refreshing Xero data
- Validates authentication and redirects to sync progress
- Handles authentication errors gracefully

#### Parameters
- No parameters required

#### Returns
- **302 Redirect**: To sync progress or authentication
- **200 OK**: Error template for non-auth failures

#### Integration
- get_valid_token() for authentication validation
- Redirect-based flow to sync progress interface
- Error handling with template fallbacks

## Error Handling
- **401 Unauthorized**: Invalid or missing Xero tokens with authentication redirects
- **400 Bad Request**: Sync initiation failures or invalid requests
- **500 Internal Server Error**: Background task failures or system errors
- Comprehensive logging for sync operation debugging
- Graceful SSE stream termination on errors

## Integration Points
- XeroSyncService for background task coordination
- Cache-based sync lock management
- Authentication token validation across all endpoints
- Real-time progress reporting through SSE streams