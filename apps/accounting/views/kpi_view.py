import traceback
from datetime import date
from logging import getLogger
from typing import Any, Dict

from django.views.generic import TemplateView
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.serializers import (
    KPICalendarDataSerializer,
    StandardErrorSerializer,
)
from apps.accounting.services import KPIService

logger = getLogger(__name__)


class KPICalendarTemplateView(TemplateView):
    """View for rendering the KPI Calendar page"""

    template_name = "reports/kpi_calendar.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["page_title"] = "KPI Calendar"
        return context


class KPICalendarAPIView(APIView):
    """API Endpoint to provide KPI data for calendar display"""

    serializer_class = KPICalendarDataSerializer

    @extend_schema(
        summary="Get KPI calendar data",
        description="Returns aggregated KPIs for display in calendar",
        parameters=[
            OpenApiParameter(
                name="year",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Year (YYYY). Defaults to current year.",
            ),
            OpenApiParameter(
                name="month",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Month (1-12). Defaults to current month.",
            ),
        ],
        responses={
            200: KPICalendarDataSerializer,
            400: StandardErrorSerializer,
            500: StandardErrorSerializer,
        },
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            print(f"🔍 KPI request received - all params: {dict(request.query_params)}")

            year_str = str(request.query_params.get("year", date.today().year))
            month_str = str(request.query_params.get("month", date.today().month))

            print(f"📅 KPI request - year_str: {year_str}, month_str: {month_str}")

            if not year_str.isdigit() or not month_str.isdigit():
                error_serializer = StandardErrorSerializer(
                    data={
                        "error": "The provided query param 'year' or 'month' is "
                        "not in the correct format (not a digit). Please try again."
                    }
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            year = int(year_str)
            month = int(month_str)

            print(f"📅 Parsed KPI request - year: {year}, month: {month}")

            if not 1 <= month <= 12 or not 2000 <= year <= 2100:
                error_serializer = StandardErrorSerializer(
                    data={
                        "error": "Year or month out of valid range. "
                        "Please check the query params."
                    }
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            calendar_data = KPIService.get_calendar_data(year, month)

            # Validate and serialize the response
            response_serializer = KPICalendarDataSerializer(data=calendar_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "KPI Calendar API Error: %s\n%s", str(e), traceback.format_exc()
            )
            error_serializer = StandardErrorSerializer(
                data={"error": f"Error obtaining calendar data: {str(e)}"}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
