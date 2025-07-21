from rest_framework import serializers

from apps.job.models import Job
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine


class JobForPurchasingSerializer(serializers.ModelSerializer):
    """Serializer for Job model in purchasing contexts."""

    client_name = serializers.SerializerMethodField()
    is_stock_holding = serializers.SerializerMethodField()
    job_display_name = serializers.SerializerMethodField()

    def get_client_name(self, obj) -> str:
        return obj.client.name if obj.client else "No Client"

    def get_is_stock_holding(self, obj) -> bool:
        # This will be set dynamically in the view
        return getattr(obj, "_is_stock_holding", False)

    def get_job_display_name(self, obj) -> str:
        return f"{obj.job_number} - {obj.name}"

    class Meta:
        model = Job
        fields = [
            "id",
            "job_number",
            "name",
            "client_name",
            "status",
            "is_stock_holding",
            "job_display_name",
        ]


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
            "dimensions",
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

    def get_supplier(self, obj) -> str:
        return obj.supplier.name if obj.supplier else ""

    def get_supplier_id(self, obj) -> str | None:
        return str(obj.supplier.id) if obj.supplier else None

    def get_supplier_has_xero_id(self, obj) -> bool:
        return obj.supplier.xero_contact_id is not None if obj.supplier else False


class AllJobsResponseSerializer(serializers.Serializer):
    """Serializer for AllJobsAPIView response."""

    success = serializers.BooleanField()
    jobs = JobForPurchasingSerializer(many=True)
    stock_holding_job_id = serializers.CharField()


class DeliveryReceiptAllocationSerializer(serializers.Serializer):
    """Serializer for individual allocation within a delivery receipt line."""

    job_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)


class DeliveryReceiptLineSerializer(serializers.Serializer):
    """Serializer for delivery receipt line allocation data."""

    total_received = serializers.DecimalField(max_digits=10, decimal_places=2)
    allocations = DeliveryReceiptAllocationSerializer(many=True)


class DeliveryReceiptRequestSerializer(serializers.Serializer):
    """Serializer for delivery receipt request data."""

    purchase_order_id = serializers.UUIDField()
    allocations = serializers.DictField(
        child=DeliveryReceiptLineSerializer(),
        help_text="Dictionary where keys are PurchaseOrderLine IDs and values are allocation data",
    )


class DeliveryReceiptResponseSerializer(serializers.Serializer):
    """Serializer for delivery receipt response data."""

    success = serializers.BooleanField()
    error = serializers.CharField(required=False)


class PurchaseOrderListSerializer(serializers.Serializer):
    """Serializer for listing purchase orders from service data."""

    id = serializers.UUIDField()
    po_number = serializers.CharField()
    status = serializers.CharField()
    order_date = serializers.DateField()
    supplier = serializers.CharField()
    supplier_id = serializers.UUIDField(allow_null=True)


class PurchaseOrderLineCreateSerializer(serializers.Serializer):
    """Serializer for creating purchase order lines."""

    job_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    price_tbc = serializers.BooleanField(default=False)
    item_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    metal_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    alloy = serializers.CharField(max_length=100, required=False, allow_blank=True)
    specifics = serializers.CharField(max_length=255, required=False, allow_blank=True)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)
    dimensions = serializers.CharField(max_length=255, required=False, allow_blank=True)


class PurchaseOrderLineUpdateSerializer(serializers.Serializer):
    """Serializer for updating purchase order lines (includes ID)."""

    id = serializers.UUIDField(
        required=False, allow_null=True
    )  # Include ID for updates
    job_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    price_tbc = serializers.BooleanField(default=False)
    item_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    metal_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    alloy = serializers.CharField(max_length=100, required=False, allow_blank=True)
    specifics = serializers.CharField(max_length=255, required=False, allow_blank=True)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)
    dimensions = serializers.CharField(max_length=255, required=False, allow_blank=True)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    """Serializer for creating purchase orders."""

    supplier_id = serializers.UUIDField(required=False, allow_null=True)
    reference = serializers.CharField(max_length=255, required=False, allow_blank=True)
    order_date = serializers.DateField(required=False, allow_null=True)
    expected_delivery = serializers.DateField(required=False, allow_null=True)
    lines = PurchaseOrderLineCreateSerializer(many=True, required=False)


class PurchaseOrderCreateResponseSerializer(serializers.Serializer):
    """Serializer for purchase order creation response."""

    id = serializers.UUIDField()
    po_number = serializers.CharField()


class PurchaseOrderUpdateSerializer(serializers.Serializer):
    """Serializer for updating purchase orders."""

    supplier_id = serializers.UUIDField(required=False, allow_null=True)
    reference = serializers.CharField(max_length=255, required=False, allow_blank=True)
    expected_delivery = serializers.DateField(required=False, allow_null=True)
    status = serializers.CharField(max_length=50, required=False, allow_blank=True)
    lines_to_delete = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of line IDs to delete",
    )
    lines = PurchaseOrderLineUpdateSerializer(many=True, required=False)


