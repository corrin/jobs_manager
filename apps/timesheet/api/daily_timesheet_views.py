"""
Daily Timesheet API Views

REST API endpoints for daily timesheet functionality using DRF
"""

import logging
from datetime import date, datetime

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.timesheet.serializers import DailyTimesheetSummarySerializer
from apps.timesheet.services import DailyTimesheetService

logger = logging.getLogger(__name__)


@api_view(["GET"])
def daily_timesheet_summary(request, target_date: str = None):
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
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            parsed_date = date.today()

        logger.info(f"Getting daily timesheet summary for {parsed_date}")

        # Get data from service
        summary_data = DailyTimesheetService.get_daily_summary(parsed_date)

        # Serialize response
        serializer = DailyTimesheetSummarySerializer(summary_data)

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in daily_timesheet_summary: {e}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def staff_daily_detail(request, staff_id: str, target_date: str = None):
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
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            parsed_date = date.today()

        logger.info(f"Getting staff detail for {staff_id} on {parsed_date}")

        # Get full summary and extract staff data
        summary_data = DailyTimesheetService.get_daily_summary(parsed_date)

        # Find specific staff
        staff_data = next(
            (s for s in summary_data["staff_data"] if s["staff_id"] == staff_id), None
        )

        if not staff_data:
            return Response(
                {"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(staff_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in staff_daily_detail: {e}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
