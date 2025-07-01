"""
Weekly Timesheet Service

Service layer for handling weekly timesheet business logic including:
- Weekly data aggregation
- IMS export functionality
- Staff summary calculations
- Job metrics
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Q, Sum

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.job.models import Job, JobPricing
from apps.timesheet.models import TimeEntry

logger = logging.getLogger(__name__)


class WeeklyTimesheetService:
    """Service for weekly timesheet operations."""

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
            # Return only weekdays (Monday to Friday)
            return [start_date + timedelta(days=i) for i in range(5)]

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
        ).order_by("last_name", "first_name")

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
        """Get standard daily data for a staff member."""
        try:
            scheduled_hours = staff_member.get_scheduled_hours(day)
            time_entries = TimeEntry.objects.filter(
                staff=staff_member, date=day
            ).select_related("job_pricing")

            daily_hours = sum(entry.hours for entry in time_entries)
            billable_hours = sum(
                entry.hours for entry in time_entries if entry.is_billable
            )

            # Check for leave
            leave_entries = time_entries.filter(
                job_pricing__job__name__icontains="Leave"
            )
            has_leave = leave_entries.exists()
            leave_type = (
                leave_entries.first().job_pricing.job.name if has_leave else None
            )

            # Determine status
            status = cls._get_day_status(daily_hours, scheduled_hours, has_leave)

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
        """Get IMS-specific daily data including wage rate breakdowns."""
        try:
            base_data = cls._get_daily_data(staff_member, day)

            # Get wage rate breakdowns
            time_entries = TimeEntry.objects.filter(
                staff=staff_member, date=day
            ).exclude(job_pricing__job__name__icontains="Leave")

            standard_hours = 0
            time_and_half_hours = 0
            double_time_hours = 0
            unpaid_hours = 0

            for entry in time_entries:
                multiplier = Decimal(entry.wage_rate_multiplier or 1.0)
                if multiplier == Decimal("1.0"):
                    standard_hours += entry.hours
                elif multiplier == Decimal("1.5"):
                    time_and_half_hours += entry.hours
                elif multiplier == Decimal("2.0"):
                    double_time_hours += entry.hours
                elif multiplier == Decimal("0.0"):
                    unpaid_hours += entry.hours

            # Calculate overtime
            scheduled_hours = base_data["scheduled_hours"]
            overtime = max(0, base_data["hours"] - scheduled_hours)

            # Get leave hours
            leave_entries = TimeEntry.objects.filter(
                staff=staff_member, date=day, job_pricing__job__name__icontains="Leave"
            )
            leave_hours = sum(entry.hours for entry in leave_entries)

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
        """Get job-related metrics for the week."""
        try:
            # Get active jobs
            active_jobs = Job.objects.filter(
                status__in=["approved", "in_progress", "quoting"]
            ).count()
            # Get jobs with entries in this week using CostLine system
            jobs_with_entries = (
                Job.objects.filter(
                    cost_sets__cost_lines__entry_date__range=[start_date, end_date]
                )
                .distinct()
                .count()
            )

            # Calculate total estimated and actual hours using CostLine system
            job_stats = Job.objects.filter(
                cost_sets__cost_lines__entry_date__range=[start_date, end_date]
            ).aggregate(
                total_estimated=Sum("estimated_hours"),
                total_actual=Sum("cost_sets__cost_lines__actual_hours"),
            )

            return {
                "job_count": active_jobs,
                "jobs_worked_this_week": jobs_with_entries,
                "total_estimated_hours": float(job_stats["total_estimated"] or 0),
                "total_actual_hours": float(job_stats["total_actual"] or 0),
            }

        except Exception as e:
            logger.error(f"Error getting job metrics: {e}")
            return {
                "job_count": 0,
                "jobs_worked_this_week": 0,
                "total_estimated_hours": 0,
                "total_actual_hours": 0,
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
        """Submit a paid absence request."""
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

            # Get job pricing
            job_pricing = JobPricing.objects.filter(job=leave_job).first()
            if not job_pricing:
                raise ValueError(f"Job pricing for '{job_name}' not found")

            # Create time entries for each working day
            current_date = start_date
            entries_created = 0

            while current_date <= end_date:
                # Skip weekends
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    # Check if entry already exists
                    existing_entry = TimeEntry.objects.filter(
                        staff=staff, date=current_date, job_pricing=job_pricing
                    ).first()

                    if not existing_entry:
                        TimeEntry.objects.create(
                            staff=staff,
                            date=current_date,
                            job_pricing=job_pricing,
                            hours=Decimal(str(hours_per_day)),
                            description=f"{leave_type.title()} - {description}".strip(),
                            is_billable=False,
                            wage_rate_multiplier=Decimal("1.0"),
                        )
                        entries_created += 1

                current_date += timedelta(days=1)

            return {
                "success": True,
                "entries_created": entries_created,
                "message": f"Successfully created {entries_created} leave entries",
            }

        except Exception as e:
            logger.error(f"Error submitting paid absence: {e}")
            return {"success": False, "error": str(e)}
