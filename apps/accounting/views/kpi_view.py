import traceback
from datetime import date
from logging import getLogger

from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.services import KPIService

logger = getLogger(__name__)


class KPICalendarTemplateView(TemplateView):
    """View for rendering the KPI Calendar page"""

    template_name = "reports/kpi_calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "KPI Calendar"
        return context


class KPICalendarAPIView(APIView):
    """API Endpoint to provide KPI data for calendar display"""

    def get(self, request, *args, **kwargs):
        try:
            year = str(request.query_params.get("year", date.today().year))
            month = str(request.query_params.get("month", date.today().month))

            if not year.isdigit() or not month.isdigit():
                return Response(
                    {
                        "error": "The provided query param 'year' or 'month' is "
                        "not in the correct format (not a digit). Please try again."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            year = int(year)
            month = int(month)

            if not 1 <= month <= 12 or not 2000 <= year <= 2100:
                return Response(
                    {
                        "error": "Year or month out of valid range. "
                        "Please check the query params."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            calendar_data = KPIService.get_calendar_data(year, month)

            return Response(calendar_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "KPI Calendar API Error: %s\n%s", str(e), traceback.format_exc()
            )
            return Response(
                {"error": f"Error obtaining calendar data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
