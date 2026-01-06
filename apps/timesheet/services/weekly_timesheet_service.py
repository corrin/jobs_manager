"""
Weekly Timesheet Service

Service layer for handling weekly timesheet business logic including:
- Weekly data aggregation
- Payroll export functionality
- Staff summary calculations
- Job metrics

Refactored to use CostSet/CostLine system only
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.db import models
from django.db.models.expressions import RawSQL

from apps.accounts.models import Staff
from apps.accounts.utils import get_displayable_staff
from apps.job.models import Job
from apps.job.models.costing import CostLine

logger = logging.getLogger(__name__)


class WeeklyTimesheetService:
    """Service for weekly timesheet operations (Monday to Sunday)."""

    @classmethod
    def get_weekly_overview(cls, start_date: date) -> Dict[str, Any]:
        """
        Get comprehensive weekly timesheet overview with payroll data.

        Args:
            start_date: Monday of the target week

        Returns:
            Dict containing weekly overview data with payroll fields
        """
        try:
            # Calculate week range
            week_days = cls._get_week_days(start_date)
            end_date = start_date + timedelta(days=6)

            # Get staff data
            staff_data = cls._get_staff_data(week_days)

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
                "export_mode": "payroll",
                "is_current_week": cls._is_current_week(start_date),
            }

        except Exception as e:
            logger.error(f"Error getting weekly overview: {e}")
            raise

    @classmethod
    def _get_week_days(cls, start_date: date) -> List[date]:
        """Get list of days for the week (Monday to Sunday)."""
        return [start_date + timedelta(days=i) for i in range(7)]

    @classmethod
    def _get_staff_data(cls, week_days: List[date]) -> List[Dict[str, Any]]:
        """Get comprehensive staff data for the week with payroll fields."""
        staff_members = get_displayable_staff(date_range=(week_days[0], week_days[-1]))

        staff_data = []

        for staff_member in staff_members:
            # Get daily data for each day
            weekly_hours = []
            total_hours = 0
            total_billable_hours = 0
            total_scheduled_hours = 0

            # Payroll totals
            total_billed_hours = 0
            total_unbilled_hours = 0
            total_overtime_1_5x_hours = 0
            total_overtime_2x_hours = 0
            total_sick_leave_hours = 0
            total_annual_leave_hours = 0
            total_bereavement_leave_hours = 0
            total_weighted_hours = 0  # For cost calculation (hours × rate_multiplier)

            for day in week_days:
                daily_data = cls._get_payroll_daily_data(staff_member, day)

                # Calculate daily cost from weighted hours
                daily_weighted = daily_data.get("daily_weighted_hours", 0)
                daily_data["daily_cost"] = round(
                    float(staff_member.wage_rate) * daily_weighted, 2
                )

                weekly_hours.append(daily_data)
                total_hours += daily_data["hours"]
                total_billable_hours += daily_data.get("billable_hours", 0)
                total_scheduled_hours += daily_data.get("scheduled_hours", 0)

                total_billed_hours += daily_data.get("billed_hours", 0)
                total_unbilled_hours += daily_data.get("unbilled_hours", 0)
                total_overtime_1_5x_hours += daily_data.get("overtime_1_5x_hours", 0)
                total_overtime_2x_hours += daily_data.get("overtime_2x_hours", 0)
                total_sick_leave_hours += daily_data.get("sick_leave_hours", 0)
                total_annual_leave_hours += daily_data.get("annual_leave_hours", 0)
                total_bereavement_leave_hours += daily_data.get(
                    "bereavement_leave_hours", 0
                )
                total_weighted_hours += daily_data.get("daily_weighted_hours", 0)

            # Calculate cost and percentages
            weekly_cost = float(staff_member.wage_rate) * total_weighted_hours
            billable_percentage = (
                (total_billable_hours / total_hours * 100) if total_hours > 0 else 0
            )

            staff_entry = {
                "staff_id": str(staff_member.id),
                "name": staff_member.get_display_full_name(),
                "weekly_hours": weekly_hours,
                "total_hours": float(total_hours),
                "total_billable_hours": float(total_billable_hours),
                "total_scheduled_hours": float(total_scheduled_hours),
                "billable_percentage": round(billable_percentage, 1),
                "status": cls._get_staff_status(total_hours, staff_member),
                "total_billed_hours": float(total_billed_hours),
                "total_unbilled_hours": float(total_unbilled_hours),
                "total_overtime_1_5x_hours": float(total_overtime_1_5x_hours),
                "total_overtime_2x_hours": float(total_overtime_2x_hours),
                "total_sick_leave_hours": float(total_sick_leave_hours),
                "total_annual_leave_hours": float(total_annual_leave_hours),
                "total_bereavement_leave_hours": float(total_bereavement_leave_hours),
                "weekly_cost": round(weekly_cost, 2),
            }

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
    def _get_payroll_daily_data(cls, staff_member: Staff, day: date) -> Dict[str, Any]:
        """Get daily data with Xero posting categories using CostLine."""
        try:
            base_data = cls._get_daily_data(staff_member, day)

            # Get work hours by rate and billability (excludes unpaid/leave)
            cost_lines = (
                CostLine.objects.annotate(
                    staff_id=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.staff_id'))",
                        (),
                        output_field=models.CharField(),
                    ),
                    wage_rate_multiplier=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.wage_rate_multiplier'))",
                        (),
                        output_field=models.DecimalField(),
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
                .exclude(cost_set__job__name__icontains="Leave")
                .select_related("cost_set__job")
            )

            billed_hours = 0
            unbilled_hours = 0
            overtime_1_5x_hours = 0
            overtime_2x_hours = 0
            daily_weighted_hours = Decimal(0)  # hours × rate_multiplier for cost calc

            for line in cost_lines:
                multiplier = line.wage_rate_multiplier or Decimal("1.0")
                hours = line.quantity

                # Accumulate weighted hours for cost (unpaid hours × 0 = 0)
                daily_weighted_hours += hours * multiplier

                # Skip unpaid hours from billability/overtime categorization
                if multiplier == Decimal("0.0"):
                    continue

                # Categorize by billability
                if line.is_billable:
                    billed_hours += hours
                else:
                    unbilled_hours += hours

                # Categorize overtime
                if multiplier == Decimal("1.5"):
                    overtime_1_5x_hours += hours
                elif multiplier == Decimal("2.0"):
                    overtime_2x_hours += hours

            # Get leave hours broken down by type
            leave_lines = (
                CostLine.objects.annotate(
                    staff_id=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.staff_id'))",
                        (),
                        output_field=models.CharField(),
                    ),
                )
                .filter(
                    cost_set__kind="actual",
                    kind="time",
                    staff_id=str(staff_member.id),
                    accounting_date=day,
                    cost_set__job__name__icontains="Leave",
                )
                .select_related("cost_set__job")
            )

            sick_leave_hours = 0
            annual_leave_hours = 0
            bereavement_leave_hours = 0

            for line in leave_lines:
                pay_item = line.cost_set.job.default_xero_pay_item
                hours = line.quantity

                if pay_item is None:
                    continue  # Not a leave job
                elif pay_item.name == "Sick Leave":
                    sick_leave_hours += hours
                    daily_weighted_hours += hours  # Paid at 1.0x
                elif pay_item.name == "Annual Leave":
                    annual_leave_hours += hours
                    daily_weighted_hours += hours  # Paid at 1.0x
                elif pay_item.name == "Bereavement Leave":
                    bereavement_leave_hours += hours
                    daily_weighted_hours += hours  # Paid at 1.0x
                # Skip Unpaid Leave (contributes $0 to cost)

            base_data.update(
                {
                    "billed_hours": float(billed_hours),
                    "unbilled_hours": float(unbilled_hours),
                    "overtime_1_5x_hours": float(overtime_1_5x_hours),
                    "overtime_2x_hours": float(overtime_2x_hours),
                    "sick_leave_hours": float(sick_leave_hours),
                    "annual_leave_hours": float(annual_leave_hours),
                    "bereavement_leave_hours": float(bereavement_leave_hours),
                    "daily_weighted_hours": float(daily_weighted_hours),
                }
            )

            return base_data

        except Exception as e:
            logger.error(f"Error getting Payroll data for {staff_member} on {day}: {e}")
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
