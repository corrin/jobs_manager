# Stock View Documentation

## Business Purpose
Provides comprehensive interface and API for inventory management in jobbing shop operations. Handles stock creation, consumption tracking, search functionality, and soft deletion for material inventory control. Critical for managing raw materials, tracking usage across jobs, and maintaining accurate costing throughout the quote → job → invoice workflow.

## Views

### use_stock_view
**File**: `apps/purchasing/views/stock.py`
**Type**: Function-based view with authentication
**URL**: `/purchasing/use-stock/` and `/purchasing/use-stock/<uuid:job_id>/`

#### What it does
- Displays comprehensive stock management interface with AG Grid
- Lists all available stock items with calculated markup pricing
- Provides job selection for stock consumption workflows
- Supports pre-selection of jobs via URL parameter or query string

#### Parameters
- `job_id`: Optional job UUID for pre-selection (path or query parameter)

#### Returns
- Stock management template with:
  - Active stock items with quantity and pricing
  - Available jobs list (excluding stock holding job)
  - Calculated unit revenue with materials markup
  - JSON data for AG Grid interface

#### Integration
- Uses Stock.get_stock_holding_job() for inventory organization
- Applies CompanyDefaults materials markup for pricing
- Integrates with get_active_jobs() for job selection

### consume_stock_api_view
**File**: `apps/purchasing/views/stock.py`
**Type**: Function-based API view with transaction support
**URL**: `/purchasing/api/stock/consume/`

#### What it does
- Consumes stock items for specific jobs with validation
- Updates inventory quantities and creates job material entries
- Maintains audit trail for stock consumption tracking
- Enforces business rules for stock availability

#### Parameters
- JSON body with consumption data:
  - `job_id`: UUID of job consuming stock (required)
  - `stock_item_id`: UUID of stock item (required)
  - `quantity_used`: Decimal quantity to consume (required, positive)

#### Returns
- **200 OK**: Success confirmation for stock consumption
- **400 Bad Request**: Validation errors, insufficient stock, or invalid data
- **404 Not Found**: Job or stock item not found
- **500 Internal Server Error**: Unexpected consumption failures

#### Integration
- Uses consume_stock service for business logic
- Database transactions for data integrity
- Comprehensive validation for quantity and availability

### create_stock_api_view
**File**: `apps/purchasing/views/stock.py`
**Type**: Function-based API view with transaction support
**URL**: `/purchasing/api/stock/create/`

#### What it does
- Creates new stock items with comprehensive material information
- Associates stock with stock holding job for organization
- Calculates pricing with company markup for revenue tracking
- Supports detailed material specifications and location tracking

#### Parameters
- JSON body with stock item data:
  - `description`: Stock description (required)
  - `quantity`: Initial quantity (required, positive decimal)
  - `unit_cost`: Cost per unit (required, positive decimal)
  - `source`: Source of stock (required)
  - `notes`: Additional notes (optional)
  - `metal_type`: Material type (optional)
  - `alloy`: Alloy specification (optional)
  - `specifics`: Detailed specifications (optional)
  - `location`: Storage location (optional)

#### Returns
- **201 Created**: Created stock item with calculated pricing data
- **400 Bad Request**: Validation errors or invalid numeric values
- **500 Internal Server Error**: Stock creation failures

#### Integration
- Links to stock holding job for inventory organization
- Applies materials markup from CompanyDefaults
- Returns comprehensive stock data for immediate use

### search_available_stock_api
**File**: `apps/purchasing/views/stock.py`
**Type**: Function-based API view
**URL**: `/purchasing/api/stock/search/`

#### What it does
- Provides autocomplete search for available stock items
- Filters active stock by description with configurable limits
- Returns structured data for dropdown and selection interfaces
- Optimized for real-time search and selection workflows

#### Parameters
- `q`: Search query string (query parameter)
- `limit`: Maximum results (query parameter, default 25)

#### Returns
- **200 OK**: Search results with stock details and availability
- Empty results for missing or short queries

#### Integration
- Filters by is_active=True for available inventory
- Includes job information for context
- Structured response format for UI components

### deactivate_stock_api_view
**File**: `apps/purchasing/views/stock.py`
**Type**: Function-based API view with transaction support
**URL**: `/purchasing/api/stock/<uuid:stock_id>/deactivate/`

#### What it does
- Performs soft deletion of stock items by setting is_active=False
- Maintains inventory history while removing from active use
- Preserves referential integrity and audit trails
- Provides safe inventory management without data loss

#### Parameters
- `stock_id`: UUID of stock item to deactivate (path parameter)

#### Returns
- **200 OK**: Successful deactivation confirmation
- **404 Not Found**: Stock item not found
- **500 Internal Server Error**: Deactivation failures

#### Integration
- Soft delete pattern preserves data integrity
- Updates only is_active field for efficiency
- Maintains full audit trail for inventory tracking

## Error Handling
- **400 Bad Request**: Validation errors, invalid quantities, insufficient stock, or malformed JSON
- **404 Not Found**: Stock items or jobs not found
- **500 Internal Server Error**: Database errors, transaction failures, or unexpected system errors
- Comprehensive input validation for numeric values and required fields
- Transaction rollback for data integrity preservation
- Detailed logging for debugging and audit purposes

## Related Views
- Job management views for stock consumption tracking
- Purchase order views for stock procurement
- Material entry views for job costing integration
- Delivery receipt views for stock receiving workflow
- Company defaults views for markup configuration
