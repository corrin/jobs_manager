import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from django.db import models, transaction
from django.db.models import Index, Max
from simple_history.models import HistoricalRecords

from apps.accounts.models import Staff
from apps.job.helpers import get_company_defaults

# We say . rather than job.models to avoid going through init,
# otherwise it would have a circular import
from .job_event import JobEvent

if TYPE_CHECKING:
    from .costing import CostSet

logger = logging.getLogger(__name__)


class Job(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=False, blank=False)
    JOB_STATUS_CHOICES: List[tuple[str, str]] = [
        # Main kanban columns (visible)
        ("draft", "Draft"),
        ("awaiting_approval", "Awaiting Approval"),
        ("approved", "Approved"),
        ("in_progress", "In Progress"),
        ("unusual", "Unusual"),
        ("recently_completed", "Recently Completed"),
        # Hidden statuses (maintained but not shown on kanban)
        ("special", "Special"),
        ("archived", "Archived"),
        # Legacy statuses for migration compatibility - remove after migration is complete
        ("quoting", "Quoting"),
        ("accepted_quote", "Accepted Quote"),
        ("awaiting_materials", "Awaiting Materials"),
        ("awaiting_staff", "Awaiting Staff"),
        ("awaiting_site_availability", "Awaiting Site Availability"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ]

    STATUS_TOOLTIPS: Dict[str, str] = {
        # Main kanban statuses
        "draft": "Initial job creation - quote being prepared",
        "awaiting_approval": "Quote submitted and waiting for customer approval",
        "approved": "Quote approved and ready to start work",
        "in_progress": "Work has started on this job",
        "unusual": "Jobs requiring special attention - on hold, waiting for materials/staff/site",
        "recently_completed": "Work has just finished on this job (including rejected jobs)",
        # Hidden statuses
        "special": "Shop jobs, upcoming shutdowns, etc. (not visible on kanban without advanced search)",
        "archived": "The job has been paid for and picked up",
        # Legacy tooltips for migration compatibility - remove after migration is complete
        "quoting": "The quote is currently being prepared (legacy - will become draft)",
        "accepted_quote": "The quote has been approved (legacy - will become approved)",
        "awaiting_materials": "Job is ready to start but waiting for materials (legacy - will become unusual)",
        "awaiting_staff": "Job is waiting for available staff (legacy - will become unusual)",
        "awaiting_site_availability": "Job is waiting for site access (legacy - will become unusual)",
        "on_hold": "The job is on hold for other reasons (legacy - will become unusual)",
        "completed": "Work finished and job is completed (legacy - will become recently_completed)",
        "rejected": "The quote was declined (legacy - will become recently_completed with rejected_flag=True)",
    }

    client = models.ForeignKey(
        "client.Client",
        on_delete=models.SET_NULL,  # Option to handle if a client is deleted
        null=True,
        related_name="jobs",  # Allows reverse lookup of jobs for a client
    )
    order_number = models.CharField(max_length=100, null=True, blank=True)

    # New relationship to ClientContact
    contact = models.ForeignKey(
        "client.ClientContact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        help_text="The contact person for this job",
    )
    job_number = models.IntegerField(unique=True)  # Job 1234
    description = models.TextField(
        blank=True,
        null=True,
        help_text="This becomes the first line item on the invoice",
    )

    quote_acceptance_date: datetime = models.DateTimeField(
        null=True,
        blank=True,
    )
    delivery_date = models.DateField(null=True, blank=True)
    status: str = models.CharField(
        max_length=30, choices=JOB_STATUS_CHOICES, default="draft"
    )  # type: ignore

    # Flag to track jobs that were rejected (displayed in Recently Completed with different styling)
    rejected_flag = models.BooleanField(
        default=False,
        help_text="Indicates if this job was rejected (shown in Recently Completed with rejected styling)",
    )  # type: ignore

    PRICING_METHODOLOGY_CHOICES = [
        ("time_materials", "Time & Materials"),
        ("fixed_price", "Fixed Price"),
    ]

    pricing_methodology = models.CharField(
        max_length=20,
        choices=PRICING_METHODOLOGY_CHOICES,
        default="time_materials",
        help_text=(
            "Determines whether job uses quotes or time and materials pricing type."
        ),
    )

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

    job_is_valid = models.BooleanField(default=False)
    collected: bool = models.BooleanField(default=False)
    paid: bool = models.BooleanField(default=False)
    charge_out_rate = (
        models.DecimalField(  # TODO: This needs to be added to the edit job form
            max_digits=10,
            decimal_places=2,
            null=False,  # Not nullable because save() ensures a value
            blank=False,  # Should be required in forms too
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history: HistoricalRecords = HistoricalRecords(table_name="workflow_historicaljob")

    complex_job = models.BooleanField(default=False)

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes about the job. Not shown on the invoice.",
    )

    created_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True)

    people = models.ManyToManyField(Staff, related_name="assigned_jobs")

    # Latest cost set snapshots for linking to current estimates/quotes/actuals
    latest_estimate = models.OneToOneField(
        "CostSet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Latest estimate cost set snapshot",
    )

    latest_quote = models.OneToOneField(
        "CostSet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Latest quote cost set snapshot",
    )

    latest_actual = models.OneToOneField(
        "CostSet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Latest actual cost set snapshot",
    )

    PRIORITY_INCREMENT = 200

    priority = models.FloatField(
        default=0.0,
        help_text="Priority of the job, higher numbers are higher priority.",
    )

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        ordering = ["job_number"]
        db_table = "workflow_job"
        indexes = [
            Index(fields=["status", "priority"], name="job_priority_status_idx"),
        ]

    @classmethod
    def _calculate_next_priority_for_status(cls, status_value: str) -> float:
        max_entry = (
            cls.objects.filter(status=status_value).aggregate(Max("priority"))[
                "priority__max"
            ]
            or 0.0
        )
        return max_entry + cls.PRIORITY_INCREMENT

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
        status_display = self.get_status_display()
        return f"[Job {self.job_number}] {self.name} ({status_display})"

    def get_latest(self, kind: str) -> Optional["CostSet"]:
        """
        Returns the respective CostSet or None.

        Args:
            kind: 'estimate', 'quote' or 'actual'

        Returns:
            CostSet instance or None
        """
        field_mapping = {
            "estimate": "latest_estimate",
            "quote": "latest_quote",
            "actual": "latest_actual",
        }

        if kind not in field_mapping:
            raise ValueError(
                f"Invalid kind '{kind}'. Must be one of: {list(field_mapping.keys())}"
            )

        return getattr(self, field_mapping[kind], None)

    def set_latest(self, kind: str, cost_set: "CostSet") -> None:
        """
        Updates pointer and saves.

        Args:
            kind: 'estimate', 'quote' or 'actual'
            cost_set: CostSet instance to set as latest
        """
        field_mapping = {
            "estimate": "latest_estimate",
            "quote": "latest_quote",
            "actual": "latest_actual",
        }

        if kind not in field_mapping:
            raise ValueError(
                f"Invalid kind '{kind}'. Must be one of: {list(field_mapping.keys())}"
            )

        # Validate that the cost_set belongs to this job and is of the correct kind
        if cost_set.job != self:
            raise ValueError("CostSet must belong to this job")

        if cost_set.kind != kind:
            raise ValueError(
                f"CostSet kind '{cost_set.kind}' does not match requested kind '{kind}'"
            )

        setattr(self, field_mapping[kind], cost_set)
        self.save(update_fields=[field_mapping[kind]])

    @property
    def job_display_name(self) -> str:
        """
        Returns a formatted display name for the job including client name.
        Format: job_number - (first 12 chars of client name), job_name
        """
        client_name = self.client.name[:12] if self.client else "No Client"
        return f"{self.job_number} - {client_name}, {self.name}"

    def generate_job_number(self) -> int:
        from apps.workflow.models import CompanyDefaults

        company_defaults: CompanyDefaults = get_company_defaults()
        starting_number: int = company_defaults.starting_job_number
        highest_job: int = (
            Job.objects.all().aggregate(Max("job_number"))["job_number__max"] or 0
        )
        next_job_number = max(starting_number, highest_job + 1)
        return next_job_number

    def save(self, *args, **kwargs):
        from apps.workflow.models import CompanyDefaults

        staff = kwargs.pop("staff", None)

        is_new = self._state.adding
        original_status = None if is_new else Job.objects.get(pk=self.pk).status

        create_creation_event = False
        if (staff and is_new) or (not self.created_by and staff):
            create_creation_event = True
            self.created_by = staff

        if self.charge_out_rate is None:
            company_defaults = CompanyDefaults.objects.first()
            self.charge_out_rate = company_defaults.charge_out_rate

        if is_new:
            # Ensure job_number is generated for new instances before saving
            self.job_number = self.generate_job_number()
            if not self.job_number:
                logger.error("Failed to generate a job number. Cannot save job.")
                raise ValueError("Job number generation failed.")
            logger.debug(f"Saving new job with job number: {self.job_number}")

            # To assure all jobs have a priority
            with transaction.atomic():
                default_priority = self._calculate_next_priority_for_status(self.status)
                self.priority = default_priority

                # Save the job first
                super(Job, self).save(*args, **kwargs)

                # Create initial CostSet instances (modern system)
                logger.debug("Creating initial CostSet entries.")
                from .costing import CostSet

                # Create estimate cost set
                estimate_cost_set = CostSet.objects.create(
                    job=self, kind="estimate", rev=1
                )
                self.latest_estimate = estimate_cost_set

                # Create quote cost set
                quote_cost_set = CostSet.objects.create(job=self, kind="quote", rev=1)
                self.latest_quote = quote_cost_set

                # Create actual cost set
                actual_cost_set = CostSet.objects.create(job=self, kind="actual", rev=1)
                self.latest_actual = actual_cost_set

                logger.debug("Initial CostSets created successfully.")

                # Save the references back to the DB
                super(Job, self).save(
                    update_fields=[
                        "latest_estimate",
                        "latest_quote",
                        "latest_actual",
                    ]
                )

                if create_creation_event and staff:
                    JobEvent.objects.create(
                        job=self,
                        event_type="job_created",
                        description="New job created",
                        staff=staff,
                    )

        else:
            if original_status != self.status and staff:
                super(Job, self).save(*args, **kwargs)

                JobEvent.objects.create(
                    job=self,
                    event_type="status_changed",
                    description=(
                        f"Status changed from "
                        f"{original_status.replace('_', ' ').title()} "
                        f"to {self.status.replace('_', ' ').title()}"
                    ),
                    staff=staff,
                )

                return

            # Step 5: Save the Job to persist everything, including relationships
            super(Job, self).save(*args, **kwargs)
