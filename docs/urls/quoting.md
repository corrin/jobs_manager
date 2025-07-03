# Quoting URLs Documentation

## API Endpoints

#### Extract-Supplier-Price-List Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/extract-supplier-price-list/` | `views.extract_supplier_price_list_data_view` | `quoting:extract_supplier_price_list_data` | Extract data from a supplier price list using Gemini. |

#### System
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/mcp/job_context/<uuid:job_id>/` | `views.job_context_api` | `quoting:mcp_job_context` | MCP API endpoint for fetching job context (for "Interactive Quote" button). |
| `/api/mcp/search_stock/` | `views.search_stock_api` | `quoting:mcp_search_stock` | MCP API endpoint for searching internal stock inventory. |
| `/api/mcp/search_supplier_prices/` | `views.search_supplier_prices_api` | `quoting:mcp_search_supplier_prices` | MCP API endpoint for searching supplier pricing. |

### Upload-Price-List Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/upload-price-list/` | `views.UploadPriceListView` | `quoting:upload_price_list` | No description available |

### Upload-Supplier-Pricing Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/upload-supplier-pricing/` | `views.UploadSupplierPricingView` | `quoting:upload_supplier_pricing` | No description available |
