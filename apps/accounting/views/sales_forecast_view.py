"""
Sales Forecast Report View

Provides monthly sales comparison between Xero invoices and Job Manager revenue.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from logging import getLogger
from typing import Any, Dict, List

from django.db.models import Q, Sum
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.models import Invoice
from apps.job.models import CostLine

logger = getLogger(__name__)


class SalesForecastTemplateView(TemplateView):
    """View for rendering the Sales Forecast page"""

    template_name = "reports/sales_forecast.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Sales Forecast"
        return context


class SalesForecastAPIView(APIView):
    """
    API Endpoint to compare monthly sales between Xero and Job Manager.

    Returns a table with:
    - Month
    - Xero Sales (total of invoices for that month)
    - JM Sales (total revenue attributed to that month via accounting_date)
    """

    @extend_schema(
        summary="Get monthly sales forecast data",
        description=(
            "Returns monthly sales comparison between Xero invoices and "
            "Job Manager revenue for all months with data"
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "months": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "month": {"type": "string", "example": "2025-01"},
                                "month_label": {
                                    "type": "string",
                                    "example": "Jan 2025",
                                },
                                "xero_sales": {
                                    "type": "number",
                                    "example": 125000.50,
                                },
                                "jm_sales": {"type": "number", "example": 118500.75},
                                "variance": {"type": "number", "example": 6499.75},
                                "variance_pct": {"type": "number", "example": 5.48},
                            },
                        },
                    },
                },
            },
            500: {
                "type": "object",
                "properties": {"error": {"type": "string"}},
            },
        },
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Get monthly sales comparison data"""
        try:
            # Get Xero sales by month (from Invoice.date)
            xero_sales_by_month = self._get_xero_sales_by_month()

            # Get JM sales by month (from CostLine.accounting_date)
            jm_sales_by_month = self._get_jm_sales_by_month()

            # Combine all months that have data from either source (newest first)
            all_months = sorted(
                set(xero_sales_by_month.keys()) | set(jm_sales_by_month.keys()),
                reverse=True,
            )

            # Build response data
            result: List[Dict[str, Any]] = []
            for month_key in all_months:
                xero_sales = float(xero_sales_by_month.get(month_key, Decimal("0")))
                jm_sales = float(jm_sales_by_month.get(month_key, Decimal("0")))
                variance = xero_sales - jm_sales
                variance_pct = (variance / xero_sales * 100) if xero_sales != 0 else 0.0

                # Parse month_key (YYYY-MM format) to create label
                year, month = month_key.split("-")
                month_date = date(int(year), int(month), 1)
                month_label = month_date.strftime("%b %Y")

                result.append(
                    {
                        "month": month_key,
                        "month_label": month_label,
                        "xero_sales": xero_sales,
                        "jm_sales": jm_sales,
                        "variance": variance,
                        "variance_pct": round(variance_pct, 2),
                    }
                )

            return Response({"months": result}, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.exception("Error generating sales forecast report")
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_xero_sales_by_month(self) -> Dict[str, Decimal]:
        """
        Get total invoice amounts grouped by month from Xero invoices.

        Returns:
            Dict mapping 'YYYY-MM' to total invoice amount
        """
        # Query all invoices, excluding DRAFT, DELETED, and VOIDED
        invoices = (
            Invoice.objects.filter(
                ~Q(status__in=["DRAFT", "DELETED", "VOIDED"]),
                date__isnull=False,
            )
            .values("date")
            .annotate(total=Sum("total_incl_tax"))
        )

        sales_by_month: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for invoice in invoices:
            invoice_date = invoice["date"]
            month_key = invoice_date.strftime("%Y-%m")
            sales_by_month[month_key] += invoice["total"] or Decimal("0")

        return dict(sales_by_month)

    def _get_jm_sales_by_month(self) -> Dict[str, Decimal]:
        """
        Get total revenue grouped by month from Job Manager cost lines.

        Revenue is calculated from CostLine.total_rev using accounting_date.

        Returns:
            Dict mapping 'YYYY-MM' to total revenue
        """
        # Query actual cost lines only (not estimates or quotes)
        cost_lines = CostLine.objects.filter(
            cost_set__kind="actual",
            accounting_date__isnull=False,
            unit_rev__isnull=False,
            quantity__isnull=False,
        ).values("accounting_date", "unit_rev", "quantity")

        sales_by_month: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for line in cost_lines:
            accounting_date = line["accounting_date"]
            month_key = accounting_date.strftime("%Y-%m")
            total_rev = (
                Decimal(str(line["unit_rev"])) * Decimal(str(line["quantity"]))
                if line["unit_rev"] and line["quantity"]
                else Decimal("0")
            )
            sales_by_month[month_key] += total_rev

        return dict(sales_by_month)
