from rest_framework import serializers

from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    """Serializer for PurchaseOrderLine model."""

    job_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id",
            "item_code",
            "description",
            "quantity",
            "received_quantity",
            "unit_cost",
            "price_tbc",
            "metal_type",
            "alloy",
            "specifics",
            "location",
            "job_id",
        ]


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    """Return purchase order details with related lines."""

    supplier = serializers.SerializerMethodField()
    supplier_id = serializers.SerializerMethodField()
    supplier_has_xero_id = serializers.SerializerMethodField()
    lines = PurchaseOrderLineSerializer(source="po_lines", many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "po_number",
            "reference",
            "supplier",
            "supplier_id",
            "supplier_has_xero_id",
            "status",
            "order_date",
            "expected_delivery",
            "lines",
            "online_url",
            "xero_id",
        ]

    def get_supplier(self, obj):
        return obj.supplier.name if obj.supplier else ""

    def get_supplier_id(self, obj):
        return str(obj.supplier.id) if obj.supplier else None

    def get_supplier_has_xero_id(self, obj):
        return obj.supplier.xero_contact_id is not None if obj.supplier else False
