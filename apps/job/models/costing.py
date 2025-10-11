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

    Meta Field Structure by Kind:

    TIME (kind='time'):
        - staff_id (str, UUID): Reference to Staff member who performed the work
        - date (str, ISO date): Date the work was performed (legacy, use accounting_date field)
        - is_billable (bool): Whether this time is billable to the client
        - wage_rate_multiplier (float): Multiplier for staff wage rate (e.g., 1.5 for overtime)
        - rate_multiplier (float): Alternative name for wage_rate_multiplier (legacy)
        - note (str): Optional notes about the time entry
        - created_from_timesheet (bool): True if created via modern timesheet interface
        - wage_rate (float): Wage rate at time of entry (for timesheet entries)
        - charge_out_rate (float): Charge-out rate at time of entry (for timesheet entries)

    MATERIAL (kind='material'):
        - item_code (str): Stock item code reference
        - comments (str): Notes about the material usage
        - source (str): Origin of the material entry ('delivery_receipt' for PO deliveries)
        - retail_rate (float): Retail markup rate applied (e.g., 0.2 for 20%)
        - po_number (str): Purchase order reference number
        - consumed_by (str): Reference to what consumed this material

    ADJUSTMENT (kind='adjust'):
        - comments (str): Explanation of the adjustment
        - source (str): Origin of adjustment ('manual_adjustment' for user-created)
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
    meta = models.JSONField(
        default=dict,
        help_text="Additional metadata - structure varies by kind (see class docstring)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Accounting date - the date this cost should be attributed to for reporting
    accounting_date = models.DateField(
        help_text="The date this cost should be attributed to for accounting purposes",
    )

    # Xero sync fields for bidirectional time/expense tracking
    # This really shouldn't be here. It should be on ext_refs. That's the whole point of ext_refs and the whole costline model.
    # This violates the hexagonal architecture principles.
    xero_time_id = models.CharField(max_length=255, null=True, blank=True)
    xero_expense_id = models.CharField(max_length=255, null=True, blank=True)
    xero_last_modified = models.DateTimeField(null=True, blank=True)
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["cost_set_id", "kind"]),
            models.Index(fields=["cost_set_id", "created_at"]),
            models.Index(fields=["cost_set_id", "kind", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

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

        # Allow negative values for adjustments, discounts, credits, etc.

    def _update_cost_set_summary(self) -> None:
        """Update cost set summary with aggregated data - PRESERVE existing data"""
        cost_set = self.cost_set
        cost_lines = cost_set.cost_lines.all()

        total_cost = sum(line.total_cost for line in cost_lines)
        total_rev = sum(line.total_rev for line in cost_lines)
        total_hours = sum(
            float(line.quantity) for line in cost_lines if line.kind == "time"
        )

        # Preserve existing summary data (especially revisions)
        current_summary = cost_set.summary or {}
        current_summary.update(
            {
                "cost": float(total_cost),
                "rev": float(total_rev),
                "hours": total_hours,
            }
        )

        cost_set.summary = current_summary  # Preserves revisions[]
        cost_set.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_cost_set_summary()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._update_cost_set_summary()
