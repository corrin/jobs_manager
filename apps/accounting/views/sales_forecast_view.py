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
                                "invoices": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string", "format": "uuid"},
                                            "number": {
                                                "type": "string",
                                                "example": "INV-0001",
                                            },
                                            "date": {
                                                "type": "string",
                                                "format": "date",
                                            },
                                            "total_incl_tax": {"type": "number"},
                                        },
                                    },
                                },
                                "total_invoiced": {"type": "number"},
                                "job": {
                                    "type": "object",
                                    "nullable": True,
                                    "properties": {
                                        "id": {"type": "string", "format": "uuid"},
                                        "job_number": {"type": "integer"},
                                        "name": {"type": "string"},
                                        "revenue": {"type": "number"},
                                    },
                                },
                                "client_name": {"type": "string"},
                                "match_type": {
                                    "type": "string",
                                    "enum": ["matched", "xero_only", "jm_only"],
                                },
                                "variance": {"type": "number"},
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
        """Build comparison rows for the given month.

        One row per job (aggregating all invoices for that job) or per unlinked invoice.
        """
        rows: List[Dict[str, Any]] = []

        # Get invoices for this month
        invoices = Invoice.objects.filter(
            ~Q(status__in=["DRAFT", "DELETED", "VOIDED"]),
            date__year=year,
            date__month=month,
        ).select_related("client", "job", "job__client")

        # Get jobs with actual revenue in this month
        jobs_with_revenue = self._get_jobs_with_revenue(year, month)

        # Group invoices by job_id (None for unlinked invoices)
        invoices_by_job: Dict[str, List[Invoice]] = defaultdict(list)
        unlinked_invoices: List[Invoice] = []

        for invoice in invoices:
            if invoice.job:
                invoices_by_job[str(invoice.job.id)].append(invoice)
            else:
                unlinked_invoices.append(invoice)

        # Track all job IDs that have invoices
        jobs_with_invoices = set(invoices_by_job.keys())

        # Build rows for jobs with invoices (matched)
        for job_id, job_invoices in invoices_by_job.items():
            job = job_invoices[0].job  # All invoices in this list have the same job
            total_invoiced = sum(float(inv.total_incl_tax) for inv in job_invoices)
            job_revenue = float(jobs_with_revenue.get(job_id, Decimal("0")))

            rows.append(
                {
                    "invoices": [
                        {
                            "id": str(inv.id),
                            "number": inv.number,
                            "date": inv.date.isoformat(),
                            "total_incl_tax": float(inv.total_incl_tax),
                        }
                        for inv in job_invoices
                    ],
                    "total_invoiced": round(total_invoiced, 2),
                    "job": {
                        "id": str(job.id),
                        "job_number": job.job_number,
                        "name": job.name,
                        "revenue": job_revenue,
                    },
                    "client_name": job.client.name if job.client else None,
                    "match_type": "matched",
                    "variance": round(total_invoiced - job_revenue, 2),
                }
            )

        # Build rows for unlinked invoices (xero_only)
        for invoice in unlinked_invoices:
            xero_amount = float(invoice.total_incl_tax)
            rows.append(
                {
                    "invoices": [
                        {
                            "id": str(invoice.id),
                            "number": invoice.number,
                            "date": invoice.date.isoformat(),
                            "total_incl_tax": xero_amount,
                        }
                    ],
                    "total_invoiced": round(xero_amount, 2),
                    "job": None,
                    "client_name": invoice.client.name if invoice.client else None,
                    "match_type": "xero_only",
                    "variance": round(xero_amount, 2),
                }
            )

        # Build rows for jobs with revenue but no invoices (jm_only)
        for job_id, revenue in jobs_with_revenue.items():
            if job_id not in jobs_with_invoices:
                job = Job.objects.select_related("client").get(id=job_id)
                jm_amount = float(revenue)
                rows.append(
                    {
                        "invoices": [],
                        "total_invoiced": 0.0,
                        "job": {
                            "id": str(job.id),
                            "job_number": job.job_number,
                            "name": job.name,
                            "revenue": jm_amount,
                        },
                        "client_name": job.client.name if job.client else None,
                        "match_type": "jm_only",
                        "variance": round(-jm_amount, 2),
                    }
                )

        # Sort: matched first, then xero_only, then jm_only
        # Within each group, sort by job number (or invoice number for xero_only)
        sort_order = {"matched": 0, "xero_only": 1, "jm_only": 2}

        def sort_key(row: Dict[str, Any]) -> tuple:
            match_type = row["match_type"]
            if row["job"]:
                return (sort_order[match_type], row["job"]["job_number"])
            return (sort_order[match_type], row["invoices"][0]["number"])

        rows.sort(key=sort_key)

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
