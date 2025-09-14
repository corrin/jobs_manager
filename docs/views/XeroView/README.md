# Xero Integration Views Documentation

## Business Purpose

Provides comprehensive Xero accounting system integration for jobbing shop operations. Handles OAuth2 authentication, bidirectional data synchronization, financial document management (invoices, purchase orders, quotes), and real-time monitoring. Critical for seamless accounting integration throughout the quote → job → invoice workflow.

## Architecture Overview

The Xero integration is organized into five main functional areas:

### 1. Authentication System

**File**: [authentication.md](./authentication.md)

Handles secure OAuth2 authentication flow with Xero accounting platform:

- `xero_authenticate` - Initiates OAuth flow with state validation
- `xero_oauth_callback` - Processes OAuth callback and token exchange
- `refresh_xero_token` - Manages token refresh and expiration
- `success_xero_connection` - Confirms successful authentication

### 2. Data Synchronization

**File**: [synchronization.md](./synchronization.md)

Manages real-time and background data sync between systems:

- `stream_xero_sync` - Server-Sent Events for real-time sync progress
- `start_xero_sync` - Initiates background sync tasks
- `trigger_xero_sync` - Manual sync triggering
- `get_xero_sync_info` - Sync status and entity timestamps
- `xero_sync_progress_page` - User interface for sync monitoring

### 3. Document Management

**File**: [document_management.md](./document_management.md)

Creates and manages financial documents in Xero:

- `create_xero_invoice` - Job-to-invoice conversion
- `create_xero_purchase_order` - Supplier purchase order sync
- `create_xero_quote` - Job estimate to Xero quote
- `delete_xero_invoice` - Invoice removal with local preservation
- `delete_xero_quote` - Quote deletion and workflow management
- `delete_xero_purchase_order` - Purchase order cleanup
- `xero_disconnect` - Complete integration disconnection

### 4. REST API Endpoints

**File**: [api_views.md](./api_views.md)

Provides API access to Xero error tracking and monitoring:

- `XeroErrorListAPIView` - Paginated error history
- `XeroErrorDetailAPIView` - Detailed error information

### 5. Utility Functions

**File**: [utilities.md](./utilities.md)

Supporting views for health checking and user interface:

- `xero_ping` - Connection status health check
- `XeroIndexView` - Main dashboard interface
- Helper functions for authentication validation
- Template views for user experience

## Key Features

### OAuth2 Security

- Secure state validation prevents CSRF attacks
- Token refresh automation
- Session management for multi-step authentication
- Frontend/backend redirect coordination

### Real-Time Synchronization

- Server-Sent Events for live progress updates
- Background task coordination
- Entity-specific sync tracking
- Cache-based sync lock management

### Document Lifecycle Management

- Job-to-invoice workflow integration
- Purchase order supplier coordination
- Quote approval and conversion tracking
- Soft deletion with local data preservation

### Error Tracking & Monitoring

- Comprehensive error logging
- API-based error access
- Debugging support with stack traces
- Integration health monitoring

### Business Integration

- Bidirectional data flow with Xero
- Job workflow state management
- Client/supplier relationship sync
- Financial document coordination

## Integration Points

### Core System Dependencies

- **Job Management**: Job-to-invoice/quote conversion
- **Purchase Orders**: Supplier procurement sync
- **Client Management**: Contact synchronization
- **Authentication**: OAuth token management

### External Dependencies

- **Xero API**: Accounting platform integration
- **Background Tasks**: APScheduler coordination
- **Cache System**: Redis for sync coordination
- **Frontend**: Vue.js dashboard integration

## Error Handling Strategy

All Xero views implement comprehensive error handling:

- **401 Unauthorized**: Authentication failures with redirect guidance
- **404 Not Found**: Resource validation with user feedback
- **500 Internal Server Error**: System failures with detailed logging
- **Network Errors**: Graceful degradation and retry mechanisms

## Development Guidelines

### Authentication First

All Xero operations require valid authentication. Use `ensure_xero_authentication()` for consistent validation.

### Error Response Consistency

Use `_handle_creator_response()` for standardized document operation responses.

### Real-Time Updates

Implement Server-Sent Events for operations requiring progress feedback.

### Data Integrity

Maintain bidirectional sync while preserving local data on Xero failures.

## Related Documentation

- [Xero API Integration Guide](../../integration/xero_api.md)
- [Job Management Views](../JobManagementView/)
- [Purchase Order Views](../PurchaseOrderView/)
- [Authentication System](../AuthenticationView/)
