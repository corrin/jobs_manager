# Purchasing REST View Documentation

## Business Purpose
Provides comprehensive REST API for purchasing and inventory management in jobbing shop operations. Handles purchase order lifecycle, stock management, delivery receipt processing, and Xero integration for accounting synchronization. Critical for tracking material costs and inventory consumption across the quote → job → invoice workflow.

## Views

### XeroItemList
**File**: `apps/purchasing/views/purchasing_rest_views.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/rest/xero-items/`

#### What it does
- Retrieves list of items from Xero accounting system
- Provides item data for purchase order creation
- Enables synchronization between internal inventory and Xero items

#### Parameters
- No parameters required

#### Returns
- **200 OK**: List of Xero items with details
- **500 Internal Server Error**: Xero API failures or connection issues

#### Integration
- Uses PurchasingRestService for Xero item retrieval
- Direct Xero API integration for item synchronization

### PurchaseOrderListCreateRestView
**File**: `apps/purchasing/views/purchasing_rest_views.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/rest/purchase-orders/`

#### What it does
- **GET**: Lists purchase orders with optional status filtering
- **POST**: Creates new purchase orders for supplier procurement
- Manages purchase order lifecycle and status tracking

#### Parameters
- **GET**: `status` (query parameter) - Optional filter by PO status
- **POST**: JSON body with purchase order data

#### Returns
- **GET**: List of purchase orders with status information
- **POST**: Created purchase order ID and PO number with 201 status

#### Integration
- Uses PurchasingRestService for business logic delegation
- Creates purchase orders for supplier material procurement

### PurchaseOrderDetailRestView
**File**: `apps/purchasing/views/purchasing_rest_views.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/rest/purchase-orders/<uuid:pk>/`

#### What it does
- **GET**: Retrieves complete purchase order details including lines
- **PATCH**: Updates purchase order status and information
- Provides detailed view of purchase order with line items

#### Parameters
- `pk`: Purchase order UUID (path parameter)
- **PATCH**: JSON body with update data

#### Returns
- **GET**: Complete PO data with lines, supplier info, and Xero integration details
- **PATCH**: Updated purchase order ID and status

#### Integration
- Shows Xero integration status and online URLs
- Includes supplier contact and Xero synchronization information

### DeliveryReceiptRestView
**File**: `apps/purchasing/views/purchasing_rest_views.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/rest/delivery-receipts/`

#### What it does
- Processes delivery receipts for received purchase orders
- Handles allocation of received items to stock or direct job consumption
- Updates purchase order status and creates stock entries

#### Parameters
- `purchase_order_id`: UUID of purchase order receiving delivery
- `allocations`: Object mapping line items to allocation decisions

#### Returns
- **200 OK**: Success confirmation for processed delivery

#### Integration
- Uses delivery_receipt_service for complex allocation logic
- Updates purchase order status and creates stock records

### StockListRestView
**File**: `apps/purchasing/views/purchasing_rest_views.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/rest/stock/`

#### What it does
- **GET**: Lists available stock items for inventory management
- **POST**: Creates new stock entries for inventory tracking
- Manages inventory levels and stock item creation

#### Parameters
- **POST**: JSON body with stock item data

#### Returns
- **GET**: List of stock items with availability information
- **POST**: Created stock item ID with 201 status

#### Integration
- Uses PurchasingRestService for stock management operations
- Tracks inventory for job material consumption

### StockDeactivateRestView
**File**: `apps/purchasing/views/purchasing_rest_views.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/rest/stock/<uuid:stock_id>/`

#### What it does
- Deactivates stock items to remove them from available inventory
- Provides soft delete functionality for stock management
- Maintains inventory history while preventing future consumption

#### Parameters
- `stock_id`: UUID of stock item to deactivate

#### Returns
- **200 OK**: Success confirmation for deactivation
- **400 Bad Request**: Item already inactive

#### Integration
- Updates stock item active status for inventory control

### StockConsumeRestView
**File**: `apps/purchasing/views/purchasing_rest_views.py`
**Type**: Class-based view (APIView)
**URL**: `/purchasing/rest/stock/<uuid:stock_id>/consume/`

#### What it does
- Consumes stock items for specific jobs
- Tracks material usage and updates inventory levels
- Creates material entries for job costing and billing

#### Parameters
- `stock_id`: UUID of stock item to consume
- `job_id`: UUID of job consuming the stock
- `quantity`: Amount to consume from stock

#### Returns
- **200 OK**: Success confirmation for stock consumption
- **400 Bad Request**: Invalid data or insufficient stock

#### Integration
- Uses stock_service for consumption logic and inventory updates
- Creates job material entries for cost tracking

## Error Handling
- **400 Bad Request**: Invalid parameters, insufficient stock, or business rule violations
- **404 Not Found**: Purchase order or stock item not found
- **500 Internal Server Error**: Xero API failures or unexpected system errors
- Comprehensive validation for quantity, job/stock existence, and business constraints

## Related Views
- Job costing views for material cost integration
- Xero views for accounting synchronization
- Delivery receipt views for receiving workflow
- Stock management views for inventory tracking
