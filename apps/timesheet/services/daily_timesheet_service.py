"""
Daily Timesheet Service

Service layer for daily timesheet operations using CostLine system
Following SRP principles and clean architecture
"""

import logging
import traceback
import uuid
from datetime import date
from decimal import Decimal
from typing import Dict, List

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.job.models.costing import CostLine

logger = logging.getLogger(__name__)


def ensure_json_serializable(obj):
    """
    Recursively convert any UUID objects to strings for JSON serialization
    """
    if isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: ensure_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_serializable(item) for item in obj]
    else:
        return obj


class DailyTimesheetService:
    """Service for handling daily timesheet operations"""

    EXCLUDED_STAFF_IDS = get_excluded_staff()

    @classmethod
    def get_daily_summary(cls, target_date: date) -> Dict:
        """
        Get comprehensive daily timesheet summary for all staff

        Args:
            target_date: Date to get summary for

        Returns:
            Dict containing staff data and daily totals
        """
        try:
            staff_data = cls._get_staff_daily_data(target_date)
            daily_totals = cls._calculate_daily_totals(staff_data)
            return {
                "date": target_date.isoformat(),
                "staff_data": staff_data,
                "daily_totals": daily_totals,
                "summary_stats": cls._get_summary_stats(staff_data),
            }

        except Exception as e:
            logger.error(f"Error getting daily summary for {target_date}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    @classmethod
    def _get_staff_daily_data(cls, target_date: date) -> List[Dict]:
        """Get timesheet data for each staff member"""
        staff_data = []

        # Get active staff excluding those in EXCLUDED_STAFF_IDS
        active_staff = (
            Staff.objects.filter(is_active=True)
            .exclude(id__in=cls.EXCLUDED_STAFF_IDS)
            .order_by("first_name", "last_name")
        )

        for staff in active_staff:
            staff_info = cls._get_staff_timesheet_data(staff, target_date)
            staff_data.append(staff_info)

        return staff_data

    @classmethod
    def _get_staff_timesheet_data(cls, staff: Staff, target_date: date) -> Dict:
        """Get timesheet data for a specific staff member"""

        try:
            logger.debug(
                f"Processing staff: {staff.id} ({type(staff.id)}) for date {target_date}"
            )
            # Get cost lines for this staff and date (kind='time')
            # Convert UUID to string for JSON field lookup
            cost_lines = CostLine.objects.filter(
                meta__staff_id=str(staff.id),
                meta__date=target_date.isoformat(),
                kind="time",
            ).select_related("cost_set__job")

            logger.debug(
                f"Found {len(cost_lines)} cost lines for staff {staff.id}")

            # Calculate totals
            total_hours = sum(Decimal(line.quantity) for line in cost_lines)
            billable_hours = sum(
                Decimal(line.quantity)
                for line in cost_lines
                if line.meta.get("is_billable", True)
            )
            total_revenue = sum(Decimal(line.total_rev) for line in cost_lines)
            total_cost = sum(Decimal(line.total_cost) for line in cost_lines)

            # Get scheduled hours (8 hours default for weekdays)
            scheduled_hours = cls._get_scheduled_hours(staff, target_date)

            # Determine status
            status = cls._determine_status(
                total_hours, scheduled_hours, cost_lines)

            # Get job breakdown
            job_breakdown = cls._get_job_breakdown(cost_lines)
            logger.debug(
                f"Job breakdown for staff {staff.id}: {job_breakdown}")

            staff_data = {
                "staff_id": str(staff.id),
                "staff_name": f"{staff.first_name} {staff.last_name}",
                "staff_initials": f"{staff.first_name[0]}{staff.last_name[0]}".upper(),
                "avatar_url": getattr(staff, "avatar_url", None),
                "scheduled_hours": float(scheduled_hours),
                "actual_hours": float(total_hours),
                "billable_hours": float(billable_hours),
                "non_billable_hours": float(total_hours - billable_hours),
                "total_revenue": float(total_revenue),
                "total_cost": float(total_cost),
                "status": status,
                "status_class": cls._get_status_class(status),
                "billable_percentage": cls._calculate_percentage(
                    billable_hours, total_hours
                ),
                "completion_percentage": cls._calculate_percentage(
                    total_hours, scheduled_hours
                ),
                "job_breakdown": job_breakdown,
                "entry_count": len(cost_lines),
                "alerts": cls._get_staff_alerts(
                    staff, total_hours, scheduled_hours, cost_lines
                ),
            }

            logger.debug(f"Staff data for {staff.id}: {staff_data}")
            return staff_data

        except Exception as e:
            logger.error(f"Error processing staff {staff.id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    @classmethod
    def _get_scheduled_hours(cls, staff: Staff, target_date: date) -> Decimal:
        """Get scheduled hours for staff on given date"""
        # Skip weekends
        if target_date.weekday() >= 5:  # Saturday=5, Sunday=6
            return Decimal("0.0")

        # Default 8 hours for weekdays - could be enhanced with staff schedules
        return Decimal("8.0")

    @classmethod
    def _determine_status(
        cls, actual_hours: Decimal, scheduled_hours: Decimal, cost_lines
    ) -> str:
        """Determine status based on hours and entries"""
        if scheduled_hours == 0:
            return "Weekend"

        if actual_hours == 0:
            return "No Entry"

        if actual_hours < scheduled_hours * Decimal("0.9"):  # Less than 90%
            return "Incomplete"

        if actual_hours >= scheduled_hours:
            return "Complete"

        return "Partial"

    @classmethod
    def _get_status_class(cls, status: str) -> str:
        """Get CSS class for status"""
        status_classes = {
            "Complete": "success",
            "Partial": "warning",
            "Incomplete": "warning",
            "No Entry": "danger",
            "Weekend": "secondary",
        }
        return status_classes.get(status, "secondary")

    @classmethod
    def _get_job_breakdown(cls, cost_lines) -> List[Dict]:
        """Get breakdown of hours by job using the actual CostSet relationship"""
        job_data = {}

        for line in cost_lines:
            # Use the actual relationship instead of deprecated meta.job_id
            job = line.cost_set.job if line.cost_set else None

            if job:
                job_id_str = str(job.id)
                job_number = job.job_number or "Unknown"
                job_name = job.name or "Unknown Job"

                if job_id_str not in job_data:
                    job_data[job_id_str] = {
                        "job_id": job_id_str,
                        "job_number": job_number,
                        "job_name": job_name,
                        "client": job.client.name if job.client else "",
                        "hours": Decimal("0.0"),
                        "revenue": Decimal("0.0"),
                        "cost": Decimal("0.0"),
                        "is_billable": line.meta.get("is_billable", True),
                    }

                job_data[job_id_str]["hours"] += Decimal(line.quantity)
                job_data[job_id_str]["revenue"] += Decimal(line.total_rev)
                job_data[job_id_str]["cost"] += Decimal(line.total_cost)

        # Convert to list and sort by hours descending
        breakdown = list(job_data.values())
        breakdown.sort(key=lambda x: x["hours"], reverse=True)

        # Convert Decimal to float for JSON serialization
        for job in breakdown:
            job["hours"] = float(job["hours"])
            job["revenue"] = float(job["revenue"])
            job["cost"] = float(job["cost"])

        return breakdown

    @classmethod
    def _get_staff_alerts(
        cls, staff: Staff, actual_hours: Decimal, scheduled_hours: Decimal, cost_lines
    ) -> List[str]:
        """Get alerts for staff timesheet"""
        alerts = []

        if actual_hours == 0 and scheduled_hours > 0:
            alerts.append("No timesheet entries")

        if actual_hours > 0 and actual_hours < scheduled_hours * Decimal("0.5"):
            alerts.append("Low hours recorded")

        if actual_hours > scheduled_hours * Decimal("1.2"):  # More than 120%
            alerts.append("Overtime recorded")
        # Check for missing job information - use actual relationship instead of deprecated meta.job_id
        missing_job_entries = [
            line for line in cost_lines if not (line.cost_set and line.cost_set.job)
        ]
        if missing_job_entries:
            alerts.append(
                f"{len(missing_job_entries)} entries missing job info")

        return alerts

    @classmethod
    def _calculate_daily_totals(cls, staff_data: List[Dict]) -> Dict:
        """Calculate daily totals across all staff"""
        total_scheduled = sum(s["scheduled_hours"] for s in staff_data)
        total_actual = sum(s["actual_hours"] for s in staff_data)
        total_billable = sum(s["billable_hours"] for s in staff_data)
        total_revenue = sum(s["total_revenue"] for s in staff_data)
        total_cost = sum(s["total_cost"] for s in staff_data)
        total_entries = sum(s["entry_count"] for s in staff_data)

        return {
            "total_scheduled_hours": total_scheduled,
            "total_actual_hours": total_actual,
            "total_billable_hours": total_billable,
            "total_non_billable_hours": total_actual - total_billable,
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_entries": total_entries,
            "completion_percentage": cls._calculate_percentage(
                total_actual, total_scheduled
            ),
            "billable_percentage": cls._calculate_percentage(
                total_billable, total_actual
            ),
            "missing_hours": max(0, total_scheduled - total_actual),
        }

    @classmethod
    def _get_summary_stats(cls, staff_data: List[Dict]) -> Dict:
        """Get summary statistics"""
        total_staff = len(staff_data)
        complete_staff = len(
            [s for s in staff_data if s["status"] == "Complete"])
        partial_staff = len(
            [s for s in staff_data if s["status"] == "Partial"])
        missing_staff = len(
            [s for s in staff_data if s["status"] == "No Entry"])

        return {
            "total_staff": total_staff,
            "complete_staff": complete_staff,
            "partial_staff": partial_staff,
            "missing_staff": missing_staff,
            "completion_rate": cls._calculate_percentage(complete_staff, total_staff),
        }

    @classmethod
    def _calculate_percentage(cls, part: Decimal, total: Decimal) -> float:
        """Calculate percentage with proper handling of zero division"""
        if total == 0:
            return 0.0
        return float((part / total) * 100)
