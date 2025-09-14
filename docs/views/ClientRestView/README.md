# Client REST View Documentation

## Business Purpose

Provides comprehensive REST API for client relationship management in jobbing shop operations. Handles client creation, search, contact management, and Xero integration for bidirectional synchronization. Essential for maintaining customer information and relationships across the quote → job → invoice workflow.

## Views

### BaseClientRestView

**File**: `apps/client/views/client_rest_views.py`
**Type**: Base class for client REST operations
**URL**: N/A (base class)

#### What it does

- Provides common functionality for all client REST views
- Implements centralized error handling and JSON parsing
- Follows clean code principles with single responsibility

#### Integration

- CSRF exempt decorator for API endpoints
- Centralized error logging and response formatting

### ClientListAllRestView

**File**: `apps/client/views/client_rest_views.py`
**Type**: Class-based view extending BaseClientRestView
**URL**: `/clients/rest/all/`

#### What it does

- Lists all clients with minimal data (ID and name only)
- Optimized for dropdown menus and fast client selection
- Provides lightweight client list for UI components

#### Parameters

- No parameters required

#### Returns

- **200 OK**: Array of client objects with ID and name only
- **500 Internal Server Error**: Database errors or unexpected failures

#### Integration

- Uses ClientNameOnlySerializer for optimized response size
- Ordered by client name for consistent UI experience

### ClientSearchRestView

**File**: `apps/client/views/client_rest_views.py`
**Type**: Class-based view extending BaseClientRestView
**URL**: `/clients/rest/search/`

#### What it does

- Searches clients by name with intelligent filtering
- Provides detailed client information including spend analysis
- Implements minimum query length and result limiting for performance

#### Parameters

- `q`: Search query string (minimum 3 characters)

#### Returns

- **200 OK**: Search results with detailed client data
- Empty results for queries under 3 characters or no matches

#### Integration

- Includes Xero contact ID and synchronization status
- Calculates total spend and last invoice date for business insights
- Limited to 10 results for performance optimization

### ClientContactsRestView

**File**: `apps/client/views/client_rest_views.py`
**Type**: Class-based view extending BaseClientRestView
**URL**: `/clients/rest/<uuid:client_id>/contacts/`

#### What it does

- Retrieves all contacts for a specific client
- Provides contact details including primary contact designation
- Supports client relationship management workflows

#### Parameters

- `client_id`: UUID of client to fetch contacts for

#### Returns

- **200 OK**: Array of contact objects with full details
- **400 Bad Request**: Missing client ID
- **404 Not Found**: Client not found

#### Integration

- Ordered by contact name for consistent presentation
- Includes primary contact flag for relationship hierarchy

### ClientContactCreateRestView

**File**: `apps/client/views/client_rest_views.py`
**Type**: Class-based view extending BaseClientRestView
**URL**: `/clients/rest/contacts/`

#### What it does

- Creates new client contacts with validation
- Supports comprehensive contact information management
- Implements business rules for contact creation

#### Parameters

- JSON body with contact data:
  - `client_id`: UUID of parent client (required)
  - `name`: Contact name (required)
  - `email`: Contact email (optional)
  - `phone`: Contact phone (optional)
  - `position`: Job title (optional)
  - `is_primary`: Primary contact flag (optional)
  - `notes`: Additional notes (optional)

#### Returns

- **201 Created**: Created contact with full details
- **400 Bad Request**: Validation errors or missing required fields
- **500 Internal Server Error**: Contact creation failures

#### Integration

- Validates client existence before contact creation
- Enforces required field validation with guard clauses

### ClientCreateRestView

**File**: `apps/client/views/client_rest_views.py`
**Type**: Class-based view extending BaseClientRestView
**URL**: `/clients/rest/create/`

#### What it does

- Creates new clients with Xero-first workflow
- Creates client in Xero accounting system first, then syncs locally
- Prevents duplicate clients and maintains data consistency

#### Parameters

- JSON body with client data:
  - `name`: Client name (required)
  - `email`: Client email (optional)
  - `phone`: Client phone (optional)
  - `address`: Client address (optional)
  - `is_account_customer`: Account customer flag (optional)

#### Returns

- **201 Created**: Created client with full details
- **400 Bad Request**: Form validation errors or invalid data
- **401 Unauthorized**: Xero authentication required
- **409 Conflict**: Client already exists in Xero
- **500 Internal Server Error**: Xero API or sync failures

#### Integration

- Uses Django ClientForm for validation
- Creates contact in Xero first using AccountingApi
- Syncs back to local database using sync_clients service
- Maintains bidirectional Xero synchronization

## Error Handling

- **400 Bad Request**: Invalid parameters, validation errors, or missing required fields
- **401 Unauthorized**: Xero authentication required for client creation
- **404 Not Found**: Client not found for contact operations
- **409 Conflict**: Duplicate client names in Xero
- **500 Internal Server Error**: Database errors, Xero API failures, or unexpected system errors
- Comprehensive logging for debugging and monitoring

## Related Views

- Job management views for client-job relationships
- Xero integration views for accounting synchronization
- Invoice generation views for customer billing
- Contact management for client relationship tracking
