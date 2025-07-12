# Purchasing URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Delivery-Receipts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/delivery-receipts/process/` | `purchasing_rest_views.DeliveryReceiptRestView` | `purchasing:delivery_receipts_process` | REST API view for processing delivery receipts. |

#### Product-Mapping Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/product-mapping/<uuid:mapping_id>/validate/` | `product_mapping.validate_mapping` | `purchasing:validate_mapping` | Validate a product parsing mapping. |

#### Purchase-Orders Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/purchase-orders/<uuid:purchase_order_id>/email/` | `purchase_order.PurchaseOrderEmailView` | `purchasing:purchase_orders_email` | API view for generating email links for purchase orders. |
| `/api/purchase-orders/<uuid:purchase_order_id>/pdf/` | `purchase_order.PurchaseOrderPDFView` | `purchasing:purchase_orders_pdf` | API view for generating and returning PDF documents for purchase orders. |
| `/api/purchase-orders/autosave/` | `purchase_order.autosave_purchase_order_view` | `purchasing:purchase_orders_autosave` | Autosave purchase order data and sync with Xero. |

#### Stock Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/stock/<uuid:stock_id>/deactivate/` | `stock.deactivate_stock_api_view` | `purchasing:stock_deactivate_api` | API endpoint to deactivate a stock item (soft delete). |
| `/api/stock/consume/` | `stock.consume_stock_api_view` | `purchasing:stock_consume_api` | API endpoint to consume stock. |
| `/api/stock/create/` | `stock.create_stock_api_view` | `purchasing:stock_create_api` | API endpoint to create a new stock item. |
| `/api/stock/search/` | `stock.search_available_stock_api` | `purchasing:stock_search_api` | API endpoint to search available stock items for autocomplete. |

#### Supplier-Quotes Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/supplier-quotes/extract/` | `purchase_order.extract_supplier_quote_data_view` | `purchasing:supplier_quotes_extract` | Extract data from a supplier quote to pre-fill a PO form. |

### All-Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/all-jobs/` | `purchasing_rest_views.AllJobsAPIView` | `purchasing:purchasing_all_jobs_rest` | API endpoint to get all jobs with stock holding job flag. |

### Delivery-Receipts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/delivery-receipts/` | `delivery_receipt.DeliveryReceiptListView` | `purchasing:delivery_receipts_list` | View to list all purchase orders that can be received. |
| `/delivery-receipts/` | `purchasing_rest_views.DeliveryReceiptRestView` | `purchasing:delivery_receipts_rest` | REST API view for processing delivery receipts. |
| `/delivery-receipts/<uuid:pk>/` | `delivery_receipt.DeliveryReceiptCreateView` | `purchasing:delivery_receipts_create` | View to create a delivery receipt for a purchase order. |

### Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/jobs/` | `purchasing_rest_views.PurchasingJobsAPIView` | `purchasing:purchasing_jobs_rest` | API endpoint to get jobs for purchasing contexts (PO lines, stock allocation, etc.). |

### Product-Mapping Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/product-mapping/` | `product_mapping.product_mapping_validation` | `purchasing:product_mapping_validation` | Modern interface for validating product parsing mappings. |

### Purchase-Orders Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/purchase-orders/` | `purchase_order.PurchaseOrderListView` | `purchasing:purchase_orders_list` | View to list all purchase orders. |
| `/purchase-orders/` | `purchasing_rest_views.PurchaseOrderListCreateRestView` | `purchasing:purchase_orders_rest` | REST API view for listing and creating purchase orders. |
| `/purchase-orders/<uuid:pk>/` | `purchase_order.PurchaseOrderCreateView` | `purchasing:purchase_orders_detail` | View to create or edit a purchase order, following the timesheet pattern. |
| `/purchase-orders/<uuid:pk>/` | `purchasing_rest_views.PurchaseOrderDetailRestView` | `purchasing:purchase_order_detail_rest` | Returns a full PO (including lines) |
| `/purchase-orders/<uuid:pk>/delete/` | `purchase_order.delete_purchase_order_view` | `purchasing:purchase_orders_delete` | Delete a purchase order if it's in draft status. |
| `/purchase-orders/<uuid:po_id>/allocations/` | `purchasing_rest_views.PurchaseOrderAllocationsAPIView` | `purchasing:purchase_order_allocations_rest` | API endpoint to get existing allocations for a purchase order. |
| `/purchase-orders/new/` | `purchase_order.PurchaseOrderCreateView` | `purchasing:purchase_orders_create` | View to create or edit a purchase order, following the timesheet pattern. |

### Stock Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/stock/` | `purchasing_rest_views.StockListRestView` | `purchasing:stock_list_rest` | REST API view for listing and creating stock items. |
| `/stock/<uuid:stock_id>/` | `purchasing_rest_views.StockDeactivateRestView` | `purchasing:stock_deactivate_rest` | REST API view for deactivating stock items. |
| `/stock/<uuid:stock_id>/consume/` | `purchasing_rest_views.StockConsumeRestView` | `purchasing:stock_consume_rest` | REST API view for consuming stock items for jobs. |

### Use-Stock Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/use-stock/` | `stock.use_stock_view` | `purchasing:use_stock` | View for the Use Stock page. |
| `/use-stock/<uuid:job_id>/` | `stock.use_stock_view` | `purchasing:use_stock_with_job` | View for the Use Stock page. |

### Xero-Items Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/xero-items/` | `purchasing_rest_views.XeroItemList` | `purchasing:xero_items_rest` | Return list of items from Xero. |
