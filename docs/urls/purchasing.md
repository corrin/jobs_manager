# Purchasing URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

### All-Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/all-jobs/` | `purchasing_rest_views.AllJobsAPIView` | `purchasing:purchasing_all_jobs_rest` | API endpoint to get all jobs with stock holding job flag. |

### Delivery-Receipts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/delivery-receipts/` | `purchasing_rest_views.DeliveryReceiptRestView` | `purchasing:delivery_receipts_rest` | REST API view for processing delivery receipts. |

### Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/jobs/` | `purchasing_rest_views.PurchasingJobsAPIView` | `purchasing:purchasing_jobs_rest` | API endpoint to get jobs for purchasing contexts (PO lines, stock allocation, etc.). |

### Product-Mappings Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/product-mappings/` | `purchasing_rest_views.ProductMappingListView` | `purchasing:product_mappings_rest` | REST API view for listing product parsing mappings. |
| `/product-mappings/<uuid:mapping_id>/validate/` | `purchasing_rest_views.ProductMappingValidateView` | `purchasing:product_mapping_validate_rest` | REST API view for validating a product parsing mapping. |

### Purchase-Orders Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/purchase-orders/` | `purchasing_rest_views.PurchaseOrderListCreateRestView` | `purchasing:purchase_orders_rest` | REST API view for listing and creating purchase orders. |
| `/purchase-orders/<uuid:id>/` | `purchasing_rest_views.PurchaseOrderDetailRestView` | `purchasing:purchase_order_detail_rest` | Returns a full PO (including lines). |
| `/purchase-orders/<uuid:po_id>/allocations/` | `purchasing_rest_views.PurchaseOrderAllocationsAPIView` | `purchasing:purchase_order_allocations_rest` | API endpoint to get existing allocations for a purchase order. |
| `/purchase-orders/<uuid:po_id>/allocations/<str:allocation_type>/<uuid:allocation_id>/details/` | `purchasing_rest_views.AllocationDetailsAPIView` | `purchasing:allocation_details_rest` | API endpoint to get details about a specific allocation before deletion. |
| `/purchase-orders/<uuid:po_id>/lines/<uuid:line_id>/allocations/delete/` | `purchasing_rest_views.AllocationDeleteAPIView` | `purchasing:allocation_delete_rest` | API endpoint to delete specific allocations from a purchase order. |

### Stock Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/stock/` | `purchasing_rest_views.StockListRestView` | `purchasing:stock_list_rest` | REST API view for listing and creating stock items. |
| `/stock/<uuid:stock_id>/` | `purchasing_rest_views.StockDeactivateRestView` | `purchasing:stock_deactivate_rest` | REST API view for deactivating stock items. |
| `/stock/<uuid:stock_id>/consume/` | `purchasing_rest_views.StockConsumeRestView` | `purchasing:stock_consume_rest` | REST API view for consuming stock items for jobs. |

### Supplier-Price-Status Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/supplier-price-status/` | `purchasing_rest_views.SupplierPriceStatusAPIView` | `purchasing:supplier_price_status_rest` | Return latest price upload status per supplier. |

### Xero-Items Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/xero-items/` | `purchasing_rest_views.XeroItemList` | `purchasing:xero_items_rest` | Return list of items from Xero. |
