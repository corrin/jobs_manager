import logging
import os
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.client.models import Client
from apps.job.models import Job
from apps.purchasing.models import Stock
from apps.workflow.authentication import service_api_key_required

from .models import SupplierPriceList, SupplierProduct

# Temporarily commented out to debug import issues
# from .services.ai_price_extraction import extract_price_data
# from .services.product_parser import (
#     create_mapping_record,
#     populate_all_mappings_with_llm,
# )

logger = logging.getLogger(__name__)


@login_required
def index(request):
    return render(request, "quoting/index.html")


class UploadSupplierPricingView(TemplateView):
    template_name = "purchasing/upload_supplier_pricing.html"


class UploadPriceListView(LoginRequiredMixin, TemplateView):
    """
    View for uploading supplier price lists.

    Provides interface for uploading price list files and basic processing.
    """

    template_name = "quoting/upload_price_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Upload Supplier Price List"
        return context


@require_http_methods(["POST"])
def extract_supplier_price_list_data_view(request):
    """
    Extract data from a supplier price list using Gemini.
    """
    try:
        if "price_list_file" not in request.FILES:
            return JsonResponse(
                {"success": False, "error": "No price list file uploaded."}, status=400
            )

        price_list_file = request.FILES["price_list_file"]

        # Save the file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(price_list_file.name)[1]
        ) as temp_file:
            for chunk in price_list_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        content_type = price_list_file.content_type

        # extracted_data, error = extract_price_data(temp_file_path, content_type)
        # Temporary placeholder for debugging
        extracted_data, error = {}, "Service temporarily disabled for debugging"

        # Clean up the temporary file
        os.unlink(temp_file_path)

        if error:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error extracting data from price list: {error}",
                },
                status=400,
            )

        return JsonResponse({"success": True, "extracted_data": extracted_data})

    except Exception as e:
        logger.exception(f"Error in extract_supplier_price_list_data_view: {e}")
        return JsonResponse(
            {"success": False, "error": f"An unexpected error occurred: {str(e)}"},
            status=500,
        )


# MCP API Endpoints


@service_api_key_required
@require_http_methods(["GET"])
def search_stock_api(request):
    """
    MCP API endpoint for searching internal stock inventory.

    Parameters:
    - description: Material description to search for
    - metal_type: Filter by metal type (optional)
    - alloy: Filter by alloy (optional)
    - min_quantity: Minimum quantity required (optional)
    - limit: Maximum number of results (default 20)
    """
    try:
        # Get query parameters
        description = request.GET.get("description", "")
        metal_type = request.GET.get("metal_type", "")
        alloy = request.GET.get("alloy", "")
        min_quantity = request.GET.get("min_quantity", "")
        limit = int(request.GET.get("limit", 20))

        # Search Stock items
        stock_query = Stock.objects.filter(is_active=True)

        if description:
            stock_query = stock_query.filter(
                Q(description__icontains=description)
                | Q(specifics__icontains=description)
            )

        if metal_type:
            stock_query = stock_query.filter(metal_type__icontains=metal_type)

        if alloy:
            stock_query = stock_query.filter(alloy__icontains=alloy)

        if min_quantity:
            try:
                min_qty = float(min_quantity)
                stock_query = stock_query.filter(quantity__gte=min_qty)
            except ValueError:
                pass

        # Convert stock items to response format
        stock_items = []
        for stock_item in stock_query[:limit]:
            # Calculate retail price using markup
            retail_price = float(stock_item.unit_cost) * (
                1 + float(stock_item.retail_rate)
            )

            stock_items.append(
                {
                    "description": stock_item.description,
                    "quantity": float(stock_item.quantity),
                    "unit_cost": float(stock_item.unit_cost),
                    "retail_price": round(retail_price, 2),
                    "location": stock_item.location or "",
                    "metal_type": stock_item.metal_type or "",
                    "alloy": stock_item.alloy or "",
                }
            )

        return JsonResponse({"stock_items": stock_items})

    except Exception as e:
        logger.exception(f"Error in search_stock_api: {e}")
        return JsonResponse(
            {"error": f"An error occurred: {str(e)}"},
            status=500,
        )


@service_api_key_required
@require_http_methods(["GET"])
def search_supplier_prices_api(request):
    """
    MCP API endpoint for searching supplier pricing.

    Parameters:
    - description: Material description to search for
    - metal_type: Filter by metal type (optional)
    - alloy: Filter by alloy (optional)
    - suppliers: Comma-separated supplier names (optional)
    - include_internal_stock: 'true' to include internal stock as a supplier (optional)
    - limit: Maximum number of results (default 20)
    """
    try:
        # Get query parameters
        description = request.GET.get("description", "")
        metal_type = request.GET.get("metal_type", "")
        alloy = request.GET.get("alloy", "")
        suppliers = request.GET.get("suppliers", "")
        include_internal_stock = (
            request.GET.get("include_internal_stock", "").lower() == "true"
        )
        limit = int(request.GET.get("limit", 20))

        supplier_prices = []

        # Search SupplierProduct items
        supplier_query = SupplierProduct.objects.select_related("supplier")

        if description:
            supplier_query = supplier_query.filter(
                Q(product_name__icontains=description)
                | Q(description__icontains=description)
                | Q(parsed_description__icontains=description)
            )

        if metal_type:
            supplier_query = supplier_query.filter(
                Q(parsed_metal_type__icontains=metal_type)
            )

        if alloy:
            supplier_query = supplier_query.filter(parsed_alloy__icontains=alloy)

        if suppliers:
            supplier_names = [s.strip() for s in suppliers.split(",")]
            supplier_query = supplier_query.filter(supplier__name__in=supplier_names)

        # Convert supplier products to response format
        for product in supplier_query[:limit]:
            supplier_prices.append(
                {
                    "product_name": product.product_name,
                    "supplier_name": product.supplier.name,
                    "price": (
                        float(product.variant_price) if product.variant_price else None
                    ),
                    "available_stock": product.variant_available_stock,
                    "price_unit": product.price_unit or "each",
                    "metal_type": product.parsed_metal_type or "",
                    "alloy": product.parsed_alloy or "",
                    "item_no": product.item_no or "",
                }
            )

        # Optionally include internal stock as "Internal Stock" supplier
        if include_internal_stock:
            stock_query = Stock.objects.filter(is_active=True)

            if description:
                stock_query = stock_query.filter(
                    Q(description__icontains=description)
                    | Q(specifics__icontains=description)
                )

            if metal_type:
                stock_query = stock_query.filter(metal_type__icontains=metal_type)

            if alloy:
                stock_query = stock_query.filter(alloy__icontains=alloy)

            # Add stock items as "Internal Stock" supplier
            for stock_item in stock_query[:limit]:
                retail_price = float(stock_item.unit_cost) * (
                    1 + float(stock_item.retail_rate)
                )

                supplier_prices.append(
                    {
                        "product_name": stock_item.description,
                        "supplier_name": "Internal Stock",
                        "price": round(retail_price, 2),
                        "available_stock": float(stock_item.quantity),
                        "price_unit": "per metre",  # Default assumption
                        "metal_type": stock_item.metal_type or "",
                        "alloy": stock_item.alloy or "",
                        "location": stock_item.location or "",
                    }
                )

        return JsonResponse({"supplier_prices": supplier_prices})

    except Exception as e:
        logger.exception(f"Error in search_supplier_prices_api: {e}")
        return JsonResponse(
            {"error": f"An error occurred: {str(e)}"},
            status=500,
        )


@service_api_key_required
@require_http_methods(["GET"])
def job_context_api(request, job_id):
    """
    MCP API endpoint for fetching job context (for "Interactive Quote" button).

    Returns job details, existing materials, and client history to initialize
    the quoting session with relevant context.
    """
    try:
        # Get the job
        try:
            job = Job.objects.select_related("client", "contact").get(id=job_id)
        except Job.DoesNotExist:
            return JsonResponse(
                {"error": "Job not found"},
                status=404,
            )

        # Build job context
        job_data = {
            "id": str(job.id),
            "name": job.name,
            "client_name": job.client.name if job.client else None,
            "description": job.description or "",
            "status": job.status,
            "job_number": job.job_number,
        }

        # Get existing materials from job pricing (if any)
        existing_materials = []
        if job.latest_quote:
            # Get materials from the latest quote cost set
            for cost_line in job.latest_quote.cost_lines.all():
                existing_materials.append(
                    {
                        "description": cost_line.desc,
                        "quantity": (
                            float(cost_line.quantity) if cost_line.quantity else 0.0
                        ),
                        "unit_cost": (
                            float(cost_line.unit_cost) if cost_line.unit_cost else 0.0
                        ),
                        "notes": (
                            cost_line.meta.get("notes", "") if cost_line.meta else ""
                        ),
                    }
                )

        # Build client history context (recent jobs with same client)
        client_history = []
        if job.client:
            recent_jobs = (
                Job.objects.filter(
                    client=job.client, status__in=["completed", "recently_completed"]
                )
                .exclude(id=job.id)
                .order_by("-created_at")[:3]
            )

            for recent_job in recent_jobs:
                # Get a summary of materials used in previous jobs
                materials_summary = "Previous job materials not available"
                if (
                    recent_job.latest_actual
                    and recent_job.latest_actual.cost_lines.exists()
                ):
                    material_count = recent_job.latest_actual.cost_lines.count()
                    materials_summary = (
                        f"Used {material_count} different materials/services"
                    )

                client_history.append(
                    f"{recent_job.name} ({recent_job.created_at.strftime('%Y-%m-%d')}): {materials_summary}"
                )

        response_data = {
            "job": job_data,
            "existing_materials": existing_materials,
            "client_history": client_history,
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.exception(f"Error in job_context_api: {e}")
        return JsonResponse(
            {"error": f"An error occurred: {str(e)}"},
            status=500,
        )
