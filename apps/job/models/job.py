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
    ]

    STATUS_TOOLTIPS: Dict[str, str] = {
        # Main kanban statuses
        "draft": "Initial job creation - quote being prepared",
        "awaiting_approval": "Quote submitted and waiting for customer approval",
        "approved": "Quote approved and ready to start work",
        "in_progress": "Work has started on this job",
        "unusual": "Jobs requiring special attention - on hold, waiting for materials/staff/site",  # noqa: E501
        "recently_completed": "Work has just finished on this job (including rejected jobs)",  # noqa: E501
        # Hidden statuses
        "special": "Shop jobs, upcoming shutdowns, etc. (not visible on kanban without advanced search)",  # noqa: E501
        "archived": "The job has been paid for and picked up",
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

    # Flag to track jobs that were rejected
    rejected_flag = models.BooleanField(
        default=False,
        help_text="Indicates if this job was rejected (shown in Recently Completed with rejected styling)",  # noqa: E501
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
        original_job = None

        # Track original values for change detection
        if not is_new:
            original_job = Job.objects.get(pk=self.pk)
            original_job.status

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
                    client_name = self.client.name if self.client else "Shop Job"
                    contact_info = (
                        f" (Contact: {self.contact.name})" if self.contact else ""
                    )
                    JobEvent.objects.create(
                        job=self,
                        event_type="job_created",
                        description=f"New job '{self.name}' created for client {client_name}{contact_info}."  # noqa: E501
                        f" Initial status: {self.get_status_display()}."
                        f" Pricing methodology: {self.get_pricing_methodology_display()}.",  # noqa: E501
                        staff=staff,
                    )

        else:
            # Dynamic change detection for existing jobs
            if staff:
                self._create_change_events(original_job, staff)

            # Save the job first
            super(Job, self).save(*args, **kwargs)

    def _create_change_events(self, original_job, staff):
        """
        Dynamically detect field changes and create appropriate events.
        """
        # Store staff for use in handlers
        self._current_staff = staff

        # Field mapping: field_name -> description_generator_function
        field_handlers = {
            "status": self._handle_status_change,
            "name": lambda old, new: (
                "job_updated",
                f"Job name changed from '{old}' to '{new}'",
            ),
            "client_id": self._handle_client_change,
            "contact_id": self._handle_contact_change,
            "order_number": lambda old, new: (
                "job_updated",
                f"Order number changed from '{old or 'None'}' to '{new or 'None'}'",
            ),
            "description": self._handle_text_field_change(
                "Job description", "job_updated"
            ),
            "notes": self._handle_text_field_change("Internal notes", "notes_updated"),
            "delivery_date": self._handle_date_change(
                "delivery_date_changed", "Delivery date"
            ),
            "quote_acceptance_date": self._handle_quote_acceptance_change,
            "pricing_methodology": self._handle_pricing_methodology_change,
            "charge_out_rate": lambda old, new: (
                "pricing_changed",
                f"Charge out rate changed from ${old}/hour to ${new}/hour",
            ),
            "priority": lambda old, new: (
                "priority_changed",
                f"Job priority changed from {old} to {new}. This affects the job's position in the workflow queue",  # noqa: E501
            ),
            "paid": self._handle_boolean_change(
                "payment_received",
                "payment_updated",
                "Job marked as PAID. Payment has been received from client",
                "Job payment status changed to UNPAID",
            ),
            "collected": self._handle_boolean_change(
                "job_collected",
                "collection_updated",
                "Job marked as COLLECTED. Work has been picked up by client",
                "Job collection status changed to NOT COLLECTED",
            ),
            "complex_job": self._handle_boolean_change(
                "job_updated",
                "job_updated",
                "Job marked as COMPLEX JOB. This job requires special attention or has complex requirements",  # noqa: E501
                "Job no longer marked as complex job",
            ),
        }

        for field_name, handler in field_handlers.items():
            old_value = getattr(original_job, field_name)
            new_value = getattr(self, field_name)

            if old_value != new_value:
                if callable(handler):
                    result = handler(old_value, new_value)
                    if result:  # Handler can return None to skip event creation
                        event_type, description = result
                        JobEvent.objects.create(
                            job=self,
                            event_type=event_type,
                            description=description,
                            staff=staff,
                        )

    def _handle_status_change(self, old_status, new_status):
        """Handle status change with special logic for rejected jobs."""
        old_display = dict(self.JOB_STATUS_CHOICES).get(old_status, old_status)
        new_display = dict(self.JOB_STATUS_CHOICES).get(new_status, new_status)

        # Create status change event
        JobEvent.objects.create(
            job=self,
            event_type="status_changed",
            description=f"Status changed from '{old_display}' to '{new_display}'. Job moved to new workflow stage.",  # noqa: E501
            staff=self._current_staff,
        )

        # Special handling for rejected jobs
        if (
            new_status == "recently_completed"
            and hasattr(self, "rejected_flag")
            and self.rejected_flag
        ):
            JobEvent.objects.create(
                job=self,
                event_type="job_rejected",
                description="Job marked as rejected. Quote was declined by client.",
                staff=self._current_staff,
            )

        return None  # Already handled, don't create another event

    def _handle_client_change(self, old_client_id, new_client_id):
        """Handle client change with proper name resolution."""
        old_client = "Shop Job"
        new_client = "Shop Job"

        if old_client_id:
            try:
                from apps.client.models import Client

                old_client = Client.objects.get(id=old_client_id).name
            except Exception:
                old_client = "Unknown Client"

        if new_client_id:
            new_client = self.client.name if self.client else "Unknown Client"

        return (
            "client_changed",
            f"Client changed from '{old_client}' to '{new_client}'",
        )

    def _handle_contact_change(self, old_contact_id, new_contact_id):
        """Handle contact change with proper name resolution."""
        old_contact = "None"
        new_contact = "None"

        if old_contact_id:
            try:
                from apps.client.models import ClientContact

                old_contact = ClientContact.objects.get(id=old_contact_id).name
            except Exception:
                old_contact = "Unknown Contact"

        if new_contact_id:
            new_contact = self.contact.name if self.contact else "Unknown Contact"

        return (
            "contact_changed",
            f"Primary contact changed from '{old_contact}' to '{new_contact}'",
        )

    def _handle_text_field_change(self, field_display_name, event_type):
        """Factory function for handling text field changes."""

        def handler(old_value, new_value):
            if old_value and new_value:
                truncated = (
                    (old_value[:50] + "...") if len(old_value) > 50 else old_value
                )
                return (
                    event_type,
                    f"{field_display_name} updated. Previous content: '{truncated}'",
                )
            elif not old_value and new_value:
                truncated = (
                    (new_value[:100] + "...") if len(new_value) > 100 else new_value
                )
                return (event_type, f"{field_display_name} added: '{truncated}'")
            elif old_value and not new_value:
                truncated = (
                    (old_value[:50] + "...") if len(old_value) > 50 else old_value
                )
                return (
                    event_type,
                    f"{field_display_name} removed. Previous content: '{truncated}'",
                )
            return None

        return handler

    def _handle_date_change(self, event_type, field_display_name):
        """Factory function for handling date field changes."""

        def handler(old_date, new_date):
            old_str = old_date.strftime("%Y-%m-%d") if old_date else "None"
            new_str = new_date.strftime("%Y-%m-%d") if new_date else "None"
            return (
                event_type,
                f"{field_display_name} changed from '{old_str}' to '{new_str}'",
            )

        return handler

    def _handle_quote_acceptance_change(self, old_date, new_date):
        """Handle quote acceptance date with special logic."""
        if not old_date and new_date:
            return (
                "quote_accepted",
                f"Quote accepted by client on {new_date.strftime('%Y-%m-%d at %H:%M')}",
            )
        elif old_date and not new_date:
            return (
                "job_updated",
                f"Quote acceptance date removed. Was previously accepted on {old_date.strftime('%Y-%m-%d')}",  # noqa: E501
            )
        return None

    def _handle_pricing_methodology_change(self, old_method, new_method):
        """Handle pricing methodology change with display names."""
        old_display = dict(self.PRICING_METHODOLOGY_CHOICES).get(old_method, old_method)
        new_display = dict(self.PRICING_METHODOLOGY_CHOICES).get(new_method, new_method)
        return (
            "pricing_changed",
            f"Pricing methodology changed from '{old_display}' to '{new_display}'",
        )

    def _handle_boolean_change(self, true_event, false_event, true_desc, false_desc):
        """Factory function for handling boolean field changes."""

        def handler(old_value, new_value):
            if new_value and not old_value:
                return (true_event, true_desc)
            elif old_value and not new_value:
                return (false_event, false_desc)
            return None

        return handler
