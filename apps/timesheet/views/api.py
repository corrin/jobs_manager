"""
REST API views for timesheet functionality.
Provides endpoints for the Vue.js frontend to interact with timesheet data.
"""

import logging
import traceback
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.client.serializers import ClientErrorResponseSerializer
from apps.job.models import Job
from apps.timesheet.serializers import (
    DailyTimesheetSummarySerializer,
    JobsListResponseSerializer,
    ModernTimesheetJobSerializer,
    StaffListResponseSerializer,
    WeeklyTimesheetDataSerializer,
)
from apps.timesheet.serializers.payroll_serializers import (
    CreatePayRunRequestSerializer,
    CreatePayRunResponseSerializer,
    PostWeekToXeroRequestSerializer,
    PostWeekToXeroResponseSerializer,
)
from apps.timesheet.services.daily_timesheet_service import DailyTimesheetService
from apps.timesheet.services.payroll_sync import PayrollSyncService
from apps.timesheet.services.weekly_timesheet_service import WeeklyTimesheetService
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class StaffListAPIView(APIView):
    """API endpoint to get filtered list of staff members for timesheet operations.

    Returns staff members excluding system users and managers, formatted
    for timesheet entry forms and interfaces. Filters out staff with
    is_staff=True and excluded staff IDs from the utility function.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = StaffListResponseSerializer

    @extend_schema(
        summary="Returns staff members excluding system and users for a specific date",
        parameters=[
            OpenApiParameter(
                "date",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Date parameter in format YYYY-MM-DD",
            )
        ],
    )
    def get(self, request):
        """Get filtered list of staff members for a specific date."""
        try:
            # Add required date parameter
            date_param = request.query_params.get("date") or datetime.now().strftime(
                "%Y-%m-%d"
            )
            if not date_param:
                logger.error("Date parameter not received in StaffListAPIView")
                return Response(
                    {"error": "date parameter is required (YYYY-MM-DD format)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
            except ValueError:
                logger.info(f"Invalid date format received: {date_param}")
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use date-based filtering
            excluded_staff_ids = get_excluded_staff()
            staff = (
                Staff.objects.active_on_date(target_date)
                .exclude(Q(is_staff=True) | Q(id__in=excluded_staff_ids))
                .order_by("first_name", "last_name")
            )

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
                            Decimal(member.wage_rate)
                            if member.wage_rate
                            else Decimal(0)
                        ),
                        "avatarUrl": None,  # TODO: add avatar logic
                    }
                )

            return Response({"staff": staff_data, "total_count": len(staff_data)})

        except Exception as e:
            logger.error(f"Error fetching staff list: {e}")

            persist_app_error(e)

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

            persist_app_error(e)

            return Response(
                {"error": "Failed to fetch jobs", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DailyTimesheetAPIView(APIView):
    """
    API endpoint for daily timesheet overview.
    Provides comprehensive daily summary using modern CostLine system.
    Supports weekend functionality when feature flag is enabled.

    Supports multiple URL patterns:
    - GET /timesheets/api/daily/ (today's data)
    - GET /timesheets/api/daily/{date}/ (specific date)
    - GET /timesheets/api/staff/{staff_id}/daily/ (staff detail today)
    - GET /timesheets/api/staff/{staff_id}/daily/?date={date} (specific)
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

            # Add weekend information to response
            weekend_enabled = self._is_weekend_enabled()
            is_weekend = target_date.weekday() >= 5
            summary_data["weekend_enabled"] = weekend_enabled
            summary_data["is_weekend"] = is_weekend
            summary_data["day_type"] = "weekend" if is_weekend else "weekday"

            # Serialize and return response
            serializer = DailyTimesheetSummarySerializer(summary_data)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in DailyTimesheetAPIView: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            persist_app_error(e)

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
                weekend_enabled = self._is_weekend_enabled()
                is_weekend = target_date.weekday() >= 5

                # Adjust scheduled hours based on weekend feature flag
                scheduled_hours = 0.0 if is_weekend else 8.0

                initials = f"{staff.first_name[0]}{staff.last_name[0]}".upper()
                staff_data = {
                    "staff_id": str(staff_id),
                    "staff_name": f"{staff.first_name} {staff.last_name}",
                    "staff_initials": initials,
                    "avatar_url": None,
                    "scheduled_hours": scheduled_hours,
                    "actual_hours": 0.0,
                    "billable_hours": 0.0,
                    "non_billable_hours": 0.0,
                    "total_revenue": 0.0,
                    "total_cost": 0.0,
                    "status": (
                        "Weekend" if is_weekend and not weekend_enabled else "No Entry"
                    ),
                    "status_class": (
                        "secondary" if is_weekend and not weekend_enabled else "danger"
                    ),
                    "billable_percentage": 0.0,
                    "completion_percentage": 0.0,
                    "job_breakdown": [],
                    "entry_count": 0,
                    "alerts": ["No timesheet entries for this date"],
                    "is_weekend": is_weekend,
                    "weekend_enabled": weekend_enabled,
                }
            else:
                # Add weekend information to existing staff data
                weekend_enabled = self._is_weekend_enabled()
                is_weekend = target_date.weekday() >= 5
                staff_data["is_weekend"] = is_weekend
                staff_data["weekend_enabled"] = weekend_enabled

            return Response(staff_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting staff daily detail: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            persist_app_error(e)

            return Response(
                {
                    "error": "Failed to get staff daily detail",
                    "details": (
                        str(e) if request.user.is_staff else "Internal server error"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TimesheetResponseMixin:
    def build_timesheet_response(self, request):
        """Builds the weekly timesheet response data with payroll fields."""
        try:
            start_str = request.query_params.get("start_date")
            if start_str:
                try:
                    start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Default to current week
                today = datetime.today().date()
                start_date = today - timedelta(days=today.weekday())

            # Check weekend feature flag
            weekend_enabled = self._is_weekend_enabled()

            weekly_data = WeeklyTimesheetService.get_weekly_overview(start_date)

            prev_week = start_date - timedelta(days=7)
            next_week = start_date + timedelta(days=7)
            weekly_data["navigation"] = {
                "prev_week_date": prev_week.isoformat(),
                "next_week_date": next_week.isoformat(),
                "current_week_date": start_date.isoformat(),
            }

            # Add feature flag info to response
            weekly_data["weekend_enabled"] = weekend_enabled
            weekly_data["week_type"] = "7-day" if weekend_enabled else "5-day"

            return Response(
                WeeklyTimesheetDataSerializer(weekly_data).data,
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error building weekly timesheet response: {e}")

            persist_app_error(e)

            return Response(
                {
                    "error": "Failed to build weekly timesheet response",
                    "details": (
                        str(e) if request.user.is_staff else "Internal server error"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _is_weekend_enabled(self):
        """Check if weekend timesheet functionality is enabled"""
        import os

        return os.getenv("WEEKEND_TIMESHEETS_ENABLED", "false").lower() == "true"


class WeeklyTimesheetAPIView(TimesheetResponseMixin, APIView):
    """
    Comprehensive weekly timesheet API endpoint using WeeklyTimesheetService.
    Provides weekly overview with payroll fields for Vue.js frontend.
    Supports both 5-day (Mon-Fri) and 7-day (Mon-Sun) modes via flag.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WeeklyTimesheetDataSerializer

    @extend_schema(
        summary="Weekly overview with payroll data (Mon–Sun/Mon–Fri)",
        parameters=[
            OpenApiParameter(
                "start_date",
                OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Monday of target week in YYYY-MM-DD format. "
                "Defaults to current week.",
            ),
        ],
        responses={
            200: WeeklyTimesheetDataSerializer,
            400: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
    )
    def get(self, request):
        """Return weekly timesheet data with payroll fields (5/7 days)."""
        return self.build_timesheet_response(request)

    @extend_schema(
        summary="Submit paid absence",
        request=OpenApiTypes.OBJECT,
        responses={
            201: OpenApiTypes.OBJECT,
            400: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
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

            persist_app_error(e)

            return Response(
                {
                    "error": "Failed to submit paid absence",
                    "details": (
                        str(e) if request.user.is_staff else "Internal server error"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreatePayRunAPIView(APIView):
    """API endpoint to create a pay run in Xero Payroll."""

    permission_classes = [IsAuthenticated]
    serializer_class = CreatePayRunRequestSerializer

    @extend_schema(
        summary="Create pay run for a week",
        request=CreatePayRunRequestSerializer,
        responses={
            201: CreatePayRunResponseSerializer,
            400: ClientErrorResponseSerializer,
            409: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
    )
    def post(self, request):
        """Create a new pay run for the specified week."""
        try:
            from apps.workflow.api.xero.payroll import create_pay_run

            data = request.data
            week_start_date_str = data.get("week_start_date")

            if not week_start_date_str:
                return Response(
                    {"error": "week_start_date is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Parse date
            try:
                week_start_date = datetime.strptime(
                    week_start_date_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create pay run (validates Monday, creates in Xero)
            pay_run_id = create_pay_run(week_start_date)

            # Calculate dates for response
            week_end_date = week_start_date + timedelta(days=6)
            payment_date = week_end_date + timedelta(days=3)

            return Response(
                {
                    "pay_run_id": pay_run_id,
                    "status": "Draft",
                    "period_start_date": week_start_date.isoformat(),
                    "period_end_date": week_end_date.isoformat(),
                    "payment_date": payment_date.isoformat(),
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            # Client errors (bad date, not Monday)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating pay run: {e}", exc_info=True)
            persist_app_error(e)

            # Check for conflict (draft already exists)
            error_msg = str(e)
            if "only be one draft pay run" in error_msg.lower():
                return Response({"error": error_msg}, status=status.HTTP_409_CONFLICT)

            return Response(
                {"error": f"Failed to create pay run: {error_msg}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PostWeekToXeroPayrollAPIView(APIView):
    """API endpoint to post a weekly timesheet to Xero Payroll."""

    permission_classes = [IsAuthenticated]
    serializer_class = PostWeekToXeroRequestSerializer

    @extend_schema(
        summary="Post weekly timesheet to Xero Payroll",
        request=PostWeekToXeroRequestSerializer,
        responses={
            200: PostWeekToXeroResponseSerializer,
            400: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
    )
    def post(self, request):
        """Post a week's timesheet to Xero Payroll."""
        data = request.data
        staff_id = data.get("staff_id")
        week_start_date_str = data.get("week_start_date")

        if not staff_id:
            return Response(
                {"error": "staff_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not week_start_date_str:
            return Response(
                {"error": "week_start_date is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse date
        try:
            week_start_date = datetime.strptime(week_start_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Post to Xero (service validates Monday, checks pay run status, posts data)
        result = PayrollSyncService.post_week_to_xero(staff_id, week_start_date)

        # Return appropriate HTTP status based on success
        if result["success"]:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
