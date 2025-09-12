from datetime import datetime
from logging import getLogger
from typing import Any

from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.serializers import (
    StaffPerformanceErrorResponseSerializer,
    StaffPerformanceResponseSerializer,
)
from apps.accounting.services import StaffPerformanceService
from apps.workflow.services.error_persistence import persist_app_error

logger = getLogger(__name__)


class StaffPerformanceTemplateView(TemplateView):
    """View for rendering the Staff Performance page"""

    template_name = "reports/staff_performance.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Staff Performance Report"
        return context


class StaffPerformanceSummaryAPIView(APIView):
    """API endpoint for staff performance summary (all staff)"""

    serializer_class = StaffPerformanceResponseSerializer

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            # Validate query parameters
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")

            if not start_date_str or not end_date_str:
                error_data = {
                    "error": (
                        "Both start_date and end_date query parameters are required"
                    )
                }
                error_serializer = StaffPerformanceErrorResponseSerializer(
                    data=error_data
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError as exc:
                error_data = {"error": "Invalid date format. Use YYYY-MM-DD format"}
                error_serializer = StaffPerformanceErrorResponseSerializer(
                    data=error_data
                )
                error_serializer.is_valid(raise_exception=True)
                persist_app_error(
                    exc,
                    additional_context={
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                    },
                )
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            if start_date > end_date:
                error_data = {"error": "start_date must be before or equal to end_date"}
                error_serializer = StaffPerformanceErrorResponseSerializer(
                    data=error_data
                )
                error_serializer.is_valid(raise_exception=True)
                persist_app_error(
                    ValueError("start_date must be before or equal to end_date"),
                    additional_context={
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                    },
                )
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            # Get staff performance data
            performance_data = StaffPerformanceService.get_staff_performance_data(
                start_date=start_date, end_date=end_date
            )

            # Serialize and return response
            response_serializer = StaffPerformanceResponseSerializer(
                data=performance_data
            )
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.error(f"Error in staff performance summary API: {str(exc)}")
            persist_app_error(
                exc,
                additional_context={
                    "operation": "staff_performance_summary",
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                },
            )
            error_data = {
                "error": (
                    "Internal server error occurred while generating staff "
                    "performance report"
                )
            }
            error_serializer = StaffPerformanceErrorResponseSerializer(data=error_data)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StaffPerformanceDetailAPIView(APIView):
    """API endpoint for individual staff performance detail"""

    serializer_class = StaffPerformanceResponseSerializer

    def get(
        self, request: Request, staff_id: str, *args: Any, **kwargs: Any
    ) -> Response:
        try:
            # Validate query parameters
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")

            if not start_date_str or not end_date_str:
                error_data = {
                    "error": (
                        "Both start_date and end_date query parameters are required"
                    )
                }
                error_serializer = StaffPerformanceErrorResponseSerializer(
                    data=error_data
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                error_data = {"error": "Invalid date format. Use YYYY-MM-DD format"}
                error_serializer = StaffPerformanceErrorResponseSerializer(
                    data=error_data
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            if start_date > end_date:
                error_data = {"error": "start_date must be before or equal to end_date"}
                error_serializer = StaffPerformanceErrorResponseSerializer(
                    data=error_data
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            # Get individual staff performance data with job breakdown
            performance_data = StaffPerformanceService.get_staff_performance_data(
                start_date=start_date, end_date=end_date, staff_id=staff_id
            )

            # Check if staff was found
            if not performance_data["staff"]:
                error_data = {
                    "error": f"No performance data found for staff ID: {staff_id}"
                }
                error_serializer = StaffPerformanceErrorResponseSerializer(
                    data=error_data
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

            # Serialize and return response
            response_serializer = StaffPerformanceResponseSerializer(
                data=performance_data
            )
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.error(f"Error in staff performance detail API: {str(exc)}")
            persist_app_error(
                exc,
                additional_context={
                    "operation": "staff_performance_detail",
                    "staff_id": staff_id,
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                },
            )
            error_data = {
                "error": (
                    "Internal server error occurred while generating staff "
                    "performance report"
                )
            }
            error_serializer = StaffPerformanceErrorResponseSerializer(data=error_data)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
