# Client Views Documentation

## Business Purpose
Provides comprehensive client management functionality for jobbing shop operations. Handles client CRUD operations, contact management, search capabilities, and Xero integration for bidirectional client synchronization. Essential for maintaining customer relationships throughout the quote → job → invoice workflow.

## Views

### get_client_contact_persons
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view
**URL**: `/client/api/contacts/<uuid:client_id>/`

#### What it does
- Retrieves contact persons for specific clients from model fields
- Provides structured contact data including primary and secondary contacts
- Eliminates duplicate contact entries
- Supports client communication and job assignment workflows

#### Parameters
- `client_id`: UUID of client to fetch contacts for (path parameter)

#### Returns
- **200 OK**: JSON array of contact persons with names and emails
- **404 Not Found**: Client not found
- **500 Internal Server Error**: Contact retrieval failures

#### Integration
- Client model primary and secondary contact fields
- Duplicate contact elimination logic
- Comprehensive logging for debugging

### get_client_phones
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view
**URL**: `/client/api/phones/<uuid:client_id>/`

#### What it does
- Extracts phone numbers from client records
- Provides structured phone data for communication
- Handles multiple phone number formats and sources
- Supports client contact and communication workflows

#### Parameters
- `client_id`: UUID of client to fetch phone numbers for (path parameter)

#### Returns
- **200 OK**: JSON array of phone numbers with types and labels
- **404 Not Found**: Client not found
- **500 Internal Server Error**: Phone data retrieval failures

#### Integration
- Client model phone fields and structured data
- Phone number parsing and formatting
- Communication system integration

### get_all_clients_api
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view
**URL**: `/client/api/all/`

#### What it does
- Retrieves all clients for dropdown and selection interfaces
- Supports archived client inclusion with optional parameter
- Provides minimal client data for performance optimization
- Orders clients alphabetically for consistent presentation

#### Parameters
- `include_archived`: Optional query parameter to include archived clients (boolean)

#### Returns
- **200 OK**: JSON array of clients with ID, name, and Xero contact ID
- **500 Internal Server Error**: Client retrieval failures

#### Integration
- Client model filtering and ordering
- Xero integration status tracking
- Archive status management

### ClientListView
**File**: `apps/client/views/client_views.py`
**Type**: Class-based view (SingleTableView)
**URL**: `/client/list/`

#### What it does
- Displays paginated table of all clients in the system
- Provides main client management interface
- Supports sorting and basic filtering
- Integrates with table rendering framework

#### Parameters
- Standard pagination parameters

#### Returns
- **200 OK**: Client list template with table data

#### Integration
- SingleTableView for table rendering
- Client model for data source
- Template-based interface

### ClientUpdateView
**File**: `apps/client/views/client_views.py`
**Type**: Class-based view (UpdateView)
**URL**: `/client/update/<uuid:pk>/`

#### What it does
- Provides client editing interface with form validation
- Handles client updates with Xero synchronization
- Manages form processing and error handling
- Supports client data modification workflows

#### Parameters
- `pk`: Client UUID to update (path parameter)
- Form data for client updates

#### Returns
- **200 OK**: Update form template or success redirect
- **302 Redirect**: To authentication if Xero token required

#### Integration
- ClientForm for validation and processing
- Xero synchronization on successful updates
- Form validation and error handling

### ClientSearch
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view
**URL**: `/client/api/search/`

#### What it does
- Performs intelligent client search with multiple criteria
- Supports name-based search with filtering
- Returns structured search results for UI components
- Implements search term validation and processing

#### Parameters
- `q`: Search query string (query parameter, minimum 3 characters)

#### Returns
- **200 OK**: JSON search results with client details
- Empty results for queries under minimum length

#### Integration
- Q object filtering for database searches
- Search term validation and processing
- Result formatting for UI consumption

### client_detail
**File**: `apps/client/views/client_views.py`
**Type**: Function-based template view
**URL**: `/client/detail/<uuid:client_id>/`

#### What it does
- Displays detailed client information and related data
- Shows client jobs, contacts, and financial history
- Provides comprehensive client overview interface
- Supports client relationship management

#### Parameters
- `client_id`: UUID of client to display (path parameter)

#### Returns
- **200 OK**: Client detail template with comprehensive data
- **404 Not Found**: Client not found

#### Integration
- Client model with related data loading
- Job history and financial data
- Contact relationship display

### all_clients
**File**: `apps/client/views/client_views.py`
**Type**: Function-based template view
**URL**: `/client/all/`

