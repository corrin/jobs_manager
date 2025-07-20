from django.urls import path

from apps.purchasing.views.purchasing_rest_views import (
    AllJobsAPIView,
    DeliveryReceiptRestView,
    PurchaseOrderAllocationsAPIView,
    PurchaseOrderDetailRestView,
    PurchaseOrderListCreateRestView,
    PurchasingJobsAPIView,
    StockConsumeRestView,
    StockDeactivateRestView,
    StockListRestView,
    XeroItemList,
)

urlpatterns = [
    path("all-jobs/", AllJobsAPIView.as_view(), name="purchasing_all_jobs_rest"),
    path("jobs/", PurchasingJobsAPIView.as_view(), name="purchasing_jobs_rest"),
    path("xero-items/", XeroItemList.as_view(), name="xero_items_rest"),
    path(
        "purchase-orders/",
        PurchaseOrderListCreateRestView.as_view(),
        name="purchase_orders_rest",
    ),
    path(
        "delivery-receipts/",
        DeliveryReceiptRestView.as_view(),
        name="delivery_receipts_rest",
    ),
    path("stock/", StockListRestView.as_view(), name="stock_list_rest"),
    path(
        "stock/<uuid:stock_id>/consume/",
        StockConsumeRestView.as_view(),
        name="stock_consume_rest",
    ),
    path(
        "purchase-orders/<uuid:id>/",
        PurchaseOrderDetailRestView.as_view(),
        name="purchase_order_detail_rest",
    ),
    path(
        "purchase-orders/<uuid:po_id>/allocations/",
        PurchaseOrderAllocationsAPIView.as_view(),
        name="purchase_order_allocations_rest",
    ),
    path(
        "stock/<uuid:stock_id>/",
        StockDeactivateRestView.as_view(),
        name="stock_deactivate_rest",
    ),
]
