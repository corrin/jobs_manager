from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

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
        if self.quantity < 0:
            raise ValidationError("Quantity must be non-negative")
        if self.unit_cost < 0:
            raise ValidationError("Unit cost must be non-negative")
        if self.unit_rev < 0:
            raise ValidationError("Unit revenue must be non-negative")
