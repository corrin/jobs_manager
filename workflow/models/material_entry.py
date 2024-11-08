# material_entry.py

import uuid
from decimal import Decimal

from django.db import models


class MaterialEntry(models.Model):
    """Materials, e.g., sheets"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        "JobPricing",
        on_delete=models.CASCADE,
        related_name="material_entries",
    )
    item_code = models.CharField(
        max_length=20, null=True, blank=True
    )  # Later a FK probably
    description = models.CharField(max_length=200)
    comments = models.CharField(
        max_length=200, null=True, blank=True
    )  # Freetext internal note
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    unit_revenue = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def cost(self) -> Decimal:
        return self.unit_cost * self.quantity

    @property
    def revenue(self) -> Decimal:
        return self.unit_revenue * self.quantity

    def __str__(self):
        return f"Material for {self.job_pricing.job.name} - {self.description}"
