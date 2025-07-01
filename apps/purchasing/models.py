import logging
import os
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import IntegerField, Max
from django.db.models.functions import Cast, Substr
from django.utils import timezone

from apps.job.enums import MetalType
from apps.job.models import Job
from apps.workflow.helpers import get_company_defaults

logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    """A request to purchase materials from a supplier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        "client.Client",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        null=True,
        blank=True,
    )
    job = models.ForeignKey(
        "job.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary job this PO is for",
    )
    po_number = models.CharField(max_length=50, unique=True)
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional reference for the purchase order",
    )
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    xero_id = models.UUIDField(unique=True, null=True, blank=True)
    xero_tenant_id = models.CharField(
        max_length=255, null=True, blank=True
    )  # For reference only - we are not fully multi-tenant yet
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted to Supplier"),
            ("partially_received", "Partially Received"),
            ("fully_received", "Fully Received"),
            ("deleted", "Deleted"),
        ],
        default="draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    xero_last_modified = models.DateTimeField(null=True, blank=True)
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)
    online_url = models.URLField(max_length=500, null=True, blank=True)
    raw_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw JSON data from Xero for this purchase order",
    )

    def generate_po_number(self):
        """Generate the next sequential PO number based on the configured prefix."""
        defaults = get_company_defaults()
        start = defaults.starting_po_number
        po_prefix = defaults.po_prefix  # Get prefix from CompanyDefaults

        prefix_len = len(po_prefix)

        # 1) Filter to exactly <prefix><digits> (removed hyphen from regex)
        # 2) Strip off "<prefix>" (first prefix_len chars), cast the rest to int
        # 3) Take the MAX of that numeric part
        agg = (
            PurchaseOrder.objects.filter(po_number__regex=rf"^{po_prefix}\d+$")
            .annotate(num=Cast(Substr("po_number", prefix_len + 1), IntegerField()))
            .aggregate(max_num=Max("num"))
        )
        max_existing = agg["max_num"] or 0

        nxt = max(start, max_existing + 1)
        return f"{po_prefix}{nxt:04d}"  # Use the dynamic prefix

    def save(self, *args, **kwargs):
        """Save the model and auto-generate PO number if none exists."""
        if not self.po_number:
            self.po_number = self.generate_po_number()

        super().save(*args, **kwargs)

    def reconcile(self):
        """Check received quantities against ordered quantities."""
        for line in self.po_lines.all():
            total_received = sum(
                po_line.quantity for po_line in line.received_lines.all()
            )
            if total_received > line.quantity:
                return "Over"
            elif total_received < line.quantity:
                return "Partial"

        self.status = "fully_received"
        self.save()
        return "Reconciled"

    class Meta:
        db_table = "workflow_purchaseorder"


class PurchaseOrderLine(models.Model):
    """A line item on a PO."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        "purchasing.PurchaseOrder", on_delete=models.CASCADE, related_name="po_lines"
    )
    job = models.ForeignKey(
        "job.Job",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_order_lines",
        help_text="The job this purchase line is for",
    )
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    dimensions = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Dimensions such as length, width, height, etc.",
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    price_tbc = models.BooleanField(
        default=False,
        help_text="If true, the price is to be confirmed and unit cost will be None",
    )
    supplier_item_code = models.CharField(
        max_length=50, blank=True, null=True, help_text="Supplier's own item code/SKU"
    )
    item_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Internal item code for Xero integration",
    )
    received_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total quantity received against this line",
    )
    metal_type = models.CharField(
        max_length=100,
        choices=MetalType.choices,
        default=MetalType.UNSPECIFIED,
        blank=True,
        null=True,
    )
    alloy = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Alloy specification (e.g., 304, 6061)",
    )
    specifics = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Specific details (e.g., m8 countersunk socket screw)",
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Where this item will be stored",
    )
    raw_line_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw JSON data from the source system or document",
    )

    class Meta:
        db_table = "workflow_purchaseorderline"


