# workflow/models/job_pricing.py
import logging
import uuid
from decimal import Decimal

from django.db import models, transaction
from django.apps import apps

from workflow.enums import JobPricingStage, JobPricingType



logger = logging.getLogger(__name__)

class JobPricing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pricing_stage = models.CharField(
        max_length=20,
        choices=JobPricingStage.choices,
        default=JobPricingStage.ESTIMATE,
        help_text="Stage of the job pricing (estimate, quote, or reality).",
    )
    pricing_type = models.CharField(
        max_length=20,
        choices=JobPricingType.choices,
        default=JobPricingType.TIME_AND_MATERIALS,
        help_text="Type of pricing for the job (fixed price or time and materials).",
    )

    revision_number = models.PositiveIntegerField(
        default=1, help_text="Tracks the revision number for friendlier quotes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def material_entries(self):
        """Returns all MaterialEntries related to this JobPricing"""
        return self.materialentries_set.all()

    @property
    def time_entries(self):
        """Returns all TimeEntries related to this JobPricing"""
        return self.timeentries_set.all()

    @property
    def adjustment_entries(self):
        """Returns all AdjustmentEntries related to this JobPricing"""
        return self.adjustmententries_set.all()

    @property
    def total_time_cost(self):
        """Calculate the total cost for all time entries."""
        return sum(entry.cost for entry in self.time_entries.all())

    @property
    def total_time_revenue(self):
        """Calculate the total revenue for all time entries."""
        return sum(
            entry.revenue for entry in self.time_entries.all()
        )  # Assuming 'revenue' field exists

    @property
    def total_material_cost(self):
        """Calculate the total cost for all material entries."""
        return sum(
            entry.unit_cost * entry.quantity for entry in self.material_entries.all()
        )

    @property
    def total_material_revenue(self):
        """Calculate the total revenue for all material entries."""
        return sum(
            entry.unit_revenue * entry.quantity for entry in self.material_entries.all()
        )

    @property
    def total_adjustment_cost(self):
        """Calculate the total cost for all adjustment entries."""
        return sum(entry.cost_adjustment for entry in self.adjustment_entries.all())

    @property
    def total_adjustment_revenue(self):
        """Calculate the total cost for all adjustment entries."""
        return sum(entry.price_adjustment for entry in self.adjustment_entries.all())

    @property
    def total_cost(self):
        """Calculate the total cost including time, materials, and adjustments."""
        return (
            self.total_time_cost + self.total_material_cost + self.total_adjustment_cost
        )

    @property
    def total_revenue(self):
        """Calculate the total cost including time, materials, and adjustments."""
        return (
            self.total_time_revenue
            + self.total_material_revenue
            + self.total_adjustment_revenue
        )


    class Meta:
        ordering = [
            "-created_at",
            "pricing_stage",
        ]  # Orders by newest entries first, and then by stage

    def save(self, *args, **kwargs):
        if self._state.adding:
            # Get the models we need
            TimeEntry = apps.get_model('workflow', 'TimeEntry')
            MaterialEntry = apps.get_model('workflow', 'MaterialEntry')
            AdjustmentEntry = apps.get_model('workflow', 'AdjustmentEntry')

            self.revision_number = 1

            # Save first so we have a primary key
            super().save(*args, **kwargs)

            # Create default entries
            TimeEntry.objects.create(
                job_pricing=self,
                wage_rate=Decimal('32.00'),
                charge_out_rate=Decimal('105.00')
            )

            MaterialEntry.objects.create(
                job_pricing=self
            )

            AdjustmentEntry.objects.create(
                job_pricing=self
            )
        else:
            # Normal save for existing instances
            super().save(*args, **kwargs)

    @property
    def related_job(self):
        """Get the associated job through reverse relationships."""
        Job = apps.get_model('workflow', 'Job')
        return (Job.objects.filter(latest_estimate_pricing=self).first() or
                Job.objects.filter(latest_quote_pricing=self).first() or
                Job.objects.filter(latest_reality_pricing=self).first())

    def display_entries(self):
        """This is like a long form of __str___ - it gives a full list of all time/materials/adjustments."""
        time_entries = self.time_entries.all()
        material_entries = self.material_entries.all()
        adjustment_entries = self.adjustment_entries.all()

        logger.debug(f"\nEntries for JobPricing {self.id} ({self.pricing_stage}):")
        logger.debug("\nTime Entries:")
        for entry in time_entries:
            logger.debug(f"- {entry.description}: {entry.items} items, {entry.mins_per_item} mins/item")

        logger.debug("\nMaterial Entries:")
        for entry in material_entries:
            logger.debug(f"- {entry.description}: {entry.quantity} @ {entry.unit_cost}/{entry.unit_revenue}")

        logger.debug("\nAdjustment Entries:")
        for entry in adjustment_entries:
            logger.debug(f"- {entry.description}: cost {entry.cost_adjustment}, price {entry.price_adjustment}")

    def __str__(self):
        # Only bother displaying revision if there is one
        if self.revision_number > 1:
            revision_str = f" - Revision {self.revision_number}"
        else:
            revision_str = ""

        job = self.related_job
        job_name = job.name if job else "No Job"
        job_name_str = f"{job_name} - {self.get_pricing_stage_display()} ({self.get_pricing_type_display()}){revision_str}"
        return job_name_str




# Not implemented yet - just putting this here to add in future design thinking
def snapshot_and_add_time_entry(job_pricing, hours_worked):
    from workflow.models import (
        TimeEntry,
        MaterialEntry,
        AdjustmentEntry,
    )  # Import the necessary models to avoid ciruclar

    # Create a snapshot of the current JobPricing before modifying it
    snapshot_pricing = JobPricing.objects.create(
        job=job_pricing.job,
        pricing_stage=job_pricing.pricing_stage,
        pricing_type=job_pricing.pricing_type,
        created_at=job_pricing.created_at,
        updated_at=job_pricing.updated_at,
    )

    # Copy related time entries to the snapshot
    for time_entry in job_pricing.time_entries.all():
        TimeEntry.objects.create(
            job_pricing=snapshot_pricing, hours_worked=time_entry.hours_worked
        )

    # Copy related materials and adjustments if necessary
    for material_entry in job_pricing.material_entries.all():
        MaterialEntry.objects.create(
            job_pricing=snapshot_pricing,
            material=material_entry.material,
            quantity=material_entry.quantity,
        )

    for adjustment_entry in job_pricing.adjustment_entries.all():
        AdjustmentEntry.objects.create(
            job_pricing=snapshot_pricing,
            description=adjustment_entry.description,
            amount=adjustment_entry.amount,
        )

    # Now, add the new time entry to the current (updated) JobPricing
    TimeEntry.objects.create(job_pricing=job_pricing, hours_worked=hours_worked)

    return snapshot_pricing  # Return the snapshot to track it if needed


class QuotePricing(JobPricing):
    quote_is_finished = models.BooleanField(default=False)  # Locks the quote when true
    date_quote_submitted = models.DateField(
        null=True, blank=True
    )  # Date the quote was submitted to client
    quote_number = models.IntegerField(
        null=False, blank=False, unique=True
    )  # For Quote #123

    @staticmethod
    def generate_unique_quote_number():
        with transaction.atomic():
            last_pricing = (
                JobPricing.objects.select_for_update().order_by("-quote_number").first()
            )
            if last_pricing and last_pricing.quote_number:
                return last_pricing.quote_number + 1
            return 1  # Start numbering from 1 if there are no existing records
