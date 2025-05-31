import uuid

from django.db import models


class AdjustmentEntry(models.Model):
    """For when costs are manually added to a job"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part = models.ForeignKey(
        "Part",
        on_delete=models.CASCADE,
        null=False,  # Required after migration
        blank=False,
        related_name="adjustment_entries",
        help_text="The part this adjustment entry belongs to",
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        db_table = "workflow_adjustmententry"

    def __str__(self):
        job_name = self.part.job_pricing.job.name
        return f"Adjustment for {job_name} - {self.description or 'No Description'}"
