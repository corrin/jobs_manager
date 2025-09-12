"""
Daily Timesheet API Views

REST API endpoints for daily timesheet functionality using DRF
"""

import logging
from datetime import date, datetime

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.timesheet.serializers.daily_timesheet_serializers import (
    DailyTimesheetSummarySerializer,
    TimesheetErrorResponseSerializer,
)
from apps.timesheet.services import DailyTimesheetService

logger = logging.getLogger(__name__)


class DailyTimesheetSummaryAPIView(APIView):
    """
    Get daily timesheet summary for all staff

    GET /timesheet/api/daily/<target_date>/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DailyTimesheetSummarySerializer

    @extend_schema(operation_id="getDailyTimesheetSummaryByDate")
    def get(self, request, target_date: str = None):
        """
        Get daily timesheet summary for all staff

        Args:
            target_date: Date in YYYY-MM-DD format (optional, defaults to today)

        Returns:
            JSON response with daily timesheet data
        """
        try:
            # Parse date or use today
            if target_date:
                try:
                    parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                except ValueError:
                    error_response = {"error": "Invalid date format. Use YYYY-MM-DD"}
                    error_serializer = TimesheetErrorResponseSerializer(
                        data=error_response
                    )
                    error_serializer.is_valid(raise_exception=True)
                    return Response(
                        error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                parsed_date = date.today()

            logger.info(f"Getting daily timesheet summary for {parsed_date}")

            # Get data from service
            summary_data = DailyTimesheetService.get_daily_summary(parsed_date)

            # Serialize response
            serializer = DailyTimesheetSummarySerializer(data=summary_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting daily timesheet summary: {e}")
            error_response = {"error": "Failed to get daily timesheet summary"}
            error_serializer = TimesheetErrorResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StaffDailyDetailAPIView(APIView):
    """
    Get detailed timesheet data for a specific staff member

    GET /timesheet/api/staff/<staff_id>/daily/<target_date>/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DailyTimesheetSummarySerializer  # Reusing the same serializer

    @extend_schema(operation_id="getStaffDailyTimesheetDetailByDate")
    def get(self, request, staff_id: str, target_date: str = None):
        """
        Get detailed timesheet data for a specific staff member

        Args:
            staff_id: Staff member ID
            target_date: Date in YYYY-MM-DD format (optional, defaults to today)

        Returns:
            JSON response with staff timesheet detail
        """
        try:
            # Parse date or use today
            if target_date:
                try:
                    parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                except ValueError:
                    error_response = {"error": "Invalid date format. Use YYYY-MM-DD"}
                    error_serializer = TimesheetErrorResponseSerializer(
                        data=error_response
                    )
                    error_serializer.is_valid(raise_exception=True)
                    return Response(
                        error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                parsed_date = date.today()

            logger.info(f"Getting staff detail for {staff_id} on {parsed_date}")

            # Get full summary and extract staff data
            summary_data = DailyTimesheetService.get_daily_summary(parsed_date)

            # Find specific staff
            staff_data = next(
                (s for s in summary_data["staff_data"] if s["staff_id"] == staff_id),
                None,
            )

            if not staff_data:
                error_response = {"error": "Staff member not found"}
                error_serializer = TimesheetErrorResponseSerializer(data=error_response)
                error_serializer.is_valid(raise_exception=True)
                return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

            return Response(staff_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in staff_daily_detail: {e}")
            error_response = {"error": "Internal server error"}
            error_serializer = TimesheetErrorResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
