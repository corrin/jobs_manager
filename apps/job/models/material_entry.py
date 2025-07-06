import logging
import uuid
import warnings
from decimal import Decimal

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class MaterialEntry(models.Model):
    """
    DEPRECATED: Materials, e.g., sheets

    This model is deprecated and should not be used for new functionality.
    Use CostLine with CostSet instead for all new material tracking.

    Legacy model for backward compatibility only.
    """

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
    source_stock = models.ForeignKey(
        "purchasing.Stock",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="consumed_entries",
        help_text="The Stock item consumed to create this entry",
    )
    purchase_order_line = models.ForeignKey(
        "purchasing.PurchaseOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_entries",
        help_text="Convenience link to original PO line (derived via source_stock)",
    )

    accounting_date = models.DateField(
        null=False,
        blank=False,
        default=timezone.now,  # Will use current date as default
        help_text="Date for accounting purposes (when the material was used)",
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

    def save(self, *args, **kwargs):
        """
        Save method with deprecation warning.
        """
        warnings.warn(
            "MaterialEntry is deprecated. Use CostLine with CostSet instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.warning(
            f"Creating deprecated MaterialEntry for job_pricing {self.job_pricing_id}. "
            "Consider using CostLine with CostSet instead."
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Material for {self.job_pricing.job.name} - {self.description}"
