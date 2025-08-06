import json
import logging
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from apps.job.utils import get_active_jobs
from apps.purchasing.models import Stock
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger(__name__)


@login_required
def use_stock_view(request, job_id=None):
    """
    View for the Use Stock page.
    Displays a list of available stock items and allows searching and consuming stock.

    Args:
        request: The HTTP request
        job_id: Optional job ID to pre-select in the dropdown
            (can be provided in URL path or query string)
    """
    # Check if job_id is provided in query string
    if not job_id and request.GET.get("job_id"):
        job_id = request.GET.get("job_id")

    # Get all active stock items
    stock_items = Stock.objects.filter(is_active=True).order_by("description")

    # Get the stock holding job and active jobs
    stock_holding_job = Stock.get_stock_holding_job()
    active_jobs = (
        get_active_jobs().exclude(id=stock_holding_job.id).order_by("job_number")
    )

    # Get company defaults for markup calculation
    company_defaults = CompanyDefaults.get_instance()
    materials_markup = company_defaults.materials_markup

    # Prepare stock data for AG Grid
    stock_data = []
    for item in stock_items:
        # Calculate unit revenue using the materials markup
        unit_revenue = item.unit_cost * (1 + materials_markup)
        total_value = item.quantity * item.unit_cost

        stock_data.append(
            {
                "id": str(item.id),  # Convert UUID to string
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_cost": float(item.unit_cost),
                "unit_revenue": float(unit_revenue),
                "total_value": float(total_value),
                "metal_type": item.metal_type,
                "alloy": item.alloy or "",
                "specifics": item.specifics or "",
                "location": item.location or "",
            }
        )

    # If job_id is provided, validate that it exists in active jobs
    if job_id:
        target_id = UUID(job_id)
        if not any(j.id == target_id for j in active_jobs):
            raise ValueError(f"Job {target_id} not found in active jobs")

    context = {
        "title": "Use Stock",
        "stock_items": stock_items,
        "stock_data_json": json.dumps(stock_data),
        "active_jobs": active_jobs,
        "stock_holding_job": stock_holding_job,
        "default_job_id": str(job_id) if job_id else None,
    }

    return render(request, "purchasing/use_stock.html", context)


def search_available_stock_api(request):
    """
    API endpoint to search available stock items for autocomplete.
    Searches active stock items matching the search term.
    Relies on is_active=True implicitly meaning quantity > 0 and
    item is available for consumption (likely linked to Worker Admin job).
    """
    search_term = request.GET.get("q", "").strip()
    limit = int(request.GET.get("limit", 25))  # Limit results

    results = []  # Default to empty list

    if search_term:
        # Filter only by active status and description
        # Assumes is_active=True implies quantity > 0 and correct job allocation
        matching_stock = (
            Stock.objects.filter(is_active=True, description__icontains=search_term)
            .select_related("job")
            .order_by("description")[:limit]
        )  # Keep select_related for job name display

        # Serialize the data for autocomplete
        results = [
            {
                "id": str(item.id),
                # Display job name in text for clarity if needed, assuming active stock is under Worker Admin
                "text": f"{item.description} (Avail: {item.quantity}, Loc: {item.job.name if item.job else 'N/A'})",
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_cost": float(item.unit_cost),
            }
            for item in matching_stock
        ]

    # Return results directly, matching ClientSearch response structure
    return JsonResponse({"results": results})
