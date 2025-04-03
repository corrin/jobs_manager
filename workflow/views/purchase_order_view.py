import json
import logging
from datetime import datetime
from django.views.generic import ListView, CreateView, DetailView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory, Form
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError # Import transaction and IntegrityError


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
        purchase_order: PurchaseOrder | None = None
        xero_online_url = None
        xero_id = None
        purchase_order_status = None # Initialize status
        
        if purchase_order_id:
            # Editing an existing purchase order
            purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
            context['title'] = f'Purchase Order {purchase_order.po_number}'
            context['purchase_order_id'] = str(purchase_order.id) # Pass ID to template

            # Fetch Xero details if available
            xero_online_url = purchase_order.online_url
            xero_id = purchase_order.xero_id
            purchase_order_status = purchase_order.status # Fetch the status

            # Add purchase order data
            context['purchase_order_json'] = json.dumps({
                'id': str(purchase_order.id),
                'po_number': purchase_order.po_number,
                'supplier': str(purchase_order.supplier.id),
                'supplier_name': purchase_order.supplier.name,
                'order_date': purchase_order.order_date.isoformat() if purchase_order.order_date else None,
                'expected_delivery': purchase_order.expected_delivery.isoformat() if purchase_order.expected_delivery else None,
                'status': purchase_order_status, # Use the fetched status
                'xero_id': str(xero_id) if xero_id else None, # Include Xero ID if exists
                'xero_online_url': xero_online_url # Include Xero URL if exists
            })

            # Get line items for this purchase order
            assert isinstance(purchase_order, PurchaseOrder) # Ensure type for Pylance
            line_items = purchase_order.po_lines.all() # Use correct related_name 'po_lines'
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
            context['purchase_order_id'] = '' # Ensure it's empty for new POs
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
                'estimated_materials': float(job.latest_estimate_pricing.total_material_cost) if job.latest_estimate_pricing else 0 # Handle None case
            } for job in jobs
        ])
        
        
        # Add Xero details to the main context for template access
        context['xero_purchase_order_url'] = xero_online_url 
        context['xero_id'] = str(xero_id) if xero_id else None
        context['purchase_order_status'] = purchase_order_status
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
@transaction.atomic # Ensure atomicity for PO and lines processing
def autosave_purchase_order_view(request):
    """
    Handles autosave requests for purchase order data. Separates create and update logic.
    """
    request_timestamp = datetime.now().isoformat()
    try:
        data = json.loads(request.body.decode('utf-8', errors='ignore'))
        purchase_order_data = data.get("purchase_order", {})
        line_items = data.get("line_items", [])
        deleted_line_items = data.get("deleted_line_items", [])
        purchase_order_id = purchase_order_data.get("id")

        logger.info(
            f"[{request_timestamp}] autosave_purchase_order_view called. Incoming PO ID: {purchase_order_id}"
        )
        logger.debug("Request data: %s", json.dumps(data, indent=2))
        logger.debug(f"Number of line items: {len(line_items)}")
        logger.debug(f"Number of items to delete: {len(deleted_line_items)}")

        # --- Handle Deletions First ---
        if deleted_line_items:
            try:
                # Ensure deletions only happen if the PO exists (relevant for update path)
                if purchase_order_id:
                    PurchaseOrderLine.objects.filter(id__in=deleted_line_items, purchase_order_id=purchase_order_id).delete()
                    logger.debug(f"Deleted line items with IDs: {deleted_line_items} for PO {purchase_order_id}")
                else:
                    # Should not happen if frontend logic is correct (can't delete lines from non-existent PO)
                     logger.warning(f"Attempted to delete lines {deleted_line_items} for a non-existent PO.")
            except Exception as e:
                 logger.exception(f"Error deleting line items: {deleted_line_items}")
                 messages.error(request, f"Error deleting line items: {e}")
                 return JsonResponse({"error": f"Error deleting line items: {e}", "messages": extract_messages(request)}, status=500)


        purchase_order = None
        created = False

        # --- Determine Create or Update Path ---
        if purchase_order_id:
            # --- UPDATE PATH ---
            logger.debug(f"Attempting to update Purchase Order with ID: {purchase_order_id}")
            try:
                # Lock the row for update
                purchase_order = PurchaseOrder.objects.select_for_update().get(id=purchase_order_id)

                # Update fields from payload
                purchase_order.supplier_id = purchase_order_data.get("client_id", purchase_order.supplier_id)
                purchase_order.status = purchase_order_data.get("status", purchase_order.status)
                purchase_order.order_date = purchase_order_data.get("order_date", purchase_order.order_date)
                # Handle expected_delivery carefully - allow setting to None
                if "expected_delivery" in purchase_order_data:
                     purchase_order.expected_delivery = purchase_order_data.get("expected_delivery") or None
                # Add reference if needed: purchase_order.reference = purchase_order_data.get("reference", purchase_order.reference)

                purchase_order.save()
                logger.debug(f"Updated purchase order {purchase_order.po_number}")
                created = False
            except PurchaseOrder.DoesNotExist:
                logger.error(f"Purchase Order with ID {purchase_order_id} not found for update.")
                messages.error(request, f"Purchase Order with ID {purchase_order_id} not found.")
                return JsonResponse({"error": "Purchase Order not found", "messages": extract_messages(request)}, status=404)
            except Exception as e:
                 logger.exception(f"Error updating PO {purchase_order_id}: {e}")
                 messages.error(request, f"Error updating purchase order: {e}")
                 return JsonResponse({"error": f"Error updating purchase order: {e}", "messages": extract_messages(request)}, status=500)

        else:
            # --- CREATE PATH ---
            logger.debug("Attempting to create a new Purchase Order.")
            supplier_id = purchase_order_data.get("client_id")
            order_date = purchase_order_data.get("order_date")

            if not supplier_id or not order_date:
                 logger.error("Missing supplier_id or order_date for PO creation.")
                 messages.error(request, "Supplier and Order Date are required to create a Purchase Order.")
                 return JsonResponse({"error": "Missing required fields (Supplier, Order Date)", "messages": extract_messages(request)}, status=400)

            try:
                purchase_order = PurchaseOrder(
                    supplier_id=supplier_id,
                    status=purchase_order_data.get("status", 'draft'),
                    order_date=order_date,
                    expected_delivery=purchase_order_data.get("expected_delivery") or None
                    # Add reference if needed: reference=purchase_order_data.get("reference")
                )
                purchase_order.save() # Generates ID and po_number
                logger.debug(f"Created purchase order {purchase_order.po_number} with ID {purchase_order.id}")
                created = True
            except IntegrityError as e:
                 logger.exception(f"Integrity error during PO creation: {e}")
                 messages.error(request, f"Failed to create purchase order due to a conflict: {e}")
                 # Distinguish duplicate PO number error if possible
                 error_msg = f"Database integrity error: {e}"
                 if 'po_number' in str(e):
                     error_msg = "Failed to create purchase order: A purchase order with this number might already exist or there was a generation conflict. Please try again."
                 return JsonResponse({"error": error_msg, "messages": extract_messages(request)}, status=400)
            except Exception as e:
                 logger.exception(f"Unexpected error during PO creation: {e}")
                 messages.error(request, f"Unexpected error creating purchase order: {e}")
                 return JsonResponse({"error": f"Unexpected error creating purchase order: {e}", "messages": extract_messages(request)}, status=500)


        # --- Process Line Items (Common to Create and Update) ---
        if purchase_order: # Ensure PO exists before processing lines
            processed_line_ids = set()
            for item_data in line_items:
                line_id = item_data.get("id")
                try:
                    # Use update_or_create for lines
                    line, line_created = PurchaseOrderLine.objects.update_or_create(
                        id=line_id or None,
                        purchase_order=purchase_order, # Associate with the correct PO
                        defaults={
                            'job_id': item_data.get("job"),
                            'description': item_data.get("description"),
                            'quantity': item_data.get("quantity"),
                            'unit_cost': item_data.get("unit_cost"),
                            'price_tbc': item_data.get("price_tbc", False)
                        }
                    )
                    processed_line_ids.add(str(line.id))
                    # logger.debug(f"{'Created' if line_created else 'Updated'} line item {line.id} for PO {purchase_order.po_number}")
                except Exception as e:
                    logger.exception(f"Error processing line item {item_data}: {e}")
                    messages.error(request, f"Error processing line item: {e}")
                    # Decide if this should be a fatal error for the whole request
                    return JsonResponse({"error": f"Error processing line item: {e}", "messages": extract_messages(request)}, status=500)

            logger.debug("Line items processed successfully")
        else:
             logger.error("Purchase order object is None after create/update logic. Cannot process lines.")
             return JsonResponse({"error": "Internal error: Purchase order not available after processing.", "messages": extract_messages(request)}, status=500)


        # --- Success Response ---
        response_data = {
            "success": True,
            "messages": extract_messages(request),
            "po_number": purchase_order.po_number,
            "id": str(purchase_order.id), # Crucial: Always return the ID
            "action": "created" if created else "updated",
        }
        logger.debug(f"Returning success response: {response_data}")
        return JsonResponse(response_data)

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON in autosave request")
        messages.error(request, "Invalid request format.")
        return JsonResponse(
            {"error": "Invalid JSON", "messages": extract_messages(request)}, status=400
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        logger.exception("Unexpected error during purchase order autosave")
        return JsonResponse(
            {"error": f"Unexpected server error: {str(e)}", "messages": extract_messages(request)}, status=500
        )