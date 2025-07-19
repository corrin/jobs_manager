"""
Job REST Service Layer

Following SRP (Single Responsibility Principle) and clean code guidelines.
All business logic for Job REST operations should be implemented here.
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict
from uuid import UUID

from django.db import models, transaction
from django.db.models.expressions import RawSQL
from django.shortcuts import get_object_or_404

from apps.accounts.models import Staff
from apps.client.models import Client, ClientContact
from apps.job.models import CostSet, Job, JobEvent
from apps.job.models.costing import CostLine
from apps.job.serializers import JobSerializer

logger = logging.getLogger(__name__)


class JobRestService:
    """
    Service layer for Job REST operations.
    Implements all business rules related to Job manipulation via REST API.
    """

    @staticmethod
    def create_job(data: Dict[str, Any], user: Staff) -> Job:
        """
        Creates a new Job with essential data.
        Applies early return for validations.

        Args:
            data: Form creation data
            user: User creating the job

        Returns:
            Job: Created job instance

        Raises:
            ValueError: If required data is missing
        """
        # Guard clauses - early return for validations
        if not data.get("name"):
            raise ValueError("Job name is required")

        if not data.get("client_id"):
            raise ValueError("Client is required")

        try:
            client = Client.objects.get(id=data["client_id"])
        except Client.DoesNotExist:
            raise ValueError("Client not found")

        job_data = {
            "name": data["name"],
            "client": client,
            "created_by": user,
        }

        # Optional fields - only if provided
        optional_fields = ["description", "order_number", "notes"]
        for field in optional_fields:
            if data.get(field):
                job_data[field] = data[field]

        # Contact (optional relationship)
        if data.get("contact_id"):
            try:
                contact = ClientContact.objects.get(id=data["contact_id"])
                job_data["contact"] = contact
            except ClientContact.DoesNotExist:
                logger.warning(f"Contact {data['contact_id']} not found, ignoring")

        with transaction.atomic():
            job = Job(**job_data)
            job.save(staff=user)
            # Log creation
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type="job_created",
                description="New job created",
            )

        return job

    @staticmethod
    def get_job_for_edit(job_id: UUID, request) -> Dict[str, Any]:
        """
        Fetches complete Job data for editing.

        Args:
            job_id: Job UUID

        Returns:
            Dict with job data (pricing data removed - use CostSet endpoints)
        """
        job = Job.objects.select_related("client").get(id=job_id)

        # Serialise main data
        job_data = JobSerializer(job, context={"request": request}).data

        # instead of embedding pricing data here

        # Fetch job events
        events = JobEvent.objects.filter(job=job).order_by("-timestamp")[:10]
        events_data = [
            {
                "id": str(event.id),
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "description": event.description,
                "staff": (
                    event.staff.get_display_full_name() if event.staff else "System"
                ),
            }
            for event in events
        ]
        company_defaults = JobRestService._get_company_defaults()
        return {
            "job": job_data,
            "events": events_data,
            "company_defaults": company_defaults,
        }

    @staticmethod
    def update_job(job_id: UUID, data: Dict[str, Any], user: Staff) -> Job:
        """
        Updates an existing Job.

        Args:
            job_id: Job UUID
            data: Data for updating
            user: User performing the update

        Returns:
            Job: Updated instance
        """
        job = get_object_or_404(Job, id=job_id)
        # Store original values for comparison
        original_values = {
            "name": job.name,
            "description": job.description,
            "status": job.status,
            "priority": job.priority,
            "client_id": job.client_id,
            "charge_out_rate": job.charge_out_rate,
            "order_number": job.order_number,
            "notes": job.notes,
            "contact_id": job.contact.id if job.contact else None,
            "contact_name": job.contact.name if job.contact else None,
            "contact_email": job.contact.email if job.contact else None,
            "contact_phone": job.contact.phone if job.contact else None,
        }

        # Use serialiser for validation and updating
        serializer = JobSerializer(
            instance=job,
            data=data,
            partial=True,
            context={"request": type("MockRequest", (), {"user": user})()},
        )

        if not serializer.is_valid():
            raise ValueError(f"Invalid data: {serializer.errors}")

        with transaction.atomic():
            job = serializer.save(staff=user)
            # Generate descriptive update message
            description = JobRestService._generate_update_description(
                original_values, serializer.validated_data
            )

            # Log the update with descriptive message
            JobEvent.objects.create(
                job=job, staff=user, event_type="job_updated", description=description
            )

        return job

    @staticmethod
    def toggle_complex_job(
        job_id: UUID, complex_job: bool, user: Staff
    ) -> Dict[str, Any]:
        """
        Toggles the complex_job mode of a Job.
        Implements specific validation rules.

        Args:
            job_id: Job UUID
            complex_job: New boolean value
            user: User making the change

        Returns:
            Dict with operation result
        """
        # Early return - type validation
        if not isinstance(complex_job, bool):
            raise ValueError("complex_job must be a boolean value")

        job = get_object_or_404(Job, id=job_id)

        # Guard clause - check if can disable complex mode
        if not complex_job and job.complex_job:
            validation_result = JobRestService._validate_can_disable_complex_mode(job)
            if not validation_result["can_disable"]:
                raise ValueError(validation_result["reason"])

        with transaction.atomic():
            job.complex_job = complex_job
            job.save()
            # Log the change
            mode_action = "enabled" if complex_job else "disabled"
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type="setting_changed",
                description=f"Itemised billing {mode_action}",
            )

        return {
            "success": True,
            "job_id": str(job_id),
            "complex_job": complex_job,
            "message": "Job updated successfully",
        }

    @staticmethod
    def add_job_event(job_id: UUID, description: str, user: Staff) -> Dict[str, Any]:
        """
        Adds a manual event to the Job.

        Args:
            job_id: Job UUID
            description: Event description
            user: User creating the event

        Returns:
            Dict with created event data
        """
        # Guard clause - input validation
        if not description or not description.strip():
            raise ValueError("Event description is required")

        job = get_object_or_404(Job, id=job_id)

        event = JobEvent.objects.create(
            job=job,
            staff=user,
            description=description.strip(),
            event_type="manual_note",
        )

        logger.info(f"Event {event.id} created for job {job_id} by {user.email}")

        return {
            "success": True,
            "event": {
                "id": str(event.id),
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "description": event.description,
                "staff": user.get_display_full_name() if user else "System",
            },
        }

    @staticmethod
    def delete_job(job_id: UUID, user: Staff) -> Dict[str, Any]:
        """
        Deletes a Job if allowed by business rules.

        Args:
            job_id: Job UUID
            user: User attempting to delete

        Returns:
            Dict with operation result
        """
        job = get_object_or_404(Job, id=job_id)

        actual_cost_set = job.latest_actual

        if actual_cost_set and (
            actual_cost_set.summary.get("cost", 0) > 0
            or actual_cost_set.summary.get("rev", 0) > 0
        ):
            raise ValueError(
                "Cannot delete this job because it has real costs or revenue."
            )

        job_name = job.name
        job_number = job.job_number
        with transaction.atomic():
            job.delete()

            logger.info(f"Job {job_number} '{job_name}' deleted by {user.email}")

        return {"success": True, "message": f"Job {job_number} deleted successfully"}

    @staticmethod
    def get_weekly_metrics(week: date = None) -> list[Dict[str, Any]]:
        """
        Fetches weekly metrics for all active jobs.

        Args:
            week: Optional date parameter (ignored for now, but can be used for calculations)

        Returns:
            List of dicts with weekly metrics data, including:
                - Job information
                - Estimated hours
                - Actual hours
                - Total profit
        """
        # NOTE: Previous time entries filter (commented out for future reference):
        # if week is None:
        #     week = date.today()
        # week_start = week - timedelta(days=week.weekday())
        # week_end = week_start + timedelta(days=6)
        # job_ids_with_time_entries = (
        #     CostLine.objects.annotate(
        #         date_meta=RawSQL(
        #             "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.date'))",
        #             (),
        #             output_field=models.CharField(),
        #         )
        #     )
        #     .filter(
        #         cost_set__kind="actual",
        #         kind="time",
        #         date_meta__gte=week_start.strftime('%Y-%m-%d'),
        #         date_meta__lte=week_end.strftime('%Y-%m-%d'),
        #     )
        #     .values_list('cost_set__job_id', flat=True)
        #     .distinct()
        # )
        # jobs = Job.objects.filter(id__in=job_ids_with_time_entries, ...)

        # Get all active jobs (including draft and recently completed), ordered by priority
        jobs = (
            Job.objects.filter(
                status__in=[
                    "awaiting_approval",
                    "approved",
                    "in_progress",
                    "unusual",
                    "draft",
                    "recently_completed",
                ]
            )
            .select_related("client")
            .prefetch_related("people")
            .order_by("-priority")
        )

        metrics = []
        for job in jobs:
            # Direct access to summary data
            estimated_hours = job.latest_estimate.summary["hours"]

            actual_hours = job.latest_actual.summary["hours"]
            actual_rev = job.latest_actual.summary["rev"]
            actual_cost = job.latest_actual.summary["cost"]

            profit = actual_rev - actual_cost

            job_metrics = {
                "job_id": str(job.id),
                "name": job.name,
                "job_number": job.job_number,
                "client": job.client,
                "description": job.description,
                "status": job.status,
                "people": [
                    {"name": person.get_display_full_name(), "id": str(person.id)}
                    for person in job.people.all()
                ],
                "estimated_hours": estimated_hours,
                "actual_hours": actual_hours,
                "profit": profit,
            }
            metrics.append(job_metrics)

        from pprint import pprint

        pprint(metrics)
        return metrics

    @staticmethod
    def _validate_can_disable_complex_mode(job: Job) -> Dict[str, Any]:
        """
        Validates if the job can have complex mode disabled.

        Args:
            job: Job instance

        Returns:
            Dict with validation result
        """
        for pricing in job.pricings.all():
            if not pricing:
                continue

            # Check if there are multiple entries
            if (
                pricing.time_entries.count() > 1
                or pricing.material_entries.count() > 1
                or pricing.adjustment_entries.count() > 1
            ):
                return {
                    "can_disable": False,
                    "reason": (
                        "Cannot disable complex mode with multiple pricing entries"
                    ),
                }

        return {"can_disable": True, "reason": ""}

    @staticmethod
    def _get_company_defaults() -> Dict[str, Any]:
        """
        Fetches company default settings.

        Returns:
            Dict with default settings
        """
        from apps.job.helpers import get_company_defaults

        defaults = get_company_defaults()
        return {
            "materials_markup": float(defaults.materials_markup),
            "time_markup": float(defaults.time_markup),
            "charge_out_rate": float(defaults.charge_out_rate),
            "wage_rate": float(defaults.wage_rate),
        }

    @staticmethod
    def _generate_update_description(
        original_values: Dict[str, Any], updated_data: Dict[str, Any]
    ) -> str:
        """
        Generates user-friendly description of job updates.
        Based on actual Job model fields.

        Args:
            original_values: Original field values before update
            updated_data: New data provided for update

        Returns:
            str: Human-readable description of changes
        """
        # Early return if no data to compare
        if not updated_data:
            return "Job details updated"

        changes = []

        # Field mappings based on actual Job model
        field_labels = {
            "name": "Job name",
            "description": "Description",
            "status": "Status",
            "priority": "Priority",
            "client_id": "Client",
            "charge_out_rate": "Charge out rate",
            "order_number": "Order number",
            "notes": "Notes",
            "contact_id": "Contact person",
            "contact_name": "Contact name",
            "contact_email": "Contact email",
            "contact_phone": "Contact phone",
            "complex_job": "Itemised billing",
            "delivery_date": "Delivery date",
            "quote_acceptance_date": "Quote acceptance date",
            "job_is_valid": "Job validity",
            "collected": "Collection status",
            "paid": "Payment status",
        }

        # Process each updated field
        for field, new_value in updated_data.items():
            # Guard clause - skip fields not in original values
            if field not in original_values:
                continue

            original_value = original_values[field]

            # Guard clause - skip unchanged values
            if original_value == new_value:
                continue

            label = field_labels.get(field, field.replace("_", " ").title())

            # Handle specific field types with switch-case pattern
            if field == "status":
                changes.append(
                    JobRestService._format_status_change(
                        label, original_value, new_value
                    )
                )
            elif field in ["charge_out_rate"]:
                changes.append(
                    JobRestService._format_currency_change(
                        label, original_value, new_value
                    )
                )
            elif field in ["complex_job", "job_is_valid", "collected", "paid"]:
                changes.append(
                    JobRestService._format_boolean_change(
                        label, original_value, new_value
                    )
                )
            else:
                changes.append(
                    JobRestService._format_generic_change(
                        label, original_value, new_value
                    )
                )

        # Return formatted result
        if changes:
            return ", ".join(changes)
        else:
            return "Job details updated"

    @staticmethod
    def _format_status_change(label: str, old_value: str, new_value: str) -> str:
        """Formats status change with proper labels."""
        # Status labels from Job model
        status_labels = {
            "quoting": "Quoting",
            "accepted_quote": "Accepted Quote",
            "awaiting_materials": "Awaiting Materials",
            "in_progress": "In Progress",
            "on_hold": "On Hold",
            "special": "Special",
            "completed": "Completed",
            "rejected": "Rejected",
            "archived": "Archived",
        }

        old_label = status_labels.get(old_value, old_value.replace("_", " ").title())
        new_label = status_labels.get(new_value, new_value.replace("_", " ").title())

        return f"{label} changed from {old_label} to {new_label}"

    @staticmethod
    def _format_currency_change(label: str, old_value: Any, new_value: Any) -> str:
        """Formats currency field changes."""
        if old_value and new_value:
            return f"{label} updated from ${old_value} to ${new_value}"
        elif new_value:
            return f"{label} set to ${new_value}"
        else:
            return f"{label} cleared"

    @staticmethod
    def _format_boolean_change(label: str, old_value: bool, new_value: bool) -> str:
        """Formats boolean field changes."""
        if new_value:
            return f"{label} enabled"
        else:
            return f"{label} disabled"

    @staticmethod
    def _format_generic_change(label: str, old_value: Any, new_value: Any) -> str:
        """Formats generic field changes."""
        if old_value and new_value:
            return f"{label} updated"
        elif new_value:
            return f"{label} added"
        else:
            return f"{label} removed"


# - create_time_entry() - Use CostLine creation with CostSet instead
# - create_material_entry() - Use CostLine creation with CostSet instead
# - create_adjustment_entry() - Use CostLine creation with CostSet instead
