"""
Purchasing views module.
Centralized imports following Single Responsibility Principle.
"""

# Delivery Receipt views
from .delivery_receipt import (
    DeliveryReceiptCreateView,
    DeliveryReceiptListView,
    process_delivery_receipt,
)

# Product Mapping views
from .product_mapping import product_mapping_validation, validate_mapping

# Purchase Order views
from .purchase_order import (
    PurchaseOrderCreateView,
    PurchaseOrderEmailView,
    PurchaseOrderListView,
    PurchaseOrderPDFView,
    autosave_purchase_order_view,
    delete_purchase_order_view,
    extract_supplier_quote_data_view,
)

# Stock Management views
from .stock import (
    consume_stock_api_view,
    create_stock_api_view,
    deactivate_stock_api_view,
    search_available_stock_api,
    use_stock_view,
)

__all__ = [
    # Purchase Order views
    "PurchaseOrderListView",
    "PurchaseOrderCreateView",
    "autosave_purchase_order_view",
    "delete_purchase_order_view",
    "extract_supplier_quote_data_view",
    "PurchaseOrderPDFView",
    "PurchaseOrderEmailView",
    # Delivery Receipt views
    "DeliveryReceiptListView",
    "DeliveryReceiptCreateView",
    "process_delivery_receipt",
    # Stock Management views
    "use_stock_view",
    "consume_stock_api_view",
    "create_stock_api_view",
    "search_available_stock_api",
    "deactivate_stock_api_view",
    # Product Mapping views
    "product_mapping_validation",
    "validate_mapping",
]
