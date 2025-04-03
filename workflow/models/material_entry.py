# material_entry.py
import uuid
from decimal import Decimal

from django.db import models

from .company_defaults import CompanyDefaults
from .purchase import PurchaseOrderLine


class MaterialEntry(models.Model):
    """Materials, e.g., sheets"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        "JobPricing",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="material_entries",
    )
    item_code = models.CharField(
        max_length=20, null=False, blank=True, default=""
    )  # Later a FK probably
    description = models.CharField(max_length=200, null=False, blank=True, default="")
    comments = models.CharField(
        max_length=200, null=False, blank=True, default=""
    )  # Freetext internal note
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, default=0
    )  # Default comes up on the dummy row
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, default=0
    )
    unit_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, default=0
    )
    purchase_order_line = models.ForeignKey(
        PurchaseOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_entries",
        help_text="Source purchase order line if created from a PO receipt",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    @property
    def cost(self) -> Decimal:
        return self.unit_cost * self.quantity

    @property
    def revenue(self) -> Decimal:
        return self.unit_revenue * self.quantity

    def __str__(self):
        return f"Material for {self.job_pricing.job.name} - {self.description}"
