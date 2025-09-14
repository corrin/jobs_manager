# Quoting View Documentation

## Business Purpose

Provides comprehensive interface and API for supplier pricing management and quote generation in jobbing shop operations. Handles AI-powered price list extraction, supplier product management, and MCP (Model Context Protocol) API integration for intelligent quoting workflows. Essential for accurate pricing estimation and supplier comparison throughout the quote → job → invoice workflow.

## Views

### index

**File**: `apps/quoting/views.py`
**Type**: Function-based view with authentication
**URL**: `/quoting/`

#### What it does

- Serves main quoting module landing page
- Provides navigation hub for pricing and supplier management
- Entry point for quoting workflow interfaces

#### Parameters

- No parameters required

#### Returns

- Quoting index template for module navigation

#### Integration

- Requires user authentication
- Foundation for quoting module functionality

### UploadSupplierPricingView

**File**: `apps/quoting/views.py`
**Type**: Class-based view (TemplateView)
**URL**: `/quoting/upload-supplier-pricing/`

#### What it does

- **GET**: Displays interface for uploading supplier price list PDFs
- **POST**: Processes uploaded PDF files using AI extraction for price data
- Creates comprehensive supplier product databases with validation
- Integrates with AI providers for intelligent document processing

#### Parameters

- **GET**: No parameters required
- **POST**: `pdf_file` (multipart form data) - Supplier price list PDF

#### Returns

- **GET**: Upload interface with existing price list history
- **POST**: Success/error messages with processing results and redirect

#### Integration

- Uses extract_price_data service for AI-powered PDF processing
- Creates SupplierPriceList and SupplierProduct records
- Validates supplier existence before processing
- Atomic database transactions for data integrity
- LLM integration for product mapping and categorization

### UploadPriceListView

**File**: `apps/quoting/views.py`
**Type**: Class-based view (TemplateView)
**URL**: `/quoting/upload-price-list/`

#### What it does

- Provides template-only interface for price list uploads
- Currently displays upload form but has no POST processing logic
- Appears to be placeholder for future price list upload functionality

#### Parameters

- No parameters required

#### Returns

- Price list upload template with title context only

#### Integration

- Requires user authentication
- Template-only view with no backend processing implementation

### extract_supplier_price_list_data_view

**File**: `apps/quoting/views.py`
**Type**: Function-based API view
**URL**: `/quoting/api/extract-supplier-price-list/`

#### What it does

- API endpoint for extracting price data from uploaded files
- Uses AI/Gemini integration for intelligent document parsing
- Returns structured price data without database persistence
- Supports real-time price extraction and validation

#### Parameters

- `price_list_file`: Uploaded price list file (multipart form data)

#### Returns

- **200 OK**: Extracted price data in structured JSON format
- **400 Bad Request**: Missing file or extraction errors
- **500 Internal Server Error**: AI processing or parsing failures

#### Integration

- extract_price_data service for AI-powered document processing
- Temporary file handling for security and cleanup
- Structured data format for client-side processing

### search_stock_api

**File**: `apps/quoting/views.py`
**Type**: Function-based MCP API view
**URL**: `/quoting/api/mcp/search_stock/`

#### What it does

- MCP API endpoint for searching internal stock inventory
- Provides intelligent material search with filtering capabilities
- Calculates retail pricing with markup for accurate quotes
- Supports integration with external quoting systems

#### Parameters

- `description`: Material description search term (query parameter)
- `metal_type`: Filter by metal type (optional)
- `alloy`: Filter by alloy specification (optional)
- `min_quantity`: Minimum quantity required (optional)
- `limit`: Maximum results (default 20)

#### Returns

- **200 OK**: Stock items with pricing and availability data
- **500 Internal Server Error**: Search or calculation failures

#### Integration

- Requires service API key authentication
- Searches active Stock model records
- Calculates retail pricing using markup rates
- Structured response format for MCP integration

### search_supplier_prices_api

**File**: `apps/quoting/views.py`
**Type**: Function-based MCP API view
**URL**: `/quoting/api/mcp/search_supplier_prices/`

#### What it does

- MCP API endpoint for comprehensive supplier pricing search
- Searches across multiple suppliers with intelligent filtering
- Optionally includes internal stock as supplier option
- Provides unified pricing interface for quote generation

#### Parameters

- `description`: Material description search term (query parameter)
- `metal_type`: Filter by metal type (optional)
- `alloy`: Filter by alloy specification (optional)
- `suppliers`: Comma-separated supplier names (optional)
- `include_internal_stock`: Include internal stock as supplier (optional)
- `limit`: Maximum results (default 20)

#### Returns

- **200 OK**: Supplier prices with availability and specifications
- **500 Internal Server Error**: Search or processing failures

#### Integration

- Requires service API key authentication
- Searches SupplierProduct records with supplier relationships
- Combines external supplier data with internal stock
- Unified pricing format for quote comparison

### job_context_api

**File**: `apps/quoting/views.py`
**Type**: Function-based MCP API view
**URL**: `/quoting/api/mcp/job_context/<uuid:job_id>/`

#### What it does

- MCP API endpoint for fetching comprehensive job context
- Provides job details, existing materials, and client history
- Initializes intelligent quoting sessions with relevant context
- Supports "Interactive Quote" functionality integration

#### Parameters

- `job_id`: UUID of job for context retrieval (path parameter)

#### Returns

- **200 OK**: Complete job context with materials and client history
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Context retrieval failures

#### Integration

- Requires service API key authentication
- Retrieves job with client and contact relationships
- Includes existing materials from latest quote cost set
- Provides client history from recent completed jobs
- Structured context for AI-powered quoting assistance

## Error Handling

- **400 Bad Request**: Missing files, validation errors, or invalid parameters
- **401 Unauthorized**: Missing or invalid service API key for MCP endpoints
- **404 Not Found**: Job or resources not found
- **500 Internal Server Error**: AI processing failures, database errors, or unexpected system errors
- Comprehensive input validation and sanitization
- Atomic database transactions for data integrity
- Detailed logging for debugging and monitoring
- Proper file cleanup for security

## Related Views

- Purchase order views for supplier procurement
- Job management views for quoting integration
- Stock management views for inventory pricing
- Client management views for supplier relationships
- AI provider views for document processing configuration