class PurchaseOrderUpdateResponseSerializer(serializers.Serializer):
    """Serializer for purchase order update response."""

    id = serializers.UUIDField()
    status = serializers.CharField()


class AllocationItemSerializer(serializers.Serializer):
    """Serializer for individual allocation items (job or stock)."""

    type = serializers.ChoiceField(choices=[("job", "Job"), ("stock", "Stock")])
    job_id = serializers.UUIDField()
    job_name = serializers.CharField()
    quantity = serializers.FloatField()
    retail_rate = serializers.FloatField(default=0)
    allocation_date = serializers.DateTimeField(allow_null=True)
    description = serializers.CharField()

    # Optional field for stock allocations
    stock_location = serializers.CharField(required=False, allow_null=True)


class PurchaseOrderAllocationsResponseSerializer(serializers.Serializer):
    """Serializer for purchase order allocations response."""

    po_id = serializers.UUIDField()
    allocations = serializers.DictField(
        child=serializers.ListField(child=AllocationItemSerializer()),
        help_text="Dictionary where keys are PurchaseOrderLine IDs and values are lists of allocations",
    )


class StockListSerializer(serializers.Serializer):
    """Serializer for listing stock items from service data."""

    id = serializers.UUIDField()
    description = serializers.CharField()
    quantity = serializers.FloatField()
    unit_cost = serializers.FloatField()
    metal_type = serializers.CharField(allow_blank=True)
    alloy = serializers.CharField(allow_blank=True)
    specifics = serializers.CharField(allow_blank=True)
    location = serializers.CharField(allow_blank=True)
    source = serializers.CharField()
    date = serializers.DateTimeField(allow_null=True)
    job_id = serializers.UUIDField(allow_null=True)
    notes = serializers.CharField(allow_blank=True)


class StockCreateSerializer(serializers.Serializer):
    """Serializer for creating stock items."""

    description = serializers.CharField(max_length=255)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    source = serializers.CharField(max_length=100)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    metal_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    alloy = serializers.CharField(max_length=100, required=False, allow_blank=True)
    specifics = serializers.CharField(max_length=255, required=False, allow_blank=True)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)
    dimensions = serializers.CharField(max_length=255, required=False, allow_blank=True)


class StockCreateResponseSerializer(serializers.Serializer):
    """Serializer for stock creation response."""

    id = serializers.UUIDField()


# Additional serializers for purchasing rest views


class PurchasingJobsResponseSerializer(serializers.Serializer):
    """Serializer for PurchasingJobsAPIView response"""

    jobs = JobForPurchasingSerializer(many=True)
    total_count = serializers.IntegerField()


class XeroItemSerializer(serializers.Serializer):
    """Serializer for Xero item data"""

    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    sales_details = serializers.DictField(required=False)
    purchase_details = serializers.DictField(required=False)


class XeroItemListResponseSerializer(serializers.Serializer):
    """Serializer for XeroItemList response"""

    items = XeroItemSerializer(many=True)
    total_count = serializers.IntegerField(required=False)


class StockDeactivateResponseSerializer(serializers.Serializer):
    """Serializer for stock deactivation response"""

    success = serializers.BooleanField()
    message = serializers.CharField(required=False)


class StockConsumeRequestSerializer(serializers.Serializer):
    """Serializer for stock consumption request"""

    job_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class StockConsumeResponseSerializer(serializers.Serializer):
    """Serializer for stock consumption response"""

    success = serializers.BooleanField()
    message = serializers.CharField(required=False)
    remaining_quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )


class PurchasingErrorResponseSerializer(serializers.Serializer):
    """Serializer for purchasing error responses"""

    error = serializers.CharField(help_text="Error message")


# Purchase Order Email and PDF serializers
class PurchaseOrderEmailRequestSerializer(serializers.Serializer):
    """Serializer for purchase order email generation request"""

    recipient_email = serializers.EmailField(required=False)
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class PurchaseOrderEmailResponseSerializer(serializers.Serializer):
    """Serializer for purchase order email generation response"""

    success = serializers.BooleanField()
    email_subject = serializers.CharField(required=False)
    email_body = serializers.CharField(required=False)
    pdf_url = serializers.CharField(required=False)
    message = serializers.CharField(required=False)


class PurchaseOrderPDFResponseSerializer(serializers.Serializer):
    """Serializer for purchase order PDF generation response"""

    # This endpoint returns a PDF file (FileResponse), so this is primarily for documentation
    success = serializers.BooleanField(required=False)
    message = serializers.CharField(required=False)

    class Meta:
        help_text = "Generates and returns a PDF file for the specified purchase order"
