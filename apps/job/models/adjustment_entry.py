import uuid

from django.db import models
from django.utils import timezone


class AdjustmentEntry(models.Model):
    """For when costs are manually added to a job"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        "JobPricing",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="adjustment_entries",
    )
    description = models.CharField(max_length=200, null=False, blank=True, default="")
    cost_adjustment = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, null=False
    )
    price_adjustment = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, null=False
    )
    comments = models.CharField(
        max_length=200, null=False, blank=True, default=""
    )  # Freetext internal note
    accounting_date = models.DateField(
        null=False,
        blank=False,
        default=timezone.now,  # Will use current date as default
        help_text="Date for accounting purposes (when the adjustment was made)",
    )
    is_quote_adjustment = models.BooleanField(
        default=False,
        help_text="True if this adjustment was automatically created to match quoted revenue",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        db_table = "workflow_adjustmententry"

    def __str__(self):
        return (
            f"Adjustment for {self.job_pricing.job.name} - "
            f"{self.description or 'No Description'}"
        )
