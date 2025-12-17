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
from apps.job.models import CostLine, Job

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
        )

        sales_by_month: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for line in cost_lines:
            month_key = line.accounting_date.strftime("%Y-%m")
            sales_by_month[month_key] += line.total_rev

        return dict(sales_by_month)


class SalesForecastMonthDetailAPIView(APIView):
    """
    API Endpoint to drill down into a specific month's sales data.

    Returns matched and unmatched invoices/jobs for comparison.
    """

    @extend_schema(
        summary="Get month detail for sales forecast",
        description=(
            "Returns detailed invoice and job data for a specific month, "
            "showing matched pairs and unmatched items"
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "example": "2025-01"},
                    "month_label": {"type": "string", "example": "Jan 2025"},
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "invoice": {"type": "object", "nullable": True},
                                "job": {"type": "object", "nullable": True},
                                "match_type": {
                                    "type": "string",
                                    "enum": ["matched", "xero_only", "jm_only"],
                                },
                            },
                        },
                    },
                },
            },
            400: {
                "type": "object",
                "properties": {"error": {"type": "string"}},
            },
        },
    )
    def get(self, request: Request, month: str, *args: Any, **kwargs: Any) -> Response:
        """Get detailed invoice/job comparison for a specific month"""
        # Validate month format (YYYY-MM)
        if not month or len(month) != 7 or month[4] != "-":
            return Response(
                {"error": "Invalid month format. Use YYYY-MM"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year, month_num = month.split("-")
            year_int = int(year)
            month_int = int(month_num)
            if month_int < 1 or month_int > 12:
                raise ValueError("Month must be 1-12")
            month_date = date(year_int, month_int, 1)
            month_label = month_date.strftime("%b %Y")
        except ValueError as e:
            return Response(
                {"error": f"Invalid month: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rows = self._build_comparison_rows(year_int, month_int)

            return Response(
                {
                    "month": month,
                    "month_label": month_label,
                    "rows": rows,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.exception("Error generating sales forecast month detail")
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _build_comparison_rows(self, year: int, month: int) -> List[Dict[str, Any]]:
        """Build comparison rows for the given month."""
        rows: List[Dict[str, Any]] = []

        # Get invoices for this month
        invoices = Invoice.objects.filter(
            ~Q(status__in=["DRAFT", "DELETED", "VOIDED"]),
            date__year=year,
            date__month=month,
        ).select_related("client", "job")

        # Get jobs with actual revenue in this month
        jobs_with_revenue = self._get_jobs_with_revenue(year, month)

        # Track which jobs have been matched to invoices
        matched_job_ids = set()

        # Process invoices
        for invoice in invoices:
            invoice_data = {
                "id": str(invoice.id),
                "number": invoice.number,
                "date": invoice.date.isoformat(),
                "client_name": invoice.client.name if invoice.client else None,
                "total_incl_tax": float(invoice.total_incl_tax),
                "status": invoice.status,
            }

            if invoice.job and str(invoice.job.id) in jobs_with_revenue:
                # Matched: invoice linked to job with revenue this month
                job = invoice.job
                job_revenue = jobs_with_revenue[str(job.id)]
                matched_job_ids.add(str(job.id))

                rows.append(
                    {
                        "invoice": invoice_data,
                        "job": {
                            "id": str(job.id),
                            "job_number": job.job_number,
                            "name": job.name,
                            "client_name": job.client.name if job.client else None,
                            "month_revenue": float(job_revenue),
                        },
                        "match_type": "matched",
                    }
                )
            elif invoice.job:
                # Invoice linked to job, but job has no revenue this month
                job = invoice.job
                rows.append(
                    {
                        "invoice": invoice_data,
                        "job": {
                            "id": str(job.id),
                            "job_number": job.job_number,
                            "name": job.name,
                            "client_name": job.client.name if job.client else None,
                            "month_revenue": 0.0,
                        },
                        "match_type": "matched",
                    }
                )
                matched_job_ids.add(str(job.id))
            else:
                # Xero only: invoice without job link
                rows.append(
                    {
                        "invoice": invoice_data,
                        "job": None,
                        "match_type": "xero_only",
                    }
                )

        # Add JM only jobs (jobs with revenue but no invoice this month)
        for job_id, revenue in jobs_with_revenue.items():
            if job_id not in matched_job_ids:
                job = Job.objects.select_related("client").get(id=job_id)
                rows.append(
                    {
                        "invoice": None,
                        "job": {
                            "id": str(job.id),
                            "job_number": job.job_number,
                            "name": job.name,
                            "client_name": job.client.name if job.client else None,
                            "month_revenue": float(revenue),
                        },
                        "match_type": "jm_only",
                    }
                )

        # Sort: matched first, then xero_only, then jm_only
        sort_order = {"matched": 0, "xero_only": 1, "jm_only": 2}
        rows.sort(
            key=lambda r: (
                sort_order[r["match_type"]],
                r.get("invoice", {}).get("number", "") or "",
            )
        )

        return rows

    def _get_jobs_with_revenue(self, year: int, month: int) -> Dict[str, Decimal]:
        """Get jobs that have actual revenue in the given month."""
        cost_lines = CostLine.objects.filter(
            cost_set__kind="actual",
            accounting_date__year=year,
            accounting_date__month=month,
        ).select_related("cost_set__job")

        jobs_revenue: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for line in cost_lines:
            job_id = str(line.cost_set.job.id)
            jobs_revenue[job_id] += line.total_rev

        return dict(jobs_revenue)
