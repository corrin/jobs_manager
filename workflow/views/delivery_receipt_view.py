from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
import logging


from workflow.models import PurchaseOrder, PurchaseOrderLine, Job
from workflow.services.delivery_receipt_service import process_delivery_receipt
from workflow.utils import get_active_jobs

logger = logging.getLogger(__name__)

class DeliveryReceiptListView(LoginRequiredMixin, ListView):
    """View to list all purchase orders that can be received."""
    
    model = PurchaseOrder
    template_name = 'purchases/delivery_receipt_list.html'
    context_object_name = 'purchase_orders'
    
    def get_queryset(self):
        """Return purchase orders that are submitted or partially received."""
        return PurchaseOrder.objects.filter(
            status__in=['submitted', 'partially_received']
        ).order_by('-order_date')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delivery Receipts'
        return context


class DeliveryReceiptCreateView(LoginRequiredMixin, TemplateView):
    """View to create a delivery receipt for a purchase order."""
    
    template_name = 'purchases/delivery_receipt_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase_order = get_object_or_404(PurchaseOrder, pk=kwargs['pk'])
        
        if purchase_order.status not in ['submitted', 'partially_received']:
            raise ValueError("This purchase order cannot be received")
            
        context['purchase_order'] = purchase_order
        context['title'] = f'Delivery Receipt - {purchase_order.po_number}'

        # Find the job designated for holding general stock by its specific name.
        # Assumes 'create_shop_jobs' guarantees this job exists.
        stock_holding_job = Job.objects.get(name="Worker Admin")
        context['stock_holding_job_id'] = str(stock_holding_job.id)
        context['stock_holding_job_name'] = stock_holding_job.name

        allocatable_jobs = get_active_jobs().exclude(id=stock_holding_job.id).order_by('job_number')
        job_list_for_js = [{'id': str(job.id), 'name': str(job)} for job in allocatable_jobs]
        job_list_for_js.insert(0, {'id': context['stock_holding_job_id'], 'name': f"{context['stock_holding_job_name']} (Stock)"})
        context['job_list_json'] = json.dumps(job_list_for_js)

        return context
    
    def post(self, request, *args, **kwargs):
        try:
            received_quantities = json.loads(request.POST.get('received_quantities', '{}'))
            process_delivery_receipt(kwargs['pk'], received_quantities)
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Error processing delivery receipt: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400) 