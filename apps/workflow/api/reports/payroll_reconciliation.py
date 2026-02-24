import logging
from datetime import datetime
from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.serializers.core import StandardErrorSerializer
from apps.accounting.serializers.payroll_reconciliation_serializers import (
    PayrollReconciliationResponseSerializer,
)
from apps.accounting.services.payroll_reconciliation_service import (
    PayrollReconciliationService,
)
from apps.workflow.exceptions import AlreadyLoggedException
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


def _build_error_response(
    *, message: str, status_code: int, details: dict[str, Any] | None = None
) -> Response:
    payload: dict[str, Any] = {"error": message}
    if details is not None:
        payload["details"] = details

    serializer = StandardErrorSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data, status=status_code)


class PayrollReconciliationReport(APIView):
    """Weekly payroll reconciliation: Xero pay runs vs JM time CostLines."""

    serializer_class = PayrollReconciliationResponseSerializer

    @extend_schema(
        summary="Get payroll reconciliation report",
        description=(
            "Reconciles Xero pay runs against JM CostLine time entries "
            "for each week in the given date range."
        ),
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Inclusive start date (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Inclusive end date (YYYY-MM-DD).",
            ),
        ],
        responses={
            200: PayrollReconciliationResponseSerializer,
            400: StandardErrorSerializer,
            500: StandardErrorSerializer,
        },
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return _build_error_response(
                message="start_date and end_date query params required (YYYY-MM-DD)",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return _build_error_response(
                message="Invalid date format, use YYYY-MM-DD",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if start_date > end_date:
            return _build_error_response(
                message="start_date must be before end_date",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = PayrollReconciliationService.get_reconciliation_data(
                start_date=start_date, end_date=end_date
            )

            response_serializer = PayrollReconciliationResponseSerializer(data=data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except AlreadyLoggedException as exc:
            logger.error("Payroll reconciliation error: %s", exc.original)
            return _build_error_response(
                message=(
                    "Internal server error occurred while generating "
                    "payroll reconciliation report"
                ),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.error("Payroll reconciliation error: %s", exc)
            app_error = persist_app_error(
                exc,
                additional_context={"operation": "payroll_reconciliation"},
            )
            return _build_error_response(
                message=(
                    "Internal server error occurred while generating "
                    "payroll reconciliation report"
                ),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error_id": str(app_error.id)},
            )
