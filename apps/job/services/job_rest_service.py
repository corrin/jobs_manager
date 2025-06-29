"""
Job REST Service Layer

Following SRP (Single Responsibility Principle) and clean code guidelines.
All business logic for Job REST operations should be implemented here.
"""

import logging
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.models import Staff
from apps.client.models import Client, ClientContact
from apps.job.enums import JobPricingStage
from apps.job.models import Job, JobEvent
from apps.job.serializers import JobPricingSerializer, JobSerializer
from apps.job.services.job_service import get_job_with_pricings

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
        optional_fields = ["description", "order_number", "notes", "contact_person"]
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
            Dict with job and pricing data
        """
        job = get_job_with_pricings(job_id)
        # Serialise main data
        job_data = JobSerializer(job, context={"request": request}).data
        # Fetch latest pricings
        latest_pricings = {
            "estimate": job.latest_estimate_pricing,
            "quote": job.latest_quote_pricing,
            "reality": job.latest_reality_pricing,
        }
        # Serialise pricings
        latest_pricings_data = {}
        for stage, pricing in latest_pricings.items():
            if pricing:
                latest_pricings_data[stage] = JobPricingSerializer(pricing).data
            else:
                latest_pricings_data[stage] = None
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
            "latest_pricings": latest_pricings_data,
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
            "pricing_methodology": job.pricing_methodology,
            "client_id": job.client_id,
            "charge_out_rate": job.charge_out_rate,
            "order_number": job.order_number,
            "notes": job.notes,
            "contact_person": job.contact_person,
            "contact_email": job.contact_email,
            "contact_phone": job.contact_phone,
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

        # Guard clause - check if can delete
        reality_pricing = job.pricings.filter(
            pricing_stage=JobPricingStage.REALITY, is_historical=False
        ).first()

        if reality_pricing and (
            reality_pricing.total_revenue > 0 or reality_pricing.total_cost > 0
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
                    "reason": "Cannot disable complex mode with multiple pricing entries",
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
            "pricing_methodology": "Pricing method",
            "client_id": "Client",
            "charge_out_rate": "Charge out rate",
            "order_number": "Order number",
            "notes": "Notes",
            "contact_person": "Contact person",
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
            elif field == "pricing_methodology":
                changes.append(
                    JobRestService._format_pricing_method_change(
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
    def _format_pricing_method_change(
        label: str, old_value: str, new_value: str
    ) -> str:
        """Formats pricing methodology change."""
        method_labels = {
            "time_materials": "Time & Materials",
            "fixed_price": "Fixed Price",
        }

        old_label = method_labels.get(old_value, old_value.replace("_", " ").title())
        new_label = method_labels.get(new_value, new_value.replace("_", " ").title())

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

    @staticmethod
    def create_time_entry(
        job_id: UUID, entry_data: Dict[str, Any], user: Staff
    ) -> Dict[str, Any]:
        """
        Creates a new time entry for a Job.

        Args:
            job_id: Job UUID
            entry_data: Time entry data
            user: User creating the entry

        Returns:
            Dict with operation result and updated job data
        """
        job = get_object_or_404(Job, id=job_id)

        # Guard clause - ensure estimate pricing exists
        estimate_pricing = job.latest_estimate_pricing
        if not estimate_pricing:
            raise ValueError("Job must have estimate pricing to add time entries")

        # Import TimeEntry model here to avoid circular imports
        from apps.timesheet.models import TimeEntry

        # Validate required fields
        required_fields = ["description", "hours", "charge_out_rate"]
        for field in required_fields:
            if field not in entry_data:
                raise ValueError(f"{field} is required")
        # Create time entry
        time_entry_data = {
            "job_pricing": estimate_pricing,
            "description": entry_data["description"],
            "hours": Decimal(str(entry_data["hours"])),
            "charge_out_rate": Decimal(str(entry_data["charge_out_rate"])),
            "wage_rate": Decimal(str(entry_data.get("wage_rate", 0))),
            "staff": user,
            "items": entry_data.get("items", 1),
            "minutes_per_item": Decimal(
                str(entry_data.get("minutes_per_item", entry_data["hours"] * 60))
            ),
            "date": timezone.now().date(),  # Add current date
            "is_billable": entry_data.get("is_billable", True),  # Add billable flag
            "wage_rate_multiplier": Decimal(
                str(entry_data.get("wage_rate_multiplier", 1.0))
            ),  # Add rate multiplier
        }

        with transaction.atomic():
            time_entry = TimeEntry.objects.create(**time_entry_data)
            # Log the event
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type="entry_added",
                description=f"Time entry added: {entry_data['description']}",
            )

        # Return minimal success response instead of full job data to avoid request dependency
        return {
            "success": True,
            "job_id": str(job_id),
            "time_entry_id": str(time_entry.id),
        }

    @staticmethod
    def create_material_entry(
        job_id: UUID, entry_data: Dict[str, Any], user: Staff
    ) -> Dict[str, Any]:
        """
        Creates a new material entry for a Job.

        Args:
            job_id: Job UUID
            entry_data: Material entry data
            user: User creating the entry

        Returns:
            Dict with operation result and updated job data
        """
        job = get_object_or_404(Job, id=job_id)

        # Guard clause - ensure estimate pricing exists
        estimate_pricing = job.latest_estimate_pricing
        if not estimate_pricing:
            raise ValueError("Job must have estimate pricing to add material entries")

        # Import MaterialEntry model here to avoid circular imports
        from apps.job.models import MaterialEntry

        # Validate required fields
        required_fields = ["description", "quantity", "unit_cost"]
        for field in required_fields:
            if field not in entry_data:
                raise ValueError(f"{field} is required")

        # Calculate unit_revenue if not provided
        unit_cost = Decimal(str(entry_data["unit_cost"]))
        unit_revenue = Decimal(str(entry_data.get("unit_revenue", unit_cost)))

        # Create material entry
        material_entry_data = {
            "job_pricing": estimate_pricing,
            "description": entry_data["description"],
            "quantity": Decimal(str(entry_data["quantity"])),
            "unit_cost": unit_cost,
            "unit_revenue": unit_revenue,
        }

        with transaction.atomic():
            material_entry = MaterialEntry.objects.create(**material_entry_data)
            # Log the event
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type="entry_added",
                description=f"Material entry added: {entry_data['description']}",
            )

        # Return minimal success response
        return {
            "success": True,
            "job_id": str(job_id),
            "material_entry_id": str(material_entry.id),
        }

    @staticmethod
    def create_adjustment_entry(
        job_id: UUID, entry_data: Dict[str, Any], user: Staff
    ) -> Dict[str, Any]:
        """
        Creates a new adjustment entry for a Job.

        Args:
            job_id: Job UUID
            entry_data: Adjustment entry data
            user: User creating the entry

        Returns:
            Dict with operation result and updated job data
        """
        job = get_object_or_404(Job, id=job_id)

        # Guard clause - ensure estimate pricing exists
        estimate_pricing = job.latest_estimate_pricing
        if not estimate_pricing:
            raise ValueError("Job must have estimate pricing to add adjustment entries")

        # Import AdjustmentEntry model here to avoid circular imports
        from apps.job.models import AdjustmentEntry

        # Validate required fields
        required_fields = ["description", "amount"]
        for field in required_fields:
            if field not in entry_data:
                raise ValueError(f"{field} is required")

        # Create adjustment entry
        adjustment_entry_data = {
            "job_pricing": estimate_pricing,
            "description": entry_data["description"],
            "cost_adjustment": Decimal(str(entry_data["amount"])),
            "revenue_adjustment": Decimal(str(entry_data["amount"])),
        }

        with transaction.atomic():
            adjustment_entry = AdjustmentEntry.objects.create(**adjustment_entry_data)
            # Log the event
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type="entry_added",
                description=f"Adjustment entry added: {entry_data['description']}",
            )

        # Return minimal success response
        return {
            "success": True,
            "job_id": str(job_id),
            "adjustment_entry_id": str(adjustment_entry.id),
        }
