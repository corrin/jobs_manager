from django.contrib import admin

from .models import PurchaseOrder, PurchaseOrderLine


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        "po_number",
        "supplier",
        "status",
        "order_date",
        "expected_delivery",
    ]
    list_filter = ["status", "supplier", "order_date"]
    search_fields = ["po_number", "supplier__name", "reference"]
    readonly_fields = ["xero_id"]


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = [
        "purchase_order",
        "description",
        "quantity",
        "unit_cost",
        "metal_type",
        "received_quantity",
    ]
    list_filter = ["metal_type", "purchase_order__status", "price_tbc"]
    search_fields = ["description", "supplier_item_code", "dimensions"]