#### What it does
- Renders comprehensive client list interface
- Provides client management dashboard
- Supports client navigation and overview
- Integrates with client management workflows

#### Parameters
- No parameters required

#### Returns
- **200 OK**: All clients template with navigation

#### Integration
- Template-based client overview
- Client management interface foundation

### AddClient
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view (POST only)
**URL**: `/client/api/add/`

#### What it does
- Creates new clients with comprehensive validation
- Handles Xero integration for client creation
- Manages client data validation and processing
- Supports client relationship establishment

#### Parameters
- JSON body with client creation data:
  - `name`: Client name (required)
  - `email`: Client email (optional)
  - `phone`: Client phone (optional)
  - Additional client fields

#### Returns
- **200 OK**: JSON with created client data and success confirmation
- **400 Bad Request**: Validation errors or Xero creation failures
- **500 Internal Server Error**: Client creation failures

#### Integration
- ClientForm for validation and processing
- Xero client creation and synchronization
- Error handling and user feedback

### get_client_contacts_api
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view
**URL**: `/client/api/<uuid:client_id>/contacts/`

#### What it does
- Retrieves structured contact data for specific clients
- Returns contact relationships and details
- Supports contact management workflows
- Provides comprehensive contact information

#### Parameters
- `client_id`: UUID of client to fetch contacts for (path parameter)

#### Returns
- **200 OK**: JSON array of client contacts with complete details
- **404 Not Found**: Client not found
- **500 Internal Server Error**: Contact retrieval failures

#### Integration
- ClientContact model for structured contact data
- Contact relationship management
- Comprehensive contact information display

### create_client_contact_api
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view (POST only)
**URL**: `/client/api/contacts/create/`

#### What it does
- Creates new client contacts with validation
- Handles contact relationship establishment
- Manages contact data processing and storage
- Supports client communication workflows

#### Parameters
- JSON body with contact creation data:
  - `client_id`: Client UUID (required)
  - `name`: Contact name (required)
  - `email`: Contact email (optional)
  - `phone`: Contact phone (optional)
  - Additional contact fields

#### Returns
- **201 Created**: JSON with created contact data
- **400 Bad Request**: Validation errors or missing required fields
- **404 Not Found**: Client not found
- **500 Internal Server Error**: Contact creation failures

#### Integration
- ClientContact model for contact storage
- Client relationship validation
- Contact data validation and processing

### client_contact_detail_api
**File**: `apps/client/views/client_views.py`
**Type**: Function-based API view
**URL**: `/client/api/contacts/<uuid:contact_id>/`

#### What it does
- Retrieves detailed information for specific client contacts
- Provides contact editing and management support
- Returns comprehensive contact data
- Supports contact relationship workflows

#### Parameters
- `contact_id`: UUID of contact to retrieve (path parameter)

#### Returns
- **200 OK**: JSON with detailed contact information
- **404 Not Found**: Contact not found
- **500 Internal Server Error**: Contact retrieval failures

#### Integration
- ClientContact model for contact data
- Contact serialization for API responses
- Contact relationship management

## Error Handling
- **400 Bad Request**: Validation errors, missing required fields, or Xero integration failures
- **401 Unauthorized**: Authentication required for protected operations
- **404 Not Found**: Client or contact resources not found
- **500 Internal Server Error**: Database errors, Xero API failures, or unexpected system errors
- Comprehensive logging for debugging and monitoring
- User-friendly error messages and feedback

## Integration Points
- **Xero Integration**: Bidirectional client synchronization with accounting system
- **Job Management**: Client-job relationship establishment and tracking
- **Contact Management**: Structured contact relationships and communication
- **Form Validation**: ClientForm for data validation and processing
- **Search System**: Intelligent client discovery and filtering

## Business Rules
- Client names must be unique within the system
- Xero synchronization maintains data consistency
- Contact relationships require valid client associations
- Search queries require minimum character length for performance
- Archive status affects client visibility and availability

## Performance Considerations
- Search query optimization with minimum length requirements
- Efficient database queries with proper indexing
- Xero API rate limiting and error handling
- Contact data caching for frequent access
- Pagination support for large client datasets

## Security Considerations
- Authentication required for all client operations
- Input validation and sanitization
- Xero API secure authentication and token management
- Access control for client data modification
- Audit logging for client changes and access

## Related Views
- Client REST views for modern API interface
- Job management views for client-job relationships
- Xero views for accounting integration
- Contact management for communication workflows