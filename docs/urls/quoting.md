# Quoting URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Extract-Supplier-Price-List Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/extract-supplier-price-list/` | `views.extract_supplier_price_list_data_view` | `quoting:extract_supplier_price_list_data` | Complete supplier price list processing pipeline: |

#### System
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/mcp/job_context/<uuid:job_id>/` | `views.job_context_api` | `quoting:mcp_job_context` | No description available |
| `/api/mcp/search_stock/` | `views.search_stock_api` | `quoting:mcp_search_stock` | No description available |
| `/api/mcp/search_supplier_prices/` | `views.search_supplier_prices_api` | `quoting:mcp_search_supplier_prices` | No description available |

### Pdf-Import Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/pdf-import/` | `views.PDFPriceListImportView` | `quoting:pdf_price_list_import` | Enhanced view for uploading and processing supplier pricing PDFs with preview functionality. |

### Upload-Price-List Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/upload-price-list/` | `views.UploadPriceListView` | `quoting:upload_price_list` | No description available |

### Upload-Supplier-Pricing Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/upload-supplier-pricing/` | `views.UploadSupplierPricingView` | `quoting:upload_supplier_pricing` | No description available |
