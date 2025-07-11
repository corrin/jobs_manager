# This file is autogenerated by update_init.py script

from .apps import PurchasingConfig

# Conditional imports (only when Django is ready)
try:
    from django.apps import apps

    if apps.ready:
        from .admin import PurchaseOrderAdmin, PurchaseOrderLineAdmin
        from .forms import PurchaseOrderForm, PurchaseOrderLineForm
        from .models import (
            PurchaseOrder,
            PurchaseOrderLine,
            PurchaseOrderSupplierQuote,
            Stock,
        )
        from .serializers import (
            AllJobsResponseSerializer,
            AllocationItemSerializer,
            DeliveryReceiptAllocationSerializer,
            DeliveryReceiptLineSerializer,
            DeliveryReceiptRequestSerializer,
            DeliveryReceiptResponseSerializer,
            JobForPurchasingSerializer,
            PurchaseOrderAllocationsResponseSerializer,
            PurchaseOrderCreateResponseSerializer,
            PurchaseOrderCreateSerializer,
            PurchaseOrderDetailSerializer,
            PurchaseOrderEmailRequestSerializer,
            PurchaseOrderEmailResponseSerializer,
            PurchaseOrderLineCreateSerializer,
            PurchaseOrderLineSerializer,
            PurchaseOrderListSerializer,
            PurchaseOrderPDFResponseSerializer,
            PurchaseOrderUpdateResponseSerializer,
            PurchaseOrderUpdateSerializer,
            PurchasingErrorResponseSerializer,
            PurchasingJobsResponseSerializer,
            StockConsumeRequestSerializer,
            StockConsumeResponseSerializer,
            StockCreateResponseSerializer,
            StockCreateSerializer,
            StockDeactivateResponseSerializer,
            StockListSerializer,
            XeroItemListResponseSerializer,
            XeroItemSerializer,
        )
except (ImportError, RuntimeError):
    # Django not ready or circular import, skip conditional imports
    pass

__all__ = [
    "AllJobsResponseSerializer",
    "AllocationItemSerializer",
    "DeliveryReceiptAllocationSerializer",
    "DeliveryReceiptLineSerializer",
    "DeliveryReceiptRequestSerializer",
    "DeliveryReceiptResponseSerializer",
    "JobForPurchasingSerializer",
    "PurchaseOrder",
    "PurchaseOrderAdmin",
    "PurchaseOrderAllocationsResponseSerializer",
    "PurchaseOrderCreateResponseSerializer",
    "PurchaseOrderCreateSerializer",
    "PurchaseOrderDetailSerializer",
    "PurchaseOrderEmailRequestSerializer",
    "PurchaseOrderEmailResponseSerializer",
    "PurchaseOrderForm",
    "PurchaseOrderLine",
    "PurchaseOrderLineAdmin",
    "PurchaseOrderLineCreateSerializer",
    "PurchaseOrderLineForm",
    "PurchaseOrderLineSerializer",
    "PurchaseOrderListSerializer",
    "PurchaseOrderPDFResponseSerializer",
    "PurchaseOrderSupplierQuote",
    "PurchaseOrderUpdateResponseSerializer",
    "PurchaseOrderUpdateSerializer",
    "PurchasingConfig",
    "PurchasingErrorResponseSerializer",
    "PurchasingJobsResponseSerializer",
    "Stock",
    "StockConsumeRequestSerializer",
    "StockConsumeResponseSerializer",
    "StockCreateResponseSerializer",
    "StockCreateSerializer",
    "StockDeactivateResponseSerializer",
    "StockListSerializer",
    "XeroItemListResponseSerializer",
    "XeroItemSerializer",
]
