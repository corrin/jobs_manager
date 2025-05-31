import logging
import uuid
from datetime import datetime
from typing import Dict, List

from django.db import models
from django.db.models import Max
from simple_history.models import HistoricalRecords  # type: ignore

from job.enums import JobPricingType, JobPricingMethodology
from job.helpers import get_company_defaults

# We say . rather than job.models to avoid going through init,
# otherwise it would have a circular import
from .job_event import JobEvent
from .job_pricing import JobPricing

from accounts.models import Staff


logger = logging.getLogger(__name__)


class Job(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    
    linked_quote = models.URLField(
        null=True,
        blank=True,
        help_text="URL to a linked Google Sheets quote"
    )

    JOB_STATUS_CHOICES: List[tuple[str, str]] = [
        ("quoting", "Quoting"),
        ("accepted_quote", "Accepted Quote"),
        ("awaiting_materials", "Awaiting Materials"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("special", "Special"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
        ("archived", "Archived"),
    ]

    STATUS_TOOLTIPS: Dict[str, str] = {
        "quoting": "The quote is currently being prepared.",
        "accepted_quote": "The quote has been approved, but work hasn't started yet.",
        "awaiting_materials": "Job is ready to start but waiting for materials.",
        "rejected": "The quote was declined.",
        "in_progress": "Work has started on this job.",
        "on_hold": "The job is on hold, possibly awaiting materials.",
        "special": "Shop jobs, upcoming shutdowns, etc.",
        "completed": "Work has finished on this job.",
        "archived": "The job has been paid for and picked up.",
    }

    client = models.ForeignKey(
        "workflow.Client",
        on_delete=models.SET_NULL,  # Option to handle if a client is deleted
        null=True,
        related_name="jobs",  # Allows reverse lookup of jobs for a client
    )
    order_number = models.CharField(
        max_length=100, null=True, blank=True
    )
    contact_person = models.CharField(
        max_length=100, null=True, blank=True
    )
    contact_email = models.EmailField(null=True, blank=True)  # New field for contact's email
    contact_phone = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )
    job_number = models.IntegerField(unique=True)  # Job 1234
    material_gauge_quantity = models.TextField(
        blank=True,
        null=True,
        help_text="DEPRECATED - Use notes field instead. Content will be automatically migrated.",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="This becomes the first line item on the invoice",
    )  # type: ignore

    quote_acceptance_date: datetime = models.DateTimeField(  # type: ignore
        null=True,
        blank=True,
    )
    delivery_date = models.DateField(null=True, blank=True)  # type: ignore
    status: str = models.CharField(
        max_length=30, choices=JOB_STATUS_CHOICES, default="quoting"
    )  # type: ignore
    # Decided not to bother with parent for now since we don't have a hierarchy of jobs.
    # Can be restored.
    # Parent would provide an alternative to historical records for tracking changes.
    # parent: models.ForeignKey = models.ForeignKey(
    #     "self",
    #     null=True,
    #     blank=True,
    #     related_name="revisions",
    #     on_delete=models.SET_NULL,
    # )
    # Shop job has no client (client_id is None)

    job_is_valid = models.BooleanField(default=False)  # type: ignore
    collected: bool = models.BooleanField(default=False)  # type: ignore
    paid: bool = models.BooleanField(default=False)  # type: ignore
    charge_out_rate = (
        models.DecimalField(  # TODO: This needs to be added to the edit job form
            max_digits=10,
            decimal_places=2,
            null=False,  # Not nullable because save() ensures a value
            blank=False,  # Should be required in forms too
        )
    )

    pricing_methodology = models.CharField(
        max_length=20,
        choices=JobPricingMethodology.choices,
        default=JobPricingMethodology.TIME_AND_MATERIALS,
        help_text="Type of pricing for the job (fixed price or time and materials).",
    )

    # Direct relationships for estimate, quote, reality
    latest_estimate_pricing = models.OneToOneField(
        "JobPricing",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="latest_estimate_for_job",
    )

    latest_quote_pricing = models.OneToOneField(
        "JobPricing",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="latest_quote_for_job",
    )

    latest_reality_pricing = models.OneToOneField(
        "JobPricing",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="latest_reality_for_job",
    )

    archived_pricings = models.ManyToManyField(
        "JobPricing",
        related_name="archived_pricings_for_job",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history: HistoricalRecords = HistoricalRecords(table_name="workflow_historicaljob")

    complex_job = models.BooleanField(default=False)  # type: ignore

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes about the job. Not shown on the invoice.",
    )

    created_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True)

    people = models.ManyToManyField(Staff, related_name="assigned_jobs")

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        ordering = ["job_number"]
        db_table = "workflow_job"

    @property
    def shop_job(self) -> bool:
        """Indicates if this is a shop job (no client)."""
        return (
            str(self.client_id) == "00000000-0000-0000-0000-000000000001"
        )  # This is the UUID for the shop client

    @shop_job.setter
    def shop_job(self, value: bool) -> None:
        """Sets whether this is a shop job by updating the client ID."""
        if value:
            self.client_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        else:
            self.client_id = None

    @property
    def quoted(self) -> bool:
        if hasattr(self, "quote") and self.quote is not None:
            return self.quote
        return False

    @property
    def invoiced(self) -> bool:
        if hasattr(self, "invoice") and self.invoice is not None:
            return self.invoice
        return False

    def __str__(self) -> str:
        client_name = self.client.name if self.client else "No Client"
        job_name = self.name if self.name else "No Job Name"
        return f" {self.job_number} - {job_name} for {client_name}"

    def get_display_name(self) -> str:
        return f"Job: {self.job_number}"  # type: ignore
        
    @property
    def job_display_name(self) -> str:
        """
        Returns a formatted display name for the job including client name.
        Format: job_number - (first 12 chars of client name), job_name
        """
        client_name = self.client.name[:12] if self.client else "No Client"
        return f"{self.job_number} - {client_name}, {self.name}"
    
    def generate_job_number(self) -> int:
        from workflow.models import CompanyDefaults

        company_defaults: CompanyDefaults = get_company_defaults()
        starting_number: int = company_defaults.starting_job_number

        highest_job: int = Job.objects.all().aggregate(Max('job_number'))['job_number__max'] or 0
        
        return max(starting_number, highest_job + 1)

    def save(self, *args, **kwargs):
        from workflow.models import CompanyDefaults

        staff = kwargs.pop("staff", None)

        is_new = self._state.adding
        original_status = None if is_new else Job.objects.get(pk=self.pk).status

        create_creation_event = False
        if (staff and is_new) or (not self.created_by and staff):
            create_creation_event = True
            self.created_by = staff

        # Step 1: Check if this is a new instance (based on `self._state.adding`)
        if not self.job_number:
            self.job_number = self.generate_job_number()
            logger.debug(f"Saving job with job number: {self.job_number}")

        if self.charge_out_rate is None:
            company_defaults = CompanyDefaults.objects.first()
            self.charge_out_rate = company_defaults.charge_out_rate

        if is_new:
            # Creating a new job is tricky because of the circular reference.
            # We first save the job to the DB without any associated pricings, then we
            super(Job, self).save(*args, **kwargs)

            # Lazy import JobPricing using Django's apps.get_model()
            # We need to do this because of circular imports.  JobPricing imports Job

            #  Create the initial JobPricing instances
            logger.debug("Creating related JobPricing entries.")
            self.latest_estimate_pricing = JobPricing.objects.create(
                pricing_type="estimate", job=self
            )
            self.latest_quote_pricing = JobPricing.objects.create(
                pricing_type="quote", job=self
            )
            self.latest_reality_pricing = JobPricing.objects.create(
                pricing_type="reality", job=self
            )
            logger.debug("Initial pricings created successfully.")

            # Save the references back to the DB
            super(Job, self).save(
                update_fields=[
                    "latest_estimate_pricing",
                    "latest_quote_pricing",
                    "latest_reality_pricing",
                ]
            )

            if create_creation_event and staff:
                JobEvent.objects.create(
                    job=self,
                    event_type="created",
                    description=f"Job {self.name} created",
                    staff=staff,
                )

        else:
            if original_status != self.status and staff:
                super(Job, self).save(*args, **kwargs)

                JobEvent.objects.create(
                    job=self,
                    event_type="status_change",
                    description=(
                        f"Job status changed from {original_status} "
                        f"to {self.status}"
                    ),
                    staff=staff,
                )

                return

            # Step 5: Save the Job to persist everything, including relationships
            super(Job, self).save(*args, **kwargs)
