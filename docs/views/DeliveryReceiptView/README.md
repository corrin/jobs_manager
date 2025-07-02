# Delivery Receipt Views Documentation

## Business Purpose
Provides delivery receipt functionality for purchase order receiving in jobbing shop operations. Handles receipt of ordered materials, allocation to jobs or stock, and inventory management. Essential for tracking material deliveries, updating purchase order status, and maintaining accurate inventory records throughout the procurement workflow.

## Views

### DeliveryReceiptListView
**File**: `apps/purchasing/views/delivery_receipt.py`
**Type**: Class-based view (ListView)
**URL**: `/purchasing/delivery-receipts/`

#### What it does
- Displays list of purchase orders available for receiving
- Shows purchase orders in submitted or partially received status
- Provides navigation to delivery receipt creation interface
- Enables tracking of pending deliveries and receipt status
- Supports purchase order management workflow

#### Parameters
- Standard pagination parameters

#### Returns
- **200 OK**: Delivery receipt list template with purchase orders
- **401 Unauthorized**: Login required for access

#### Integration
- PurchaseOrder model for status filtering
- LoginRequiredMixin for authentication
- Template-based interface for receipt management
- Order filtering by receipt-eligible status

### DeliveryReceiptCreateView
**File**: `apps/purchasing/views/delivery_receipt.py`
**Type**: Class-based view (TemplateView)
**URL**: `/purchasing/delivery-receipts/<uuid:pk>/`

#### What it does
- Provides interface for creating delivery receipts for specific purchase orders
- Handles material allocation to jobs or general stock
- Manages quantity reconciliation and job assignment
- Supports metadata tracking for stock items
- Enables complete or partial receipt processing

#### Parameters
- `pk`: Purchase order UUID for receipt creation (path parameter)

#### Returns
- **200 OK**: Delivery receipt form template with purchase order data
- **400 Bad Request**: Purchase order not eligible for receiving
- **401 Unauthorized**: Login required for access
- **404 Not Found**: Purchase order not found

#### Integration
- PurchaseOrder model for order data
- Job model for allocation options
- Stock holding job integration ("Worker Admin")
- Active jobs list for allocation choices

### post (Receipt Processing Method)
**File**: `apps/purchasing/views/delivery_receipt.py`
**Type**: Method within DeliveryReceiptCreateView

#### What it does
- Processes delivery receipt data with quantity allocations
- Handles allocation to specific jobs or general stock
- Manages metadata for stock items including material specifications
- Updates purchase order status based on receipt completion
- Creates stock records and material entries

#### Parameters
- Form data with receipt information:
  - `received_quantities`: JSON object with line item allocations
    - Per line: total_received, job_allocation, stock_allocation
    - Job assignment and retail rate information
    - Stock metadata (metal_type, alloy, specifics, location)

#### Returns
- **200 OK**: JSON success confirmation for successful receipt processing
- **400 Bad Request**: JSON error response for processing failures

#### Integration
- process_delivery_receipt service for business logic
- Job allocation with quantity tracking
- Stock allocation with metadata preservation
- Purchase order line item processing

## Receipt Processing Features
- **Quantity Allocation**: Split received quantities between jobs and stock
- **Job Assignment**: Direct allocation to specific active jobs
- **Stock Management**: General stock allocation with detailed metadata
- **Retail Rate Tracking**: Markup rates for cost management
- **Metadata Preservation**: Material specifications for stock items
- **Partial Receipts**: Support for incomplete deliveries

## Error Handling
- **400 Bad Request**: Invalid JSON data, processing failures, or business rule violations
- **401 Unauthorized**: Authentication required for all receipt operations
- **404 Not Found**: Purchase order not found
- **500 Internal Server Error**: System failures during receipt processing
- Comprehensive logging for debugging and audit trails
- JSON error responses for API compatibility

## Business Rules
- Only submitted or partially received purchase orders can be processed
- Receipt quantities must not exceed ordered quantities
- Allocations can be split between specific jobs and general stock
- Stock holding job ("Worker Admin") manages general inventory
- All receipt processing creates audit trails
- Material metadata supports inventory tracking

## Integration Points
- **Purchase Order Model**: Order status and line item management
- **Job Model**: Active job allocation and assignment
- **Stock Model**: Inventory creation and metadata tracking
- **Delivery Receipt Service**: Business logic for receipt processing
- **Authentication System**: Login required for all operations

## Allocation Logic
- **Job Allocation**: Direct assignment to specific jobs with quantity tracking
- **Stock Allocation**: General inventory with metadata preservation
- **Dual Allocation**: Single line items can be split between jobs and stock
- **Metadata Tracking**: Material specifications for stock management
- **Retail Rate Management**: Markup tracking for cost control

## Performance Considerations
- Efficient purchase order filtering for receipt eligibility
- Optimized job list retrieval for allocation options
- JSON processing for complex allocation data
- Service layer delegation for business logic
- Database transaction handling for receipt processing

## Security Considerations
- Authentication required for all receipt operations
- Purchase order validation prevents unauthorized access
- Input validation for allocation data
- Error message sanitization to prevent information leakage
- Audit logging for receipt tracking and compliance

## Inventory Integration
- **Stock Creation**: Automatic stock record generation
- **Material Tracking**: Metadata preservation for inventory management
- **Location Management**: Storage location tracking
- **Metal Type Classification**: Material categorization for organization
- **Alloy Specifications**: Detailed material characteristics

## Related Views
- Purchase order views for order management
- Stock views for inventory management
- Job management views for project allocation
- Purchasing REST views for API integration
- Material entry views for job costing