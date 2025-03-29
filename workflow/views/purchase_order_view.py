from datetime import datetime
from django.views.generic import ListView, CreateView, DetailView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory, Form
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
import json
import logging

from workflow.models import PurchaseOrder, PurchaseOrderLine, Client, Job
from workflow.forms import PurchaseOrderForm, PurchaseOrderLineForm
from workflow.utils import extract_messages

logger = logging.getLogger(__name__)


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    """View to list all purchase orders."""
    
    model = PurchaseOrder
    template_name = 'purchases/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    
    def get_queryset(self):
        """Return purchase orders ordered by date."""
        return PurchaseOrder.objects.all().order_by('-order_date')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Purchase Orders'
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, TemplateView):
    """View to create or edit a purchase order, following the timesheet pattern."""
    
    template_name = 'purchases/purchase_order_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if we're editing an existing purchase order
        purchase_order_id = self.kwargs.get('pk')
        purchase_order = None
        
        if purchase_order_id:
            # Editing an existing purchase order
            purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
            context['title'] = f'Purchase Order {purchase_order.po_number}'
            context['purchase_order_id'] = str(purchase_order.id)
            
            # Add purchase order data
            context['purchase_order_json'] = json.dumps({
                'id': str(purchase_order.id),
                'po_number': purchase_order.po_number,
                'supplier': str(purchase_order.supplier.id),
                'supplier_name': purchase_order.supplier.name,
                'order_date': purchase_order.order_date.isoformat() if purchase_order.order_date else None,
                'expected_delivery': purchase_order.expected_delivery.isoformat() if purchase_order.expected_delivery else None,
                'status': purchase_order.status
            })
            
            # Get line items for this purchase order
            line_items = purchase_order.lines.all()
            context['line_items_json'] = json.dumps([
                {
                    'id': str(line.id),
                    'job': str(line.job.id) if line.job else None,
                    'job_display_name': f"{line.job.job_number} - {line.job.name}" if line.job else None,
                    'description': line.description,
                    'quantity': float(line.quantity),
                    'unit_cost': float(line.unit_cost) if line.unit_cost is not None else None,
                    'price_tbc': line.price_tbc,
                    'total': float(line.quantity * (line.unit_cost or 0))
                } for line in line_items
            ])
        else:
            # Creating a new purchase order
            context['title'] = 'New Purchase Order'
            context['purchase_order_json'] = json.dumps({})
            context['line_items_json'] = json.dumps([])
        
        # Get active jobs for the line items - match exactly what timesheet view does
        jobs = Job.objects.filter(
            status__in=['quoting', 'approved', 'in_progress', 'special']
        ).select_related('client', 'latest_estimate_pricing')
        
        context['jobs_json'] = json.dumps([
            {
                'id': str(job.id),
                'job_number': job.job_number,
                'name': job.name,
                'client_name': job.client.name if job.client else 'No Client',
                'client_id': str(job.client.id) if job.client else None,
                'job_display_name': f"{job.job_number} - {job.name}",
                'estimated_materials': float(job.latest_estimate_pricing.total_material_cost)
            } for job in jobs
        ])
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle form submission via AJAX."""
        try:
            purchase_order_data = json.loads(request.POST.get('purchase_order_data', '{}'))
            line_items_data = json.loads(request.POST.get('line_items_data', '[]'))
            
            # Get the client (supplier)
            client_id = purchase_order_data.get('supplier')
            
            # Create purchase order
            purchase_order = PurchaseOrder(
                supplier_id=client_id,
                order_date=purchase_order_data.get('order_date'),
                expected_delivery=purchase_order_data.get('expected_delivery'),
                status='draft'
            )
            purchase_order.save()
            
            # Create line items
            for item in line_items_data:
                PurchaseOrderLine.objects.create(
                    purchase_order=purchase_order,
                    job_id=item.get('job'),
                    description=item.get('description'),
                    quantity=item.get('quantity'),
                    unit_cost=item.get('unit_cost')
                )
            
            messages.success(request, f"Purchase order {purchase_order.po_number} created successfully.")
            return JsonResponse({
                'success': True, 
                'redirect_url': reverse_lazy('purchase_orders')
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


# Kept for reference but not used directly anymore
PurchaseOrderLineFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderLine,
    form=PurchaseOrderLineForm,
    extra=1,
    can_delete=True
)


@require_http_methods(["POST"])
def autosave_purchase_order_view(request):
    """
    Handles autosave requests for purchase order data.
    
    Purpose:
    - Automates the saving of purchase order changes, including updates, creations, and deletions.
    - Ensures data consistency and prevents duplication during processing.
    - Follows the same pattern as timesheet autosave for consistency.
    
    Workflow:
    1. Parsing and Validation:
    - Parses the incoming request body as JSON.
    - Extracts purchase order data and line items.
    
    2. Processing:
    - Creates or updates the purchase order.
    - Creates or updates line items.
    - Handles deletions of line items.
    
    3. Response:
    - Returns success responses with feedback messages.
    - Sends error responses for invalid data or unexpected issues.
    
    Parameters:
    - `request` (HttpRequest): The HTTP POST request containing purchase order data in JSON format.
    
    Returns:
    - JsonResponse: Contains success status, messages, and updated data.
    """
    try:
        logger.debug("Purchase order autosave request received")
        data = json.loads(request.body)
        logger.debug("Request data: %s", json.dumps(data, indent=2))
        
        purchase_order_data = data.get("purchase_order", {})
        line_items = data.get("line_items", [])
        deleted_line_items = data.get("deleted_line_items", [])
        
        # Log detailed information about the purchase order data
        logger.debug("Purchase order data: %s", json.dumps(purchase_order_data, indent=2))
        
        logger.debug(f"Number of line items: {len(line_items)}")
        logger.debug(f"Number of items to delete: {len(deleted_line_items)}")
        
        # Handle deletions first - return error immediately if any line not found
        for line_id in deleted_line_items:
            logger.debug(f"Deleting line item with ID: {line_id}")
            
            try:
                line = PurchaseOrderLine.objects.get(id=line_id)
                line.delete()
                logger.debug(f"Line item with ID {line_id} deleted successfully")
            except PurchaseOrderLine.DoesNotExist:
                # Return error immediately if line not found
                logger.error(f"Line item with ID {line_id} not found for deletion")
                messages.error(request, f"Line item with ID {line_id} not found for deletion")
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Line item with ID {line_id} not found for deletion",
                        "messages": extract_messages(request),
                    },
                    status=404,
                )
        
        # True upsert pattern
        purchase_order, created = PurchaseOrder.objects.update_or_create(
            id=purchase_order_data.get("id") or None,
            defaults={
                'supplier_id': purchase_order_data.get("client_id"),
                'status': purchase_order_data.get("status"),
                'order_date': purchase_order_data.get("order_date"),
                'expected_delivery': purchase_order_data.get("expected_delivery") or None
            }
        )
        if created:
            logger.debug(f"Created purchase order {purchase_order.po_number}")
        else:
            logger.debug(f"Updated purchase order {purchase_order.po_number}")
                
        # Process line items - true upsert pattern
        for item_data in line_items:
            # Use update_or_create for true upsert
            PurchaseOrderLine.objects.update_or_create(
                id=item_data.get("id") or None,
                defaults={
                    'purchase_order': purchase_order,
                    'job_id': item_data.get("job"),
                    'description': item_data.get("description"),
                    'quantity': item_data.get("quantity"),
                    'unit_cost': item_data.get("unit_cost"),
                    'price_tbc': item_data.get("price_tbc")
                }
            )
            
        logger.debug("Line items created successfully")
        
        return JsonResponse(
            {
                "success": True,
                "messages": extract_messages(request),
                "po_number": purchase_order.po_number,
                "id": str(purchase_order.id),
                "action": "save",
            }
        )
        
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        messages.error(request, "Failed to parse JSON")
        return JsonResponse(
            {"error": "Invalid JSON", "messages": extract_messages(request)}, status=400
        )
    
    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error during purchase order autosave")
        
        # Log more detailed information about the error
        if hasattr(e, 'message_dict'):
            # This is a ValidationError with field information
            logger.error("Validation error details: %s", json.dumps(e.message_dict, indent=2))
        
        return JsonResponse(
            {"error": str(e), "messages": extract_messages(request)}, status=500
        )