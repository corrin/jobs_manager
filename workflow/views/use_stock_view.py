import json
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from workflow.models import Stock, CompanyDefaults
from workflow.utils import get_active_jobs
from workflow.enums import MetalType

logger = logging.getLogger(__name__)
def use_stock_view(request, job_id=None):
    """
    View for the Use Stock page.
    Displays a list of available stock items and allows searching and consuming stock.
    
    Args:
        request: The HTTP request
        job_id: Optional job ID to pre-select in the dropdown (can be provided in URL path or query string)
    """
    # Check if job_id is provided in query string
    if not job_id and request.GET.get('job_id'):
        job_id = request.GET.get('job_id')
    # Get all active stock items
    stock_items = Stock.objects.filter(is_active=True).order_by('description')
    
    # Get the stock holding job and active jobs
    stock_holding_job = Stock.get_stock_holding_job()
    active_jobs = get_active_jobs().exclude(id=stock_holding_job.id).order_by('job_number')
    
    # Get company defaults for markup calculation
    company_defaults = CompanyDefaults.get_instance()
    materials_markup = company_defaults.materials_markup
    
    # Prepare stock data for AG Grid
    stock_data = []
    for item in stock_items:
        # Calculate unit revenue using the materials markup
        unit_revenue = item.unit_cost * (1 + materials_markup)
        total_value = item.quantity * item.unit_cost
        
        stock_data.append({
            'id': str(item.id),  # Convert UUID to string
            'description': item.description,
            'quantity': float(item.quantity),
            'unit_cost': float(item.unit_cost),
            'unit_revenue': float(unit_revenue),
            'total_value': float(total_value),
            'metal_type': item.metal_type,
            'alloy': item.alloy or '',
            'specifics': item.specifics or '',
            'location': item.location or ''
        })
    
    # If job_id is provided, get the job object to pass to the template
    default_job = None
    if job_id:
        try:
            default_job = next((job for job in active_jobs if str(job.id) == str(job_id)), None)
        except Exception as e:
            logger.error(f"Error finding job with ID {job_id}: {e}")
            # redirect to the error page here

    context = {
        'title': 'Use Stock',
        'stock_items': stock_items,
        'stock_data_json': json.dumps(stock_data),
        'active_jobs': active_jobs,
        'stock_holding_job': stock_holding_job,
        'metal_types': MetalType.choices,
        'default_job_id': str(job_id) if job_id else None,
    }
    
    return render(request, 'purchases/use_stock.html', context)