import json
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from workflow.models import Stock, CompanyDefaults
from job.models import Job, JobPricing, MaterialEntry
from workflow.enums import JobPricingType

logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
@transaction.atomic # Ensure database operations are atomic
def consume_stock_api_view(request):
    """
    API endpoint to record stock consumption for a job and create a MaterialEntry.
    """
    try:
        data = json.loads(request.body)
        job_id = data.get('job_id')
        stock_item_id = data.get('stock_item_id')
        quantity_used_str = data.get('quantity_used')

        # --- Validation ---
        if not all([job_id, stock_item_id, quantity_used_str]):
            logger.warning("Consume stock request missing required data.")
            return JsonResponse({'error': "Missing required data."}, status=400)

        try:
            quantity_used = Decimal(str(quantity_used_str))
            if quantity_used <= 0:
                 logger.warning(f"Invalid quantity used ({quantity_used}) for stock {stock_item_id}.")
                 return JsonResponse({'error': "Quantity used must be positive."}, status=400)
        except (InvalidOperation, TypeError):
            logger.warning(f"Invalid quantity format received: {quantity_used_str}")
            return JsonResponse({'error': "Invalid quantity format."}, status=400)

        job = get_object_or_404(Job, id=job_id) # Raises 404 if not found
        stock_item = get_object_or_404(Stock, id=stock_item_id) # Raises 404 if not found

        if quantity_used > stock_item.quantity:
            logger.warning(f"Attempted to consume {quantity_used} from stock {stock_item_id} with only {stock_item.quantity} available.")
            return JsonResponse({'error': f"Quantity used exceeds available stock ({stock_item.quantity})."}, status=400)

        reality_pricing = JobPricing.objects.filter(job=job, pricing_type=JobPricingType.REALITY).first()
        if not reality_pricing:
             logger.error(f"CRITICAL: 'Reality' JobPricing not found for job {job.id} during stock consumption.")
             # Return 500 as this is a system setup issue
             return JsonResponse({'error': f"Cannot record material cost: Reality pricing missing for job {job.id}"}, status=500)

        # --- Apply Business Logic / Pricing Rules ---
        # TODO: Implement specific pricing rules (e.g., half-sheet rule) here
        unit_cost = stock_item.unit_cost
        unit_revenue = unit_cost * (1 + stock_item.retail_rate)

        # --- Perform Database Operations ---
        material_entry = MaterialEntry.objects.create(
            part=reality_pricing.get_default_part(),
            source_stock=stock_item,
            description=f"Consumed: {stock_item.description}",
            quantity=quantity_used,
            unit_cost=unit_cost,
            unit_revenue=unit_revenue,
            purchase_order_line=stock_item.source_purchase_order_line,
        )
        logger.info(f"Created MaterialEntry {material_entry.id} for Job {job_id} from Stock {stock_item_id}")

        stock_item.quantity -= quantity_used
        
        # If quantity is now zero, set is_active to False
        if stock_item.quantity <= 0:
            stock_item.is_active = False
            stock_item.save(update_fields=['quantity', 'is_active'])
            logger.info(f"Updated Stock {stock_item_id} quantity to {stock_item.quantity} and deactivated it")
        else:
            stock_item.save(update_fields=['quantity'])
            logger.info(f"Updated Stock {stock_item_id} quantity to {stock_item.quantity}")

        # --- Prepare Success Response ---
        response_data = {
            'success': True,
            'message': 'Stock consumed successfully.',
            # Include data needed to refresh the AG Grid on the frontend
            'new_material_entry': {
                'id': str(material_entry.id),
                'description': material_entry.description,
                'quantity': float(material_entry.quantity),
                'unit_cost': float(material_entry.unit_cost),
                'unit_revenue': float(material_entry.unit_revenue),
                'cost': float(material_entry.cost),
                'revenue': float(material_entry.revenue),
                'po_url': None # TODO: Generate PO URL if needed
            }
        }
        return JsonResponse(response_data, status=200) # Use 200 for successful update/action

    except json.JSONDecodeError:
        logger.warning("Invalid JSON received for stock consumption.")
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    except Http404 as e: # Catch 404 from get_object_or_404
         logger.warning(f"Not Found error during stock consumption: {e}")
         return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        logger.exception(f"Unexpected error consuming stock: {e}")
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)

@require_http_methods(["POST"])
@transaction.atomic
def create_stock_api_view(request):
    """
    API endpoint to create a new stock item.
    """
    try:
        data = json.loads(request.body)
        description = data.get('description')
        quantity_str = data.get('quantity')
        unit_cost_str = data.get('unit_cost')
        source = data.get('source')
        notes = data.get('notes', '')
        metal_type = data.get('metal_type', '')
        alloy = data.get('alloy', '')
        specifics = data.get('specifics', '')
        location = data.get('location', '')

        # --- Validation ---
        if not all([description, quantity_str, unit_cost_str, source]):
            logger.warning("Create stock request missing required data.")
            return JsonResponse({'error': "Missing required data."}, status=400)

        try:
            quantity = Decimal(str(quantity_str))
            if quantity <= 0:
                logger.warning(f"Invalid quantity ({quantity}) for new stock.")
                return JsonResponse({'error': "Quantity must be positive."}, status=400)
        except (InvalidOperation, TypeError):
            logger.warning(f"Invalid quantity format received: {quantity_str}")
            return JsonResponse({'error': "Invalid quantity format."}, status=400)

        try:
            unit_cost = Decimal(str(unit_cost_str))
            if unit_cost <= 0:
                logger.warning(f"Invalid unit cost ({unit_cost}) for new stock.")
                return JsonResponse({'error': "Unit cost must be positive."}, status=400)
        except (InvalidOperation, TypeError):
            logger.warning(f"Invalid unit cost format received: {unit_cost_str}")
            return JsonResponse({'error': "Invalid unit cost format."}, status=400)

        # Get the stock holding job
        stock_holding_job = Stock.get_stock_holding_job()

        # Get company defaults for markup calculation
        company_defaults = CompanyDefaults.get_instance()
        materials_markup = company_defaults.materials_markup

        # Create the stock item
        stock_item = Stock.objects.create(
            job=stock_holding_job,
            description=description,
            quantity=quantity,
            unit_cost=unit_cost,
            source=source,
            notes=notes,
            metal_type=metal_type,
            alloy=alloy,
            specifics=specifics,
            location=location,
            is_active=True
        )
        logger.info(f"Created new Stock item {stock_item.id}: {description}")

        # Calculate unit revenue using the materials markup
        unit_revenue = unit_cost * (1 + materials_markup)
        total_value = quantity * unit_cost

        # Prepare response data
        response_data = {
            'success': True,
            'message': 'Stock item created successfully.',
            'stock_item': {
                'id': str(stock_item.id),
                'description': stock_item.description,
                'quantity': float(stock_item.quantity),
                'unit_cost': float(stock_item.unit_cost),
                'unit_revenue': float(unit_revenue),
                'total_value': float(total_value),
                'metal_type': stock_item.metal_type,
                'alloy': stock_item.alloy,
                'specifics': stock_item.specifics,
                'location': stock_item.location
            }
        }
        return JsonResponse(response_data, status=201)  # Use 201 for resource creation

    except json.JSONDecodeError:
        logger.warning("Invalid JSON received for stock creation.")
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error creating stock: {e}")
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)

def search_available_stock_api(request):
    """
    API endpoint to search available stock items for autocomplete.
    Searches active stock items matching the search term.
    Relies on is_active=True implicitly meaning quantity > 0 and
    item is available for consumption (likely linked to Worker Admin job).
    """
    search_term = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 25)) # Limit results

    results = [] # Default to empty list

    if search_term:
        # Filter only by active status and description
        # Assumes is_active=True implies quantity > 0 and correct job allocation
        matching_stock = Stock.objects.filter(
            is_active=True,
            description__icontains=search_term
        ).select_related('job').order_by('description')[:limit] # Keep select_related for job name display

        # Serialize the data for autocomplete
        results = [
            {
                'id': str(item.id),
                # Display job name in text for clarity if needed, assuming active stock is under Worker Admin
                'text': f"{item.description} (Avail: {item.quantity}, Loc: {item.job.name if item.job else 'N/A'})",
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_cost': float(item.unit_cost),
            }
            for item in matching_stock
        ]

    # Return results directly, matching ClientSearch response structure
    return JsonResponse({'results': results})

# Note: Broad exception handling removed to strictly match ClientSearch style.
# Consider adding it back if more robustness is needed.

@require_http_methods(["POST"])
@transaction.atomic
def deactivate_stock_api_view(request, stock_id):
    """
    API endpoint to deactivate a stock item (soft delete).
    Sets is_active=False to hide it from the UI.
    """
    try:
        # Get the stock item
        stock_item = get_object_or_404(Stock, id=stock_id)
        
        # Set is_active to False (soft delete)
        stock_item.is_active = False
        stock_item.save(update_fields=['is_active'])
        
        logger.info(f"Deactivated Stock item {stock_id}: {stock_item.description}")
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Stock item deleted successfully.'
        })
    except Http404 as e:
        logger.warning(f"Stock item not found for deactivation: {stock_id}")
        return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        logger.exception(f"Unexpected error deactivating stock: {e}")
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)