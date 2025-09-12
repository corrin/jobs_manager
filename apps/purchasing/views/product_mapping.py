import logging
from decimal import Decimal

from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.quoting.models import ProductParsingMapping, SupplierProduct

logger = logging.getLogger(__name__)


def product_mapping_validation(request):
    """
    Modern interface for validating product parsing mappings.
    """
    # Get all mappings, prioritizing unvalidated ones first
    all_mappings = list(
        ProductParsingMapping.objects.filter(is_validated=False).order_by("-created_at")
    )  # Unvalidated first

    # Add validated mappings for context
    validated_mappings = list(
        ProductParsingMapping.objects.filter(is_validated=True).order_by(
            "-validated_at"
        )
    )

    # Combine all mappings
    all_mappings.extend(validated_mappings)

    # Update Xero status for all mappings
    for mapping in all_mappings:
        mapping.update_xero_status()

    # Get some stats
    total_mappings = ProductParsingMapping.objects.count()
    validated_count = ProductParsingMapping.objects.filter(is_validated=True).count()
    unvalidated_count = total_mappings - validated_count

    context = {
        "title": "Product Mapping Validation",
        "all_mappings": all_mappings,
        "stats": {
            "total_mappings": total_mappings,
            "validated_count": validated_count,
            "unvalidated_count": unvalidated_count,
            "validation_percentage": round(
                (validated_count / total_mappings * 100) if total_mappings > 0 else 0, 1
            ),
        },
    }

    return render(request, "purchasing/product_mapping_validation.html", context)


@require_http_methods(["POST"])
def validate_mapping(request, mapping_id):
    """
    Validate a product parsing mapping.
    """
    try:
        mapping = ProductParsingMapping.objects.get(id=mapping_id)

        # Update validation status
        mapping.is_validated = True
        mapping.validated_by = request.user
        mapping.validated_at = timezone.now()
        mapping.validation_notes = request.POST.get("validation_notes", "")

        # Update any modified mapping fields from the form
        mapping.mapped_item_code = request.POST.get(
            "mapped_item_code", mapping.mapped_item_code
        )
        mapping.mapped_description = request.POST.get(
            "mapped_description", mapping.mapped_description
        )
        mapping.mapped_metal_type = request.POST.get(
            "mapped_metal_type", mapping.mapped_metal_type
        )
        mapping.mapped_alloy = request.POST.get("mapped_alloy", mapping.mapped_alloy)
        mapping.mapped_specifics = request.POST.get(
            "mapped_specifics", mapping.mapped_specifics
        )
        mapping.mapped_dimensions = request.POST.get(
            "mapped_dimensions", mapping.mapped_dimensions
        )

        unit_cost = request.POST.get("mapped_unit_cost")
        if unit_cost:
            try:
                mapping.mapped_unit_cost = Decimal(unit_cost)
            except (ValueError, TypeError) as e:
                return HttpResponseBadRequest(
                    f"Invalid unit cost format: {unit_cost}. Error: {str(e)}"
                )

        mapping.mapped_price_unit = request.POST.get(
            "mapped_price_unit", mapping.mapped_price_unit
        )

        # Update Xero status based on the new item code
        mapping.update_xero_status()

        mapping.save()

        # Backflow: Update all SupplierProducts that use this mapping
        supplier_products = SupplierProduct.objects.filter(
            mapping_hash=mapping.input_hash
        )
        update_count = supplier_products.update(
            parsed_item_code=mapping.mapped_item_code,
            parsed_description=mapping.mapped_description,
            parsed_metal_type=mapping.mapped_metal_type,
            parsed_alloy=mapping.mapped_alloy,
            parsed_specifics=mapping.mapped_specifics,
            parsed_dimensions=mapping.mapped_dimensions,
            parsed_unit_cost=mapping.mapped_unit_cost,
            parsed_price_unit=mapping.mapped_price_unit,
        )

        logger.info(
            f"Updated {update_count} SupplierProducts with validated mapping {mapping_id}"
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"Mapping validated successfully. Updated {update_count} related products.",
            }
        )

    except ProductParsingMapping.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Mapping not found"}, status=404
        )
    except Exception as e:
        logger.exception(f"Error validating mapping {mapping_id}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
