# Purchase Order View Documentation

## Business Purpose

Provides comprehensive web interface and API for purchase order lifecycle management in jobbing shop operations. Handles creation, editing, approval, and supplier communication for material procurement. Integrates with Xero accounting system and supports AI-powered quote processing for efficient purchasing workflow throughout the quote → job → invoice cycle.

## Views

### PurchaseOrderListView

**File**: `apps/purchasing/views/purchase_order.py`
**Type**: Class-based view (ListView)
**URL**: `/purchasing/purchase-orders/`

#### What it does

- Lists all purchase orders in descending PO number order
- Provides overview of purchase order status and details
- Serves as main navigation hub for purchase order management

#### Parameters

- No parameters required

#### Returns

- Purchase orders list template with context data
- Orders sorted by PO number (newest first)

#### Integration

- Uses standard Django ListView pattern
- Requires user authentication
- Provides foundation for purchase order navigation

### PurchaseOrderCreateView

**File**: `apps/purchasing/views/purchase_order.py`
**Type**: Class-based view (TemplateView)
**URL**: `/purchasing/purchase-orders/new/` and `/purchasing/purchase-orders/<uuid:pk>/`

#### What it does

- **GET**: Creates new purchase orders or loads existing ones for editing
- **POST**: Processes form submission for purchase order creation
- Automatically generates unique PO numbers for new orders
- Provides comprehensive purchase order editing interface

#### Parameters

- `pk`: Purchase order UUID for editing (optional path parameter)
- **POST**: Form data with purchase order and line item information

#### Returns

- Purchase order form template with job data, line items, and Xero integration status
- JSON response for AJAX form submissions
- Redirects to detail view after successful creation

#### Integration

- Immediate PO number reservation for new orders
- Comprehensive context data including jobs, line items, and Xero details
- Supports real-time editing and autosave functionality

### autosave_purchase_order_view

**File**: `apps/purchasing/views/purchase_order.py`
**Type**: Function-based view with transaction support
**URL**: `/purchasing/api/purchase-orders/autosave/`

#### What it does

- Provides real-time autosave functionality for purchase order editing
- Manages purchase order header and line item synchronization
- Automatically syncs completed purchase orders to Xero accounting system
- Handles line item deletion and creation with referential integrity

#### Parameters

- JSON body with complete purchase order data:
  - `purchase_order`: Header information (supplier, dates, status, reference)
  - `line_items`: Array of line item data with job assignments

#### Returns

- **200 OK**: Success confirmation with Xero integration status
- **400 Bad Request**: Validation errors or missing required data
- **404 Not Found**: Purchase order not found
- **500 Internal Server Error**: Database or Xero sync failures

#### Integration

- Database transactions for data integrity
- XeroPurchaseOrderManager for accounting synchronization
- Comprehensive logging for debugging and audit trails
- Automatic line item cleanup for deleted items

### delete_purchase_order_view

**File**: `apps/purchasing/views/purchase_order.py`
**Type**: Function-based view
**URL**: `/purchasing/purchase-orders/<uuid:pk>/delete/`

#### What it does

- Deletes purchase orders with business rule validation
- Prevents deletion of purchase orders already sent to suppliers
- Maintains data integrity by restricting deletion to draft status only

#### Parameters

- `pk`: Purchase order UUID to delete (path parameter)

#### Returns

- **200 OK**: Successful deletion confirmation
- **400 Bad Request**: Invalid status or missing PO ID
- **500 Internal Server Error**: Deletion failures

#### Integration

- Business rule enforcement for deletion permissions
- Status validation to prevent improper deletions

### extract_supplier_quote_data_view

**File**: `apps/purchasing/views/purchase_order.py`
**Type**: Function-based view
**URL**: `/purchasing/api/supplier-quotes/extract/`

#### What it does

- Processes uploaded supplier quote files using AI extraction
- Creates purchase orders pre-filled with extracted quote data
- Supports automated data entry from supplier quotes and invoices
- Integrates with AI providers for intelligent document processing

#### Parameters

- `quote_file`: Uploaded quote file (multipart form data)

#### Returns

- **302 Redirect**: To purchase order detail view with extracted data
- **400 Bad Request**: Missing file or extraction errors
- **500 Internal Server Error**: AI processing or file handling failures

#### Integration

- AIProvider integration for document processing
- quote_to_po_service for data extraction and PO creation
- File handling and storage for quote documents

### PurchaseOrderEmailView

**File**: `apps/purchasing/views/purchase_order.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/api/purchase-orders/<uuid:purchase_order_id>/email/`

#### What it does

- Generates email templates and PDF attachments for supplier communication
- Creates mailto links with pre-filled content for purchase order transmission
- Provides PDF generation for purchase order documentation

#### Parameters

- `purchase_order_id`: UUID of purchase order (path parameter)

#### Returns

- **200 OK**: Email data with mailto URL, subject, body, and PDF attachment
- **400 Bad Request**: Validation errors or missing purchase order
- **500 Internal Server Error**: Email or PDF generation failures

#### Integration

- purchase_order_email_service for email template generation
- purchase_order_pdf_service for PDF document creation
- Base64 encoding for PDF attachment handling

### PurchaseOrderPDFView

**File**: `apps/purchasing/views/purchase_order.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/api/purchase-orders/<uuid:purchase_order_id>/pdf/`

#### What it does

- Generates and serves PDF documents for purchase orders
- Supports both inline viewing and download modes
- Provides professional purchase order documentation for suppliers

#### Parameters

- `purchase_order_id`: UUID of purchase order (path parameter)
- `download`: Query parameter for attachment mode (optional)

#### Returns

- **200 OK**: PDF file response with appropriate content disposition
- **404 Not Found**: Purchase order not found
- **500 Internal Server Error**: PDF generation failures

#### Integration

- purchase_order_pdf_service for document generation
- FileResponse for efficient PDF streaming
- Content disposition headers for browser handling

## Error Handling

- **400 Bad Request**: Validation errors, missing required fields, or business rule violations
- **401 Unauthorized**: Authentication required for API endpoints
- **404 Not Found**: Purchase order or related resources not found
- **500 Internal Server Error**: Database errors, Xero API failures, AI processing errors, or PDF generation issues
- Comprehensive logging and error tracking for debugging and monitoring
- Transaction rollback for data integrity preservation

## Related Views

- Job management views for purchase order job assignments
- Xero integration views for accounting synchronization
- Stock management views for inventory tracking
- Delivery receipt views for receiving workflow
- Supplier management views for vendor relationships
