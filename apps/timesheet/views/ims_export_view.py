"""
IMS Export API View for timesheet data export functionality.
Provides dedicated REST endpoint for IMS export with proper data transformation.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.timesheet.models import TimeEntry
from apps.timesheet.serializers import TimeEntryAPISerializer

logger = logging.getLogger(__name__)


class IMSExportView(APIView):
    """
    API endpoint for IMS (Integrated Management System) export functionality.
    Returns timesheet data formatted for IMS export with Tuesday-Friday + next Monday layout.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Export timesheet data in IMS format.

        Query Parameters:
            start_date (str): Start date in YYYY-MM-DD format (defaults to current week's Tuesday)

        Returns:
            JSON response with IMS formatted data including:
            - staff_data: List of staff with weekly hours breakdown
            - totals: Aggregated totals
            - week_days: List of dates for the IMS week
            - navigation URLs
        """
        try:
            start_date_str = request.GET.get("start_date")

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Default to current week's Tuesday
                today = timezone.now().date()
                start_date = self._get_ims_week_start(today)

            # Get IMS week days (Tuesday-Friday + next Monday)
            week_days = self._get_ims_week_days(start_date)

            # Get staff data with IMS formatting
            staff_data, totals = self._get_ims_staff_data(week_days)

            # Generate navigation URLs
            prev_week_url, next_week_url = self._get_navigation_urls(start_date)

            return Response(
                {
                    "success": True,
                    "staff_data": staff_data,
                    "totals": totals,
                    "week_days": [day.strftime("%Y-%m-%d") for day in week_days],
                    "prev_week_url": prev_week_url,
                    "next_week_url": next_week_url,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in IMS export: {str(e)}")
            return Response(
                {"error": "Failed to export IMS data", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_ims_week_start(self, reference_date):
        """
        Get the Tuesday of the IMS week for a given reference date.

        Args:
            reference_date: Date to find the IMS week for

        Returns:
            datetime.date: Tuesday of the IMS week
        """
        # Find the Tuesday of the current week
        days_since_tuesday = (reference_date.weekday() - 1) % 7
        tuesday = reference_date - timedelta(days=days_since_tuesday)
        return tuesday

    def _get_ims_week_days(self, tuesday_start):
        """
        Generate IMS week days: Tuesday, Wednesday, Thursday, Friday, and next Monday.

        Args:
            tuesday_start: The Tuesday to start from

        Returns:
            List[datetime.date]: List of dates for the IMS week
        """
        return [
            tuesday_start,  # Tuesday
            tuesday_start + timedelta(days=1),  # Wednesday
            tuesday_start + timedelta(days=2),  # Thursday
            tuesday_start + timedelta(days=3),  # Friday
            tuesday_start + timedelta(days=6),  # Next Monday
        ]

    def _get_ims_staff_data(self, week_days):
        """
        Get staff data formatted for IMS export.

        Args:
            week_days: List of dates for the IMS week

        Returns:
            Tuple[List[Dict], Dict]: Staff data and totals
        """
        # Get filtered staff list
        excluded_staff_ids = get_excluded_staff()
        staff_members = Staff.objects.exclude(id__in=excluded_staff_ids).order_by(
            "last_name", "first_name"
        )

        staff_data = []
        total_hours = 0
        total_billable_hours = 0
        total_standard_hours = 0
        total_time_and_half_hours = 0
        total_double_time_hours = 0

        for staff_member in staff_members:
            weekly_hours = []
            staff_total_hours = 0
            staff_billable_hours = 0
            staff_standard_hours = 0
            staff_time_and_half_hours = 0
            staff_double_time_hours = 0
            staff_annual_leave_hours = 0
            staff_sick_leave_hours = 0
            staff_other_leave_hours = 0

            for day in week_days:
                day_data = self._get_ims_day_data(staff_member, day)
                weekly_hours.append(day_data)

                # Aggregate staff totals
                staff_total_hours += day_data["hours"]
                staff_billable_hours += day_data["billable_hours"]
                staff_standard_hours += day_data["standard_hours"]
                staff_time_and_half_hours += day_data["time_and_half_hours"]
                staff_double_time_hours += day_data["double_time_hours"]
                staff_annual_leave_hours += day_data["annual_leave_hours"]
                staff_sick_leave_hours += day_data["sick_leave_hours"]
                staff_other_leave_hours += day_data["other_leave_hours"]

            # Calculate billable percentage
            billable_percentage = (
                (staff_billable_hours / staff_total_hours * 100)
                if staff_total_hours > 0
                else 0
            )

            staff_entry = {
                "staff_id": str(staff_member.id),
                "name": staff_member.get_display_full_name(),
                "weekly_hours": weekly_hours,
                "total_hours": float(staff_total_hours),
                "total_billable_hours": float(staff_billable_hours),
                "billable_percentage": round(billable_percentage, 1),
                "total_standard_hours": float(staff_standard_hours),
                "total_time_and_half_hours": float(staff_time_and_half_hours),
                "total_double_time_hours": float(staff_double_time_hours),
                "total_annual_leave_hours": float(staff_annual_leave_hours),
                "total_sick_leave_hours": float(staff_sick_leave_hours),
                "total_other_leave_hours": float(staff_other_leave_hours),
                "total_leave_hours": float(
                    staff_annual_leave_hours
                    + staff_sick_leave_hours
                    + staff_other_leave_hours
                ),
            }

            staff_data.append(staff_entry)

            # Aggregate grand totals
            total_hours += staff_total_hours
            total_billable_hours += staff_billable_hours
            total_standard_hours += staff_standard_hours
            total_time_and_half_hours += staff_time_and_half_hours
            total_double_time_hours += staff_double_time_hours

        totals = {
            "total_hours": float(total_hours),
            "total_billable_hours": float(total_billable_hours),
            "billable_percentage": round(
                (total_billable_hours / total_hours * 100) if total_hours > 0 else 0, 1
            ),
            "total_standard_hours": float(total_standard_hours),
            "total_time_and_half_hours": float(total_time_and_half_hours),
            "total_double_time_hours": float(total_double_time_hours),
        }

        return staff_data, totals

    def _get_ims_day_data(self, staff_member, day):
        """
        Get IMS formatted data for a staff member on a specific day.

        Args:
            staff_member: Staff instance
            day: datetime.date

        Returns:
            Dict: Formatted day data for IMS export
        """
        try:
            scheduled_hours = staff_member.get_scheduled_hours(day)
            time_entries = TimeEntry.objects.filter(
                staff=staff_member, date=day
            ).select_related("job_pricing__job")

            daily_hours = sum(entry.hours for entry in time_entries)
            daily_billable_hours = sum(
                entry.hours for entry in time_entries if entry.is_billable
            )

            # Handle leave entries
            leave_entries = time_entries.filter(
                job_pricing__job__name__icontains="Leave"
            )
            has_paid_leave = leave_entries.exists()
            leave_type = None
            annual_leave_hours = Decimal(0)
            sick_leave_hours = Decimal(0)
            other_leave_hours = Decimal(0)

            if has_paid_leave:
                for leave_entry in leave_entries:
                    leave_job_name = leave_entry.job_pricing.job.name.lower()
                    if "annual" in leave_job_name:
                        annual_leave_hours += leave_entry.hours
                        leave_type = "Annual"
                    elif "sick" in leave_job_name:
                        sick_leave_hours += leave_entry.hours
                        leave_type = "Sick"
                    else:
                        other_leave_hours += leave_entry.hours
                        leave_type = "Other"

            # Categorize work hours by rate multiplier
            non_leave_entries = time_entries.exclude(
                job_pricing__job__name__icontains="Leave"
            )

            standard_hours = Decimal(0)
            time_and_half_hours = Decimal(0)
            double_time_hours = Decimal(0)

            for entry in non_leave_entries:
                multiplier = Decimal(entry.wage_rate_multiplier)
                if multiplier == 1.0:
                    standard_hours += entry.hours
                elif multiplier == 1.5:
                    time_and_half_hours += entry.hours
                elif multiplier == 2.0:
                    double_time_hours += entry.hours

            # Calculate overtime
            overtime = max(Decimal(0), Decimal(daily_hours) - Decimal(scheduled_hours))

            # Determine status
            if has_paid_leave:
                status = "Leave"
            elif daily_hours >= scheduled_hours:
                status = "✓"
            elif daily_hours > 0:
                status = "⚠"
            else:
                status = "-"

            # Serialize time entries
            entries_data = []
            if time_entries:
                serializer = TimeEntryAPISerializer(time_entries, many=True)
                entries_data = serializer.data

            return {
                "date": day.strftime("%Y-%m-%d"),
                "hours": float(daily_hours),
                "billable_hours": float(daily_billable_hours),
                "standard_hours": float(standard_hours),
                "time_and_half_hours": float(time_and_half_hours),
                "double_time_hours": float(double_time_hours),
                "annual_leave_hours": float(annual_leave_hours),
                "sick_leave_hours": float(sick_leave_hours),
                "other_leave_hours": float(other_leave_hours),
                "overtime": float(overtime),
                "status": status,
                "leave_type": leave_type,
                "entries": entries_data,
            }

        except Exception as e:
            logger.error(
                f"Error getting IMS day data for {staff_member} on {day}: {str(e)}"
            )
            return {
                "date": day.strftime("%Y-%m-%d"),
                "hours": 0,
                "billable_hours": 0,
                "standard_hours": 0,
                "time_and_half_hours": 0,
                "double_time_hours": 0,
                "annual_leave_hours": 0,
                "sick_leave_hours": 0,
                "other_leave_hours": 0,
                "overtime": 0,
                "status": "⚠",
                "leave_type": None,
                "entries": [],
            }

    def _get_navigation_urls(self, start_date):
        """
        Generate navigation URLs for previous and next week.

        Args:
            start_date: Current week start date

        Returns:
            Tuple[str, str]: Previous week URL, Next week URL
        """
        prev_week_date = start_date - timedelta(days=7)
        next_week_date = start_date + timedelta(days=7)

        # For API endpoints, we'll just return the date strings
        # The frontend can construct the full URLs
        prev_week_url = f"/api/timesheets/ims-export/?start_date={prev_week_date.strftime('%Y-%m-%d')}"
        next_week_url = f"/api/timesheets/ims-export/?start_date={next_week_date.strftime('%Y-%m-%d')}"

        return prev_week_url, next_week_url
