"""
Sales Forecast Report View

Provides monthly sales comparison between Xero invoices and Job Manager revenue.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from logging import getLogger
from typing import Any, Dict, List, Optional

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
                                "date": {"type": "string", "format": "date"},
                                "client_name": {"type": "string"},
                                "job_number": {"type": "integer", "nullable": True},
                                "job_name": {"type": "string", "nullable": True},
                                "invoice_numbers": {"type": "string", "nullable": True},
                                "total_invoiced": {"type": "number"},
                                "job_revenue": {"type": "number"},
                                "variance": {"type": "number"},
                                "job_id": {
                                    "type": "string",
                                    "format": "uuid",
                                    "nullable": True,
                                },
                                "job_start_date": {
                                    "type": "string",
                                    "format": "date",
                                    "nullable": True,
                                },
                                "note": {"type": "string", "nullable": True},
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

        def build_row(
            row_date: str,
            client_name: str,
            job_number: Optional[int],
            job_name: Optional[str],
            invoice_numbers: Optional[str],
            total_invoiced: float,
            job_revenue: float,
            job_id: Optional[str],
            job_start_date: Optional[str] = None,
            note: Optional[str] = None,
        ) -> Dict[str, Any]:
            return {
                "date": row_date,
                "client_name": client_name,
                "job_number": job_number,
                "job_name": job_name,
                "invoice_numbers": invoice_numbers,
                "total_invoiced": round(total_invoiced, 2),
                "job_revenue": round(job_revenue, 2),
                "variance": round(total_invoiced - job_revenue, 2),
                "job_id": job_id,
                "job_start_date": job_start_date,
                "note": note,
            }

        def get_job_note(job: Optional[Job], match_type: str) -> Optional[str]:
            """Generate note for a row. Job characteristics first, then match status."""
            if job and job.shop_job:
                return "Shop job"
            if job:
                start = job.start_date
                end = job.completion_date
                if start and end and (start.year, start.month) != (end.year, end.month):
                    return "Multi-month"
            if match_type == "xero_only":
                return "Xero only"
            if match_type == "jm_only":
                return "JM only"
            return None

        # Build rows for jobs with invoices (matched)
        for job_id, job_invoices in invoices_by_job.items():
            job = job_invoices[0].job
            monthly_revenue = float(jobs_with_revenue.get(job_id, Decimal("0")))
            start_date = job.start_date
            rows.append(
                build_row(
                    row_date=job_invoices[0].date.isoformat(),
                    client_name=job.client.name,
                    job_number=job.job_number,
                    job_name=job.name,
                    invoice_numbers=", ".join(inv.number for inv in job_invoices),
                    total_invoiced=sum(
                        float(inv.total_incl_tax) for inv in job_invoices
                    ),
                    job_revenue=monthly_revenue,
                    job_id=str(job.id),
                    job_start_date=start_date.isoformat() if start_date else None,
                    note=get_job_note(job, "matched"),
                )
            )

        # Build rows for unlinked invoices (xero_only)
        for invoice in unlinked_invoices:
            rows.append(
                build_row(
                    row_date=invoice.date.isoformat(),
                    client_name=invoice.client.name,
                    job_number=None,
                    job_name=None,
                    invoice_numbers=invoice.number,
                    total_invoiced=float(invoice.total_incl_tax),
                    job_revenue=0.0,
                    job_id=None,
                    note=get_job_note(None, "xero_only"),
                )
            )

        # Build rows for jobs with revenue but no invoices (jm_only)
        for job_id in jobs_with_revenue.keys():
            if job_id in jobs_with_invoices:
                continue
            job = Job.objects.select_related("client").get(id=job_id)
            monthly_revenue = float(jobs_with_revenue[job_id])
            start_date = job.start_date
            completion = job.completion_date
            rows.append(
                build_row(
                    row_date=completion.isoformat() if completion else None,
                    client_name=job.client.name,
                    job_number=job.job_number,
                    job_name=job.name,
                    invoice_numbers=None,
                    total_invoiced=0.0,
                    job_revenue=monthly_revenue,
                    job_id=str(job.id),
                    job_start_date=start_date.isoformat() if start_date else None,
                    note=get_job_note(job, "jm_only"),
                )
            )

        rows.sort(key=lambda r: r["date"] or "")

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

        # Only return jobs with non-zero revenue
        return {k: v for k, v in jobs_revenue.items() if v != 0}