class PurchaseOrderSupplierQuote(models.Model):
    """A quote file attached to a purchase order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.OneToOneField(
        PurchaseOrder, related_name="supplier_quote", on_delete=models.CASCADE
    )
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_data = models.JSONField(
        null=True, blank=True, help_text="Extracted data from the quote"
    )
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("deleted", "Deleted")],
        default="active",
    )

    @property
    def full_path(self):
        """Full system path to the file."""
        return os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, self.file_path)

    @property
    def url(self):
        """URL to serve the file."""
        return f"/purchases/quotes/{self.file_path}"

    @property
    def size(self):
        """Return size of file in bytes."""
        if self.status == "deleted":
            return None

        file_path = self.full_path
        return os.path.getsize(file_path) if os.path.exists(file_path) else None

    class Meta:
        db_table = "workflow_purchaseordersupplierquote"


class Stock(models.Model):
    """
    Model for tracking inventory items.
    Each stock item represents a quantity of material that can be assigned to jobs.

    EARLY DRAFT: REVIEW AND TEST
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_items",
        help_text="The job this stock item is assigned to",
    )

    item_code = models.CharField(
        max_length=255, blank=True, null=True, help_text="Xero Item Code"
    )

    description = models.CharField(
        max_length=255, help_text="Description of the stock item"
    )

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Current quantity of the stock item"
    )

    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Cost per unit of the stock item"
    )

    retail_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.2"),
        help_text="Retail markup rate for this stock item (e.g., 0.2 for 20%)",
    )

    date = models.DateTimeField(
        default=timezone.now, help_text="Date the stock item was created"
    )

    source = models.CharField(
        max_length=50,
        choices=[
            ("purchase_order", "Purchase Order Receipt"),
            ("split_from_stock", "Split/Offcut from Stock"),
            ("manual", "Manual Adjustment/Stocktake"),
        ],
        help_text="Origin of this stock item",
    )

    source_purchase_order_line = models.ForeignKey(
        "purchasing.PurchaseOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_generated",
        help_text="The PO line this stock originated from (if source='purchase_order')",
    )
    source_parent_stock = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_stock_splits",
        help_text="The parent stock item this was split from (if source='split_from_stock')",
    )
    location = models.TextField(blank=True, help_text="Where we are keeping this")
    notes = models.TextField(
        blank=True, help_text="Additional notes about the stock item"
    )
    metal_type = models.CharField(
        max_length=100,
        choices=MetalType.choices,
        default=MetalType.UNSPECIFIED,
        blank=True,
        help_text="Type of metal",
    )
    alloy = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Alloy specification (e.g., 304, 6061)",
    )
    specifics = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Specific details (e.g., m8 countersunk socket screw)",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="False when quantity reaches zero or item is fully consumed/transformed",
    )

    xero_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique ID from Xero for this item",
    )
    xero_last_modified = models.DateTimeField(
        null=True, blank=True, help_text="Last modified date from Xero for this item"
    )
    raw_json = models.JSONField(
        null=True, blank=True, help_text="Raw JSON data from Xero for this item"
    )
    xero_inventory_tracked = models.BooleanField(
        default=False, help_text="Whether this item is inventory-tracked in Xero"
    )

    # Parser tracking fields
    parsed_at = models.DateTimeField(
        blank=True, null=True, help_text="When this inventory item was parsed by LLM"
    )
    parser_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Version of parser used for this data",
    )
    parser_confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Parser confidence score 0.00-1.00",
    )

    # TODO: Add fields for:
    # - Location
    # - Minimum stock level
    # - Reorder point
    # - Category/Type
    # - Unit of measure

    def __str__(self):
        return f"{self.description} ({self.quantity})"

    def save(self, *args, **kwargs):
        """
        Override save to add logging and validation.
        """
        logger.debug(f"Saving stock item: {self.description}")

        # Validate quantity is not negative
        if self.quantity < 0:
            logger.warning(
                f"Attempted to save stock item with negative quantity: {self.quantity}"
            )
            raise ValueError("Stock quantity cannot be negative")

        # Validate unit cost is not negative
        if self.unit_cost < 0:
            logger.warning(
                f"Attempted to save stock item with negative unit cost: {self.unit_cost}"
            )
            raise ValueError("Unit cost cannot be negative")

        super().save(*args, **kwargs)
        logger.info(f"Saved stock item: {self.description}")

    # Stock holding job name
    STOCK_HOLDING_JOB_NAME = "Worker Admin"
    _stock_holding_job = None

    @classmethod
    def get_stock_holding_job(cls):
        """
        Returns the job designated for holding general stock.
        This is a utility method to avoid repeating the job lookup across the codebase.
        Uses a class-level cache to avoid repeated database queries.
        """
        if cls._stock_holding_job is None:
            cls._stock_holding_job = Job.objects.get(name=cls.STOCK_HOLDING_JOB_NAME)
        return cls._stock_holding_job

    class Meta:
        db_table = "workflow_stock"
        constraints = [
            models.UniqueConstraint(fields=["xero_id"], name="unique_xero_id_stock")
        ]
