import uuid
from decimal import Decimal

from django.db import models


class MaterialEntry(models.Model):
    """Materials, e.g., sheets"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part = models.ForeignKey(
        "Part",
        on_delete=models.CASCADE,
        null=False,  # Required after migration
        blank=False,
        related_name="material_entries",
        help_text="The part this material entry belongs to",
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
    source_stock = models.ForeignKey(
        "workflow.Stock",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='consumed_entries',
        help_text="The Stock item consumed to create this entry"
    )
    purchase_order_line = models.ForeignKey(
        "workflow.PurchaseOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_entries",
        help_text="Convenience link to original PO line (derived via source_stock)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        db_table = "workflow_materialentry"

    @property
    def cost(self) -> Decimal:
        return self.unit_cost * self.quantity

    @property
    def revenue(self) -> Decimal:
        return self.unit_revenue * self.quantity

    def __str__(self):
        job_name = self.part.job_pricing.job.name
        return f"Material for {job_name} - {self.description}"
