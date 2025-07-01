"""
Timesheet to CostLine Migration Service

Service to handle migration from legacy TimeEntry model to modern CostLine architecture.
This service creates CostLines in the "actual" CostSet for each timesheet entry.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction

from apps.accounts.models import Staff
from apps.job.models import CostLine, CostSet, Job
from apps.timesheet.models import TimeEntry

logger = logging.getLogger(__name__)


class TimesheetToCostLineService:
    """
    Service to convert TimeEntry records to CostLine records
    Following SRP and clean code principles
    """

    @classmethod
    def create_cost_line_from_timesheet(
        cls,
        job_id: str,
        staff_id: str,
        entry_date: date,
        hours: Decimal,
        description: str,
        wage_rate: Decimal,
        charge_out_rate: Decimal,
        rate_multiplier: Decimal = Decimal("1.0"),
        is_billable: bool = True,
        ext_refs: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> CostLine:
        """
        Create a CostLine from timesheet entry data

        Args:
            job_id: Job UUID
            staff_id: Staff UUID
            entry_date: Date of work
            hours: Hours worked
            description: Description of work
            wage_rate: Staff wage rate
            charge_out_rate: Client charge out rate
            rate_multiplier: Rate multiplier (overtime, etc.)
            is_billable: Whether the work is billable
            ext_refs: External references
            meta: Additional metadata

        Returns:
            Created CostLine instance
        """
        # Guard clause - validate description is not empty
        if not description or description.strip() == "":
            raise ValueError("Description cannot be empty for timesheet entries")

        with transaction.atomic():
            # Get job
            job = Job.objects.get(id=job_id)
            staff = Staff.objects.get(id=staff_id)

            # Get or create actual CostSet
            cost_set = cls._get_or_create_actual_cost_set(job)

            # Calculate costs
            actual_wage_rate = wage_rate * rate_multiplier
            unit_cost = actual_wage_rate  # Cost per hour
            unit_rev = (
                charge_out_rate if is_billable else Decimal("0.00")
            )  # Prepare metadata - ONLY timesheet-specific data, NOT job data
            if meta is None:
                meta = {}

            meta.update(
                {
                    "staff_id": str(staff_id),
                    "staff_name": staff.get_display_full_name(),
                    "entry_date": entry_date.isoformat(),
                    "date": entry_date.isoformat(),  # Legacy compatibility
                    "is_billable": is_billable,
                    "wage_rate_multiplier": float(rate_multiplier),
                    "rate_multiplier": float(rate_multiplier),  # Legacy compatibility
                    "created_from_timesheet": True,
                }
            )

            # DO NOT include job data in meta - it comes from CostSet relationship

            if ext_refs is None:
                ext_refs = {}

            # Create CostLine
            cost_line = CostLine.objects.create(
                cost_set=cost_set,
                kind="time",  # Always time for timesheet entries
                desc=description,
                quantity=str(hours),
                unit_cost=str(unit_cost),
                unit_rev=str(unit_rev),
                ext_refs=ext_refs,
                meta=meta,
            )

            # Update cost set summary
            cls._update_cost_set_summary(cost_set)

            logger.info(
                f"Created CostLine {cost_line.id} from timesheet data for job {job_id}, "
                f"staff {staff.get_display_full_name()}, {hours} hours"
            )

            return cost_line

    @classmethod
    def migrate_time_entry_to_cost_line(cls, time_entry: TimeEntry) -> CostLine:
        """
        Migrate an existing TimeEntry to a CostLine

        Args:
            time_entry: TimeEntry instance to migrate

        Returns:
            Created CostLine instance
        """
        # Guard clause - validate time entry has required data
        if not time_entry.job_pricing:
            raise ValueError(f"TimeEntry {time_entry.id} has no job_pricing")

        if not time_entry.staff:
            raise ValueError(f"TimeEntry {time_entry.id} has no staff")

        if not time_entry.date:
            raise ValueError(f"TimeEntry {time_entry.id} has no date")

        return cls.create_cost_line_from_timesheet(
            job_id=str(time_entry.job_pricing.job.id),
            staff_id=str(time_entry.staff.id),
            entry_date=time_entry.date,
            hours=time_entry.hours,
            description=time_entry.description or "",
            wage_rate=time_entry.wage_rate,
            charge_out_rate=time_entry.charge_out_rate,
            rate_multiplier=time_entry.wage_rate_multiplier,
            is_billable=time_entry.is_billable,
            ext_refs={"time_entry_id": str(time_entry.id)},
            meta={"notes": time_entry.note or ""},
        )

    @classmethod
    def _get_or_create_actual_cost_set(cls, job: Job) -> CostSet:
        """Get or create the actual CostSet for the job"""
        cost_set = job.cost_sets.filter(kind="actual").order_by("-rev").first()

        if not cost_set:
            # Create new actual cost set
            latest_rev = job.cost_sets.filter(kind="actual").count()
            cost_set = CostSet.objects.create(
                job=job,
                kind="actual",
                rev=latest_rev + 1,
                summary={"cost": 0, "rev": 0, "hours": 0},
            )
            logger.info(
                f"Created new actual CostSet rev {cost_set.rev} for job {job.id}"
            )

        return cost_set

    @classmethod
    def _update_cost_set_summary(cls, cost_set: CostSet) -> None:
        """Update cost set summary with aggregated data"""
        cost_lines = cost_set.cost_lines.all()

        total_cost = sum(line.total_cost for line in cost_lines)
        total_rev = sum(line.total_rev for line in cost_lines)
        total_hours = sum(
            float(line.quantity) for line in cost_lines if line.kind == "time"
        )

        cost_set.summary = {
            "cost": float(total_cost),
            "rev": float(total_rev),
            "hours": total_hours,
        }
        cost_set.save()
