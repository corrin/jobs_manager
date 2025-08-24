import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .job import Job


class CostSet(models.Model):
    """
    Represents a set of costs for a job in a specific revision.
    Can be an estimate, quote or actual cost.
    """

    KIND_CHOICES = [
        ("estimate", "Estimate"),
        ("quote", "Quote"),
        ("actual", "Actual"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="cost_sets")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    rev = models.IntegerField()
    summary = models.JSONField(default=dict, help_text="Summary data for this cost set")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "kind", "rev"], name="unique_job_kind_rev"
            )
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.job.name} - {self.get_kind_display()} Rev {self.rev}"

    def clean(self):
        if self.rev < 0:
            raise ValidationError("Revision must be non-negative")

    @property
    def total_cost(self):
        """Total internal cost for all cost lines in this set"""
        return sum(cost_line.total_cost for cost_line in self.cost_lines.all())

    @property
    def total_revenue(self):
        """Total revenue (charge amount) for all cost lines in this set"""
        return sum(cost_line.total_rev for cost_line in self.cost_lines.all())


class CostLine(models.Model):
    """
    Represents a cost line within a CostSet.
    Can be time, material or adjustment.
    """

    KIND_CHOICES = [
        ("time", "Time"),
        ("material", "Material"),
        ("adjust", "Adjustment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cost_set = models.ForeignKey(
        CostSet, on_delete=models.CASCADE, related_name="cost_lines"
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    desc = models.CharField(max_length=255, help_text="Description of this cost line")
    quantity = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("1.000")
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    unit_rev = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    ext_refs = models.JSONField(
        default=dict,
        help_text="External references (e.g., time entry IDs, material IDs)",
    )
    meta = models.JSONField(default=dict, help_text="Additional metadata")

    # Xero sync fields for bidirectional time/expense tracking
    xero_time_id = models.CharField(max_length=255, null=True, blank=True)
    xero_expense_id = models.CharField(max_length=255, null=True, blank=True)
    xero_last_modified = models.DateTimeField(null=True, blank=True)
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["cost_set_id", "kind"]),
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.cost_set} - {self.get_kind_display()}: {self.desc}"

    @property
    def total_cost(self):
        """Calculates total cost (quantity * unit cost)"""
        return self.quantity * self.unit_cost

    @property
    def total_rev(self):
        """Calculates total revenue (quantity * unit revenue)"""
        return self.quantity * self.unit_rev

    def clean(self):
        import logging

        logger = logging.getLogger(__name__)

        # Log negative quantities but allow them (for adjustments, corrections, returns, etc.)
        if self.quantity < 0:
            logger.warning(
                f"CostLine has negative quantity: {self.quantity} for {self.desc}"
            )

        if self.unit_cost < 0:
            raise ValidationError("Unit cost must be non-negative")
        if self.unit_rev < 0:
            raise ValidationError("Unit revenue must be non-negative")
