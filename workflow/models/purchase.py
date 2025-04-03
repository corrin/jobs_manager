import uuid

from django.db import models
from django.db.models import Max
from django.utils import timezone

from workflow.helpers import get_company_defaults
from workflow.models import CompanyDefaults


class PurchaseOrder(models.Model):
    """A request to purchase materials from a supplier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        "Client",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    job = models.ForeignKey(
        "Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary job this PO is for",
    )
    po_number = models.CharField(max_length=50, unique=True)
    reference = models.CharField(max_length=100, blank=True, null=True, help_text="Optional reference for the purchase order")
    order_date = models.DateField()
    expected_delivery = models.DateField(null=True, blank=True)
    xero_id = models.UUIDField(unique=True, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted to Supplier"),
            ("partially_received", "Partially Received"),
            ("fully_received", "Fully Received"),
            ("void", "Voided"),
        ],
        default="draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    xero_last_modified = models.DateTimeField(null=True, blank=True)
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)
    raw_json = models.JSONField(null=True, blank=True) 
    online_url = models.URLField(max_length=500, null=True, blank=True)

    def generate_po_number(self):
        """Generate a sequential PO number based on company defaults."""
        company_defaults = get_company_defaults()
        starting_number = company_defaults.starting_po_number

        highest_po = PurchaseOrder.objects.all().aggregate(Max('po_number'))['po_number__max'] or 0
        
        # If the highest PO is a string (like "PO-12345"), extract the number part
        if isinstance(highest_po, str) and '-' in highest_po:
            try:
                highest_po = int(highest_po.split('-')[1])
            except (IndexError, ValueError):
                highest_po = 0
        
        # Generate the next number
        next_number = max(starting_number, int(highest_po) + 1)
        
        # Return with PO prefix and zero-padding (e.g., PO-0013)
        return f"PO-{next_number:04d}"

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


class PurchaseOrderLine(models.Model):
    """A line item on a PO."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="po_lines"
    )
    job = models.ForeignKey(
        "Job",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_order_lines",
        help_text="The job this purchase line is for",
    )
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_tbc = models.BooleanField(default=False, help_text="If true, the price is to be confirmed and unit cost will be None")
    item_code = models.CharField(max_length=20, blank=True)
    received_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total quantity received against this line",
    )
