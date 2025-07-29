"""
REST API views for timesheet functionality.
Provides endpoints for the Vue.js frontend to interact with timesheet data.
"""

import logging
import traceback
from datetime import datetime, timedelta

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.job.models import Job
from apps.timesheet.serializers import (
    DailyTimesheetSummarySerializer,
    JobsListResponseSerializer,
    ModernTimesheetJobSerializer,
    StaffListResponseSerializer,
    WeeklyTimesheetDataSerializer,
)
from apps.timesheet.serializers.modern_timesheet_serializers import (
    IMSWeeklyTimesheetDataSerializer,
)
from apps.timesheet.services.daily_timesheet_service import DailyTimesheetService
from apps.timesheet.services.weekly_timesheet_service import WeeklyTimesheetService

logger = logging.getLogger(__name__)


class StaffListAPIView(APIView):
    """API endpoint to get filtered list of staff members for timesheet operations.

    Returns staff members excluding system users and managers, formatted
    for timesheet entry forms and interfaces. Filters out staff with
    is_staff=True and excluded staff IDs from the utility function.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = StaffListResponseSerializer

    def get(self, request):
        """Get filtered list of staff members."""
        try:
            excluded_staff_ids = get_excluded_staff()
            # get_excluded_staff() now includes staff with no working hours
            staff = Staff.objects.exclude(
                Q(is_staff=True) | Q(id__in=excluded_staff_ids)
            ).order_by("last_name", "first_name")

            staff_data = []
            for member in staff:
                staff_data.append(
                    {
                        "id": str(member.id),
                        "name": member.get_display_name() or "Unknown",
                        "firstName": member.first_name or "",
                        "lastName": member.last_name or "",
                        "email": member.email or "",
                        "wageRate": (
                            float(member.wage_rate) if member.wage_rate else 0.0
                        ),
                        "avatarUrl": None,  # Add avatar logic if needed
                    }
                )

            return Response({"staff": staff_data, "total_count": len(staff_data)})

        except Exception as e:
            logger.error(f"Error fetching staff list: {e}")
            return Response(
                {"error": "Failed to fetch staff list", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobsAPIView(APIView):
    """API endpoint to get available jobs for timesheet entries."""

    permission_classes = [IsAuthenticated]
    serializer_class = JobsListResponseSerializer

    def get(self, request):
        """Get list of active jobs for timesheet entries using CostSet system."""
        try:
            # Get active jobs - exclude archived only
            jobs = (
                Job.objects.filter(
                    status__in=[
                        "draft",
                        "awaiting_approval",
                        "approved",
                        "in_progress",
                        "unusual",
                        "recently_completed",
                        "special",
                    ]
                )
                .select_related("client")
                .prefetch_related("cost_sets")  # Prefetch cost sets for efficiency
                .order_by("job_number")
            )

            # Filter jobs that have actual CostSet (for timesheet entries)
            # We create actual CostSet on-demand when needed
            jobs_with_actual_costset = []
            for job in jobs:
                # Temporarily include all jobs to debug the issue
                jobs_with_actual_costset.append(job)

            if not jobs_with_actual_costset:
                return Response({"jobs": [], "total_count": 0})

            serializer = ModernTimesheetJobSerializer(
                jobs_with_actual_costset, many=True
            )
            return Response(
                {"jobs": serializer.data, "total_count": len(serializer.data)}
            )

        except Exception as e:
            logger.error(f"Error fetching jobs: {e}")
            return Response(
                {"error": "Failed to fetch jobs", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DailyTimesheetAPIView(APIView):
    """
    API endpoint for daily timesheet overview.
    Provides comprehensive daily summary using modern CostLine system.

    Supports multiple URL patterns:
    - GET /timesheets/api/daily/ (today's data)
    - GET /timesheets/api/daily/{date}/ (specific date)
    - GET /timesheets/api/staff/{staff_id}/daily/ (staff detail for today)
    - GET /timesheets/api/staff/{staff_id}/daily/?date={date} (staff detail for specific date)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DailyTimesheetSummarySerializer

    def get(self, request, date=None, staff_id=None):
        """
        Get daily timesheet overview.

        Args:
            date: Optional date from URL path
            staff_id: Optional staff ID from URL path

        Query Parameters:
            date (optional): Date in YYYY-MM-DD format. Defaults to today.

        Returns:
            JSON response with daily timesheet data
        """
        try:
            # Determine target date - from URL path, query param, or today
            date_param = date or request.query_params.get("date")

            if date_param:
                try:
                    target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                target_date = date.today()

            # If staff_id is provided, return staff-specific data
            if staff_id:
                return self._get_staff_daily_detail(staff_id, target_date, request)

            # Otherwise return full daily summary
            logger.info(f"Getting daily timesheet overview for {target_date}")

            # Delegate to service layer for business logic
            summary_data = DailyTimesheetService.get_daily_summary(target_date)

            # Serialize and return response
            serializer = DailyTimesheetSummarySerializer(summary_data)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in DailyTimesheetAPIView: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {
                    "error": "Failed to get daily timesheet overview",
                    "details": (
                        str(e) if request.user.is_staff else "Internal server error"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_staff_daily_detail(self, staff_id, target_date, request):
        """Get detailed daily data for a specific staff member."""
        try:
            # Validate staff exists
            try:
                staff = Staff.objects.get(id=staff_id)
            except Staff.DoesNotExist:
                return Response(
                    {"error": "Staff member not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            logger.info(f"Getting daily detail for staff {staff_id} on {target_date}")

            # Get summary data and extract specific staff
            summary_data = DailyTimesheetService.get_daily_summary(target_date)

            # Find the staff member in the summary data
            staff_data = None
            for staff_info in summary_data.get("staff_data", []):
                if staff_info.get("staff_id") == str(staff_id):
                    staff_data = staff_info
                    break

            if not staff_data:
                # Staff exists but has no timesheet data for this date
                staff_data = {
                    "staff_id": str(staff_id),
                    "staff_name": f"{staff.first_name} {staff.last_name}",
                    "staff_initials": f"{staff.first_name[0]}{staff.last_name[0]}".upper(),
                    "avatar_url": None,
                    "scheduled_hours": 8.0,
                    "actual_hours": 0.0,
                    "billable_hours": 0.0,
                    "non_billable_hours": 0.0,
                    "total_revenue": 0.0,
                    "total_cost": 0.0,
                    "status": "No Entry",
                    "status_class": "danger",
                    "billable_percentage": 0.0,
                    "completion_percentage": 0.0,
                    "job_breakdown": [],
                    "entry_count": 0,
                    "alerts": ["No timesheet entries for this date"],
                }

            return Response(staff_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting staff daily detail: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {
                    "error": "Failed to get staff daily detail",
                    "details": (
                        str(e) if request.user.is_staff else "Internal server error"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WeeklyTimesheetAPIView(APIView):
    """
    Comprehensive weekly timesheet API endpoint using WeeklyTimesheetService.
    Provides complete weekly overview data for the modern Vue.js frontend.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "export_to_ims",
                OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Export data in IMS format for integration with IMS systems. Defaults to false.",
            )
        ],
        responses={
            "application/json": WeeklyTimesheetDataSerializer,
            "application/json; ?export_to_ims=true": IMSWeeklyTimesheetDataSerializer,
        },
    )
    def get(self, request):
        """
        Get comprehensive weekly timesheet data.

        Query Parameters:
            start_date (optional): Monday of target week in YYYY-MM-DD format
            export_to_ims (optional): Boolean to include IMS-specific data

        Returns:
            Comprehensive weekly timesheet data including:
            - Staff data with daily breakdowns
            - Weekly totals and metrics
            - Job statistics
            - Summary statistics
        """
        try:
            # Get and validate parameters
            start_date_str = request.query_params.get("start_date")
            export_to_ims = (
                request.query_params.get("export_to_ims", "").lower() == "true"
            )

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Default to current week Monday
                today = datetime.now().date()
                start_date = today - timedelta(days=today.weekday())

            logger.info(
                f"Getting weekly timesheet data for week starting {start_date}, IMS mode: {export_to_ims}"
            )

            # Use service layer for business logic
            weekly_data = WeeklyTimesheetService.get_weekly_overview(
                start_date, export_to_ims
            )

            # Add navigation URLs
            prev_week_date = start_date - timedelta(days=7)
            next_week_date = start_date + timedelta(days=7)

            weekly_data.update(
                {
                    "navigation": {
                        "prev_week_date": prev_week_date.strftime("%Y-%m-%d"),
                        "next_week_date": next_week_date.strftime("%Y-%m-%d"),
                        "current_week_date": start_date.strftime("%Y-%m-%d"),
                    }
                }
            )

            Serializer = (
                IMSWeeklyTimesheetDataSerializer
                if export_to_ims
                else WeeklyTimesheetDataSerializer
            )

            serializer = Serializer(weekly_data)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in WeeklyTimesheetAPIView: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {
                    "error": "Failed to get weekly timesheet data",
                    "details": (
                        str(e) if request.user.is_staff else "Internal server error"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """
        Submit paid absence request.

        Expected payload:
        {
            "staff_id": "uuid",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "leave_type": "annual|sick|other",
            "hours_per_day": 8.0,
            "description": "Optional description"
        }
        """
        try:
            data = request.data

            # Validate required fields
            required_fields = [
                "staff_id",
                "start_date",
                "end_date",
                "leave_type",
                "hours_per_day",
            ]
            for field in required_fields:
                if field not in data:
                    return Response(
                        {"error": f"Missing required field: {field}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Parse dates
            try:
                start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
                end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate date range
            if end_date < start_date:
                return Response(
                    {"error": "End date cannot be before start date"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Submit paid absence using service
            result = WeeklyTimesheetService.submit_paid_absence(
                staff_id=data["staff_id"],
                start_date=start_date,
                end_date=end_date,
                leave_type=data["leave_type"],
                hours_per_day=float(data["hours_per_day"]),
                description=data.get("description", ""),
            )

            if result.get("success"):
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error submitting paid absence: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            return Response(
                {
                    "error": "Failed to submit paid absence",
                    "details": (
                        str(e) if request.user.is_staff else "Internal server error"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
