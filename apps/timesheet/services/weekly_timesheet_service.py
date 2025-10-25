"""
Weekly Timesheet Service

Service layer for handling weekly timesheet business logic including:
- Weekly data aggregation
- IMS export functionality
- Staff summary calculations
- Job metrics

Refactored to use CostSet/CostLine system only
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.job.models import Job
from apps.job.models.costing import CostLine, CostSet

logger = logging.getLogger(__name__)


class WeeklyTimesheetService:
    """Service for weekly timesheet operations (Monday to Sunday)."""

    @classmethod
    def get_weekly_overview(
        cls, start_date: date, export_to_ims: bool = False
    ) -> Dict[str, Any]:
        """
        Get comprehensive weekly timesheet overview.

        Args:
            start_date: Monday of the target week
            export_to_ims: Whether to include IMS-specific data

        Returns:
            Dict containing weekly overview data
        """
        try:
            # Calculate week range
            week_days = cls._get_week_days(start_date, export_to_ims)
            end_date = start_date + timedelta(days=6)

            # Get staff data
            staff_data = cls._get_staff_data(week_days, export_to_ims)

            # Get weekly totals
            weekly_totals = cls._calculate_weekly_totals(staff_data)

            # Get job metrics
            job_metrics = cls._get_job_metrics(start_date, end_date)

            # Get summary stats
            summary_stats = cls._calculate_summary_stats(staff_data)

            return {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "week_days": [day.strftime("%Y-%m-%d") for day in week_days],
                "staff_data": staff_data,
                "weekly_summary": weekly_totals,
                "job_metrics": job_metrics,
                "summary_stats": summary_stats,
                "export_mode": "ims" if export_to_ims else "standard",
                "is_current_week": cls._is_current_week(start_date),
            }

        except Exception as e:
            logger.error(f"Error getting weekly overview: {e}")
            raise

    @classmethod
    def _get_week_days(
        cls, start_date: date, export_to_ims: bool = False
    ) -> List[date]:
        """Get list of days for the week."""
        if export_to_ims:
            return cls._get_ims_week(start_date)
        else:
            # Return all 7 days (Monday to Sunday)
            return [start_date + timedelta(days=i) for i in range(7)]

    @classmethod
    def _get_ims_week(cls, start_date: date) -> List[date]:
        """Get IMS week format (Tue-Fri + next Mon)."""
        try:
            # Find Tuesday of the week
            if start_date.weekday() == 0:  # Monday
                tuesday = start_date + timedelta(days=1)
            else:
                tuesday = start_date - timedelta(days=start_date.weekday() - 1)

            return [
                tuesday,  # Tuesday
                tuesday + timedelta(days=1),  # Wednesday
                tuesday + timedelta(days=2),  # Thursday
                tuesday + timedelta(days=3),  # Friday
                tuesday + timedelta(days=6),  # Next Monday
            ]
        except Exception as e:
            logger.error(f"Error getting IMS week: {e}")
            return []

    @classmethod
    def _get_staff_data(
        cls, week_days: List[date], export_to_ims: bool = False
    ) -> List[Dict[str, Any]]:
        """Get comprehensive staff data for the week."""
        excluded_staff_ids = get_excluded_staff()
        staff_members = Staff.objects.exclude(
            Q(is_staff=True) | Q(id__in=excluded_staff_ids)
        ).order_by("first_name", "last_name")

        staff_data = []

        for staff_member in staff_members:
            # Get daily data for each day
            weekly_hours = []
            total_hours = 0
            total_billable_hours = 0
            total_overtime = 0

            # IMS specific totals
            total_standard_hours = 0
            total_time_and_half_hours = 0
            total_double_time_hours = 0
            total_leave_hours = 0

            for day in week_days:
                if export_to_ims:
                    daily_data = cls._get_ims_daily_data(staff_member, day)
                else:
                    daily_data = cls._get_daily_data(staff_member, day)

                weekly_hours.append(daily_data)
                total_hours += daily_data["hours"]
                total_billable_hours += daily_data.get("billable_hours", 0)

                if export_to_ims:
                    total_overtime += daily_data.get("overtime", 0)
                    total_standard_hours += daily_data.get("standard_hours", 0)
                    total_time_and_half_hours += daily_data.get(
                        "time_and_half_hours", 0
                    )
                    total_double_time_hours += daily_data.get("double_time_hours", 0)
                    total_leave_hours += daily_data.get("leave_hours", 0)

            # Calculate percentages
            billable_percentage = (
                (total_billable_hours / total_hours * 100) if total_hours > 0 else 0
            )

            staff_entry = {
                "staff_id": str(staff_member.id),
                "name": staff_member.get_display_full_name(),
                "weekly_hours": weekly_hours,
                "total_hours": float(total_hours),
                "total_billable_hours": float(total_billable_hours),
                "billable_percentage": round(billable_percentage, 1),
                "status": cls._get_staff_status(total_hours, staff_member),
            }

            # Add IMS specific fields
            if export_to_ims:
                staff_entry.update(
                    {
                        "total_overtime": float(total_overtime),
                        "total_standard_hours": float(total_standard_hours),
                        "total_time_and_half_hours": float(total_time_and_half_hours),
                        "total_double_time_hours": float(total_double_time_hours),
                        "total_leave_hours": float(total_leave_hours),
                    }
                )

            staff_data.append(staff_entry)

        return staff_data

    @classmethod
    def _get_daily_data(cls, staff_member: Staff, day: date) -> Dict[str, Any]:
        """Get standard daily data for a staff member using CostLine."""
        try:
            scheduled_hours = staff_member.get_scheduled_hours(day)

            # Get cost lines for this staff and date from 'actual' cost sets
            cost_lines = (
                CostLine.objects.annotate(
                    staff_id=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.staff_id'))",
                        (),
                        output_field=models.CharField(),
                    ),
                    is_billable=RawSQL(
                        "JSON_EXTRACT(meta, '$.is_billable') = true",
                        (),
                        output_field=models.BooleanField(),
                    ),
                )
                .filter(
                    cost_set__kind="actual",
                    kind="time",
                    staff_id=str(staff_member.id),
                    accounting_date=day,
                )
                .select_related("cost_set__job")
            )

            daily_hours = sum(Decimal(line.quantity) for line in cost_lines)
            billable_hours = sum(
                Decimal(line.quantity) for line in cost_lines if line.is_billable
            )

            # Check for leave - look for jobs with "Leave" in name
            leave_lines = [
                line
                for line in cost_lines
                if line.cost_set
                and line.cost_set.job
                and "Leave" in line.cost_set.job.name
            ]
            has_leave = len(leave_lines) > 0
            leave_type = leave_lines[0].cost_set.job.name if has_leave else None

            # Determine status
            status = cls._get_day_status(float(daily_hours), scheduled_hours, has_leave)

            return {
                "day": day.strftime("%Y-%m-%d"),
                "hours": float(daily_hours),
                "billable_hours": float(billable_hours),
                "scheduled_hours": float(scheduled_hours),
                "status": status,
                "leave_type": leave_type,
                "has_leave": has_leave,
            }

        except Exception as e:
            logger.error(f"Error getting daily data for {staff_member} on {day}: {e}")
            return {
                "day": day.strftime("%Y-%m-%d"),
                "hours": 0.0,
                "billable_hours": 0.0,
                "scheduled_hours": 0.0,
                "status": "⚠",
                "leave_type": None,
                "has_leave": False,
            }

    @classmethod
    def _get_ims_daily_data(cls, staff_member: Staff, day: date) -> Dict[str, Any]:
        """Get IMS-specific daily data including wage rate breakdowns using CostLine."""
        try:
            base_data = cls._get_daily_data(staff_member, day)

            # Get wage rate breakdowns from CostLine meta
            cost_lines = (
                CostLine.objects.annotate(
                    staff_id=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.staff_id'))",
                        (),
                        output_field=models.CharField(),
                    ),
                    rate_multiplier=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.rate_multiplier'))",
                        (),
                        output_field=models.DecimalField(),
                    ),
                )
                .filter(
                    cost_set__kind="actual",
                    kind="time",
                    staff_id=str(staff_member.id),
                    accounting_date=day,
                )
                .exclude(cost_set__job__name__icontains="Leave")
            )

            standard_hours = 0
            time_and_half_hours = 0
            double_time_hours = 0
            unpaid_hours = 0

            for line in cost_lines:
                multiplier = line.rate_multiplier or Decimal("1.0")
                hours = line.quantity

                if multiplier == Decimal("1.0"):
                    standard_hours += hours
                elif multiplier == Decimal("1.5"):
                    time_and_half_hours += hours
                elif multiplier == Decimal("2.0"):
                    double_time_hours += hours
                elif multiplier == Decimal("0.0"):
                    unpaid_hours += hours

            # Calculate overtime
            scheduled_hours = base_data["scheduled_hours"]
            overtime = max(0, base_data["hours"] - scheduled_hours)

            # Get leave hours from CostLine
            leave_lines = CostLine.objects.annotate(
                staff_id=RawSQL(
                    "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.staff_id'))",
                    (),
                    output_field=models.CharField(),
                ),
            ).filter(
                cost_set__kind="actual",
                kind="time",
                staff_id=str(staff_member.id),
                accounting_date=day,
                cost_set__job__name__icontains="Leave",
            )

            leave_hours = sum(line.quantity for line in leave_lines)

            base_data.update(
                {
                    "standard_hours": float(standard_hours),
                    "time_and_half_hours": float(time_and_half_hours),
                    "double_time_hours": float(double_time_hours),
                    "unpaid_hours": float(unpaid_hours),
                    "overtime": float(overtime),
                    "leave_hours": float(leave_hours),
                }
            )

            return base_data

        except Exception as e:
            logger.error(f"Error getting IMS data for {staff_member} on {day}: {e}")
            return cls._get_daily_data(staff_member, day)

    @classmethod
    def _get_day_status(
        cls, daily_hours: float, scheduled_hours: float, has_leave: bool
    ) -> str:
        """Determine status for a day."""
        if has_leave:
            return "Leave"
        elif scheduled_hours == 0:
            return "Off"
        elif daily_hours == 0:
            return "⚠"
        elif daily_hours >= scheduled_hours:
            return "✓"
        else:
            return "⚠"

    @classmethod
    def _get_staff_status(cls, total_hours: float, staff_member: Staff) -> str:
        """Determine overall status for staff member."""
        if total_hours >= 35:
            return "Complete"
        elif total_hours >= 20:
            return "Partial"
        elif total_hours > 0:
            return "Minimal"
        else:
            return "Missing"

    @classmethod
    def _calculate_weekly_totals(
        cls, staff_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate weekly totals from staff data."""
        total_hours = sum(staff["total_hours"] for staff in staff_data)
        total_billable_hours = sum(
            staff["total_billable_hours"] for staff in staff_data
        )

        billable_percentage = (
            (total_billable_hours / total_hours * 100) if total_hours > 0 else 0
        )

        return {
            "total_hours": round(total_hours, 1),
            "total_billable_hours": round(total_billable_hours, 1),
            "billable_percentage": round(billable_percentage, 1),
            "staff_count": len(staff_data),
        }

    @classmethod
    def _get_job_metrics(cls, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get job-related metrics for the week using CostLine system."""
        try:
            # Get active jobs
            active_jobs = Job.objects.filter(
                status__in=["accepted_quote", "in_progress", "quoting"]
            ).count()

            # Get all cost lines for the week (not just time)
            cost_lines_week = CostLine.objects.filter(
                cost_set__kind="actual",
                accounting_date__gte=start_date,
                accounting_date__lte=end_date,
            ).select_related("cost_set__job")

            jobs_with_entries = (
                cost_lines_week.values("cost_set__job").distinct().count()
            )
            logger.info(f"Query result: {cost_lines_week}")

            # Calculate totals
            total_actual_hours = Decimal(0)
            total_estimated_hours = Decimal(0)
            total_estimated_profit = Decimal(0)
            total_actual_profit = Decimal(0)

            # Use a set to track jobs we've already processed for estimates
            processed_jobs = set()

            for line in cost_lines_week:
                if line.kind == "time":
                    total_actual_hours += line.quantity

                # Calculate actual profit for each line
                total_actual_profit += line.total_rev - line.total_cost

                # Calculate estimated profit for the job (once per job)
                job = line.cost_set.job
                if job and job.id not in processed_jobs:
                    processed_jobs.add(job.id)
                    if job.latest_estimate:
                        est_cost = job.latest_estimate.summary["cost"]
                        est_rev = job.latest_estimate.summary["rev"]
                        total_estimated_hours += Decimal(
                            job.latest_estimate.summary.get("total_hours", 0)
                        )
                        total_estimated_profit += Decimal(est_rev - est_cost)

            job_metrics = {
                "job_count": active_jobs,
                "jobs_worked_this_week": jobs_with_entries,
                "total_estimated_hours": float(total_estimated_hours),
                "total_actual_hours": float(total_actual_hours),
                "total_estimated_profit": float(total_estimated_profit),
                "total_actual_profit": float(total_actual_profit),
                "total_profit": float(
                    total_actual_profit
                ),  # For now, total_profit is actual
            }

            logger.info(f"Job metrics: {job_metrics}")

            return job_metrics

        except Exception as e:
            logger.error(f"Error getting job metrics: {e}")
            return {
                "job_count": 0,
                "jobs_worked_this_week": 0,
                "total_estimated_hours": 0,
                "total_actual_hours": 0,
                "total_estimated_profit": 0,
                "total_actual_profit": 0,
                "total_profit": 0,
            }

    @classmethod
    def _calculate_summary_stats(
        cls, staff_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate summary statistics."""
        total_staff = len(staff_data)
        complete_staff = len([s for s in staff_data if s["status"] == "Complete"])
        partial_staff = len([s for s in staff_data if s["status"] == "Partial"])
        missing_staff = len([s for s in staff_data if s["status"] == "Missing"])

        completion_rate = (complete_staff / total_staff * 100) if total_staff > 0 else 0

        return {
            "total_staff": total_staff,
            "complete_staff": complete_staff,
            "partial_staff": partial_staff,
            "missing_staff": missing_staff,
            "completion_rate": round(completion_rate, 1),
        }

    @classmethod
    def _is_current_week(cls, start_date: date) -> bool:
        """Check if the given start date is the current week."""
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        return start_date == current_week_start

    @classmethod
    def submit_paid_absence(
        cls,
        staff_id: str,
        start_date: date,
        end_date: date,
        leave_type: str,
        hours_per_day: float,
        description: str = "",
    ) -> Dict[str, Any]:
        """Submit a paid absence request using CostLine system."""
        try:
            # Get staff member
            staff = Staff.objects.get(id=staff_id)

            # Get appropriate leave job
            leave_job_names = {
                "vacation": "Annual Leave",
                "sick": "Sick Leave",
                "personal": "Other Leave",
                "bereavement": "Other Leave",
                "jury_duty": "Other Leave",
                "training": "Training",
                "other": "Other Leave",
            }

            job_name = leave_job_names.get(leave_type, "Other Leave")
            leave_job = Job.objects.filter(name=job_name).first()

            if not leave_job:
                raise ValueError(f"Leave job '{job_name}' not found")

            # Get or create actual cost set for the leave job
            cost_set, created = CostSet.objects.get_or_create(
                job=leave_job, kind="actual", defaults={"rev": 1, "summary": {}}
            )

            # Create cost lines for each working day
            current_date = start_date
            entries_created = 0

            while current_date <= end_date:
                # Include all days (no weekend skip)
                # Check if entry already exists using CostLine
                existing_lines = CostLine.objects.annotate(
                    staff_id=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.staff_id'))",
                        (),
                        output_field=models.CharField(),
                    ),
                ).filter(
                    cost_set=cost_set,
                    kind="time",
                    staff_id=str(staff_id),
                    accounting_date=current_date,
                )

                if not existing_lines.exists():
                    CostLine.objects.create(
                        cost_set=cost_set,
                        kind="time",
                        desc=f"{leave_type.title()} - {description}".strip(),
                        quantity=Decimal(str(hours_per_day)),
                        unit_cost=staff.wage_rate,  # Use staff wage rate
                        unit_rev=Decimal("0"),  # Leave is not billable
                        accounting_date=current_date,
                        meta={
                            "staff_id": str(staff_id),
                            "date": current_date.isoformat(),
                            "is_billable": False,
                            "wage_rate": float(staff.wage_rate),
                            "charge_out_rate": 0.0,
                            "rate_multiplier": 1.0,
                            "leave_type": leave_type,
                            "created_from_timesheet": True,
                        },
                    )
                    entries_created += 1

                current_date += timedelta(days=1)

            # Update job's latest_actual pointer if needed
            if (
                not leave_job.latest_actual
                or cost_set.rev >= leave_job.latest_actual.rev
            ):
                leave_job.latest_actual = cost_set
                leave_job.save(update_fields=["latest_actual"])

            return {
                "success": True,
                "entries_created": entries_created,
                "message": f"Successfully created {entries_created} leave entries",
            }

        except Exception as e:
            logger.error(f"Error submitting paid absence: {e}")
            return {"success": False, "error": str(e)}
