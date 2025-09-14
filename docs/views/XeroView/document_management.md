# Xero Document Management Views

## Business Purpose

Handles creation and deletion of financial documents in Xero accounting system. Manages invoices, purchase orders, and quotes with bidirectional synchronization between jobbing shop workflow and Xero accounting records.

## Views

### create_xero_invoice

**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/invoice/create/<uuid:job_id>/`

#### What it does

- Creates invoices in Xero for completed jobs
- Links job data with Xero invoice records
- Handles client and job validation before creation
- Provides feedback on creation success/failure

#### Parameters

- `job_id`: UUID of job to create invoice for (path parameter)

#### Returns

- **200 OK**: JSON success response with creation confirmation
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Invoice creation failures

#### Integration

- XeroInvoiceManager for invoice creation logic
- Job model validation and client relationship
- \_handle_creator_response() for consistent response handling
- Message framework integration for user feedback

### create_xero_purchase_order

**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/purchase-order/create/<uuid:purchase_order_id>/`

#### What it does

- Creates purchase orders in Xero for supplier procurement
- Syncs purchase order data with Xero accounting records
- Handles supplier validation and line item processing
- Returns detailed sync status and Xero URLs

#### Parameters

- `purchase_order_id`: UUID of purchase order to sync (path parameter)

#### Returns

- **200 OK**: JSON with sync status and Xero details
- **404 Not Found**: Purchase order not found
- **500 Internal Server Error**: Sync failures with detailed error information

#### Integration

- XeroPurchaseOrderManager for complex sync logic
- PurchaseOrder model validation
- Comprehensive error handling with exception type reporting
- Direct manager response without additional processing

### create_xero_quote

**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/quote/create/<uuid:job_id>/`

#### What it does

- Creates quotes in Xero from job pricing information
- Links job estimates with Xero quote records
- Handles quote approval workflow integration
- Manages quote-to-invoice conversion tracking

#### Parameters

- `job_id`: UUID of job to create quote for (path parameter)

#### Returns

- **200 OK**: JSON success response with quote creation details
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Quote creation failures

#### Integration

- XeroQuoteManager for quote creation and management
- Job model validation and pricing relationship
- \_handle_creator_response() for standardized response processing
- Client validation through job relationships

### delete_xero_invoice

**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/invoice/delete/<uuid:job_id>/`

#### What it does

- Deletes invoices from Xero accounting system
- Maintains local records while removing Xero references
- Handles deletion validation and error reporting
- Provides confirmation of successful deletion

#### Parameters

- `job_id`: UUID of job whose invoice to delete (path parameter)

#### Returns

- **200 OK**: JSON success response with deletion confirmation
- **404 Not Found**: Job or invoice not found
- **500 Internal Server Error**: Deletion failures

#### Integration

- XeroInvoiceManager for deletion logic
- Job model validation and invoice relationship
- \_handle_creator_response() for consistent response handling
- Soft deletion approach preserving local data

### delete_xero_quote

**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/quote/delete/<uuid:job_id>/`

#### What it does

- Removes quotes from Xero accounting system
- Maintains job pricing while clearing Xero references
- Supports quote revision and re-creation workflows
- Handles deletion error scenarios gracefully

#### Parameters

- `job_id`: UUID of job whose quote to delete (path parameter)

#### Returns

- **200 OK**: JSON success response with deletion status
- **404 Not Found**: Job or quote not found
- **500 Internal Server Error**: Deletion processing failures

#### Integration

- XeroQuoteManager for quote deletion operations
- Job model validation and quote relationship
- \_handle_creator_response() for standardized response handling
- Quote workflow state management

### delete_xero_purchase_order

**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/purchase-order/delete/<uuid:purchase_order_id>/`

#### What it does

- Deletes purchase orders from Xero accounting system
- Preserves local purchase order records
- Handles supplier relationship cleanup
- Manages purchase order workflow state transitions

#### Parameters

- `purchase_order_id`: UUID of purchase order to delete (path parameter)

#### Returns

- **200 OK**: JSON success response with deletion confirmation
- **404 Not Found**: Purchase order not found
- **500 Internal Server Error**: Deletion operation failures

#### Integration

- XeroPurchaseOrderManager for deletion processing
- PurchaseOrder model validation
- \_handle_creator_response() for response standardization
- Supplier relationship preservation

### xero_disconnect

**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/disconnect/`

#### What it does

- Disconnects Xero integration and clears authentication
- Removes stored tokens and tenant connections
- Provides clean disconnection workflow
- Handles post-disconnection redirects

#### Parameters

- No parameters required

#### Returns

- **302 Redirect**: To appropriate post-disconnection page
- **200 OK**: Disconnection confirmation template

#### Integration

- Token cleanup and session management
- XeroToken model manipulation
- Authentication state reset
- User feedback and navigation handling

## Helper Functions

### \_handle_creator_response

**Purpose**: Standardizes response handling for document creation operations
**Integration**: Used by create/delete operations for consistent messaging and error handling

## Error Handling

- **400 Bad Request**: Invalid document data or business rule violations
- **401 Unauthorized**: Xero authentication required
- **404 Not Found**: Jobs, purchase orders, or related records not found
- **500 Internal Server Error**: Xero API failures, network issues, or system errors
- Comprehensive logging with exception details and context
- User-friendly error messages through Django messages framework

## Business Rules

- Authentication validation before all document operations
- Job and purchase order existence validation
- Client/supplier relationship requirements
- Xero tenant connection validation
- Document state consistency between systems
