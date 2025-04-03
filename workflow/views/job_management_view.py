import logging
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from workflow.models import Job, JobPricing
from workflow.services.job_service import archive_and_reset_job_pricing

logger = logging.getLogger(__name__)


def is_staff(user):
    return user.is_staff


@user_passes_test(is_staff)
def month_end_view(request: HttpRequest) -> HttpResponse:
    """
    View for month-end processing of special jobs.
    GET: Display a list of special jobs for selection
    POST: Process the selected jobs
    """
    # Get all special jobs
    special_jobs = Job.objects.filter(status="special")
    
    # Gather additional data for each job
    job_data = []
    for job in special_jobs:
        # Find last time month-end was run (find most recent historical pricing)
        last_month_end = (
            JobPricing.objects.filter(job=job, is_historical=True)
            .order_by('-created_at')
            .first()
        )
        last_month_end_date = last_month_end.created_at if last_month_end else None
        
        # Get current reality pricing for calculations
        reality_pricing = job.latest_reality_pricing
        
        # Calculate total hours
        total_hours = Decimal('0.00')
        if reality_pricing:
            time_entries_sum = (
                reality_pricing.time_entries.aggregate(
                    Sum('hours')
                )['hours__sum'] or Decimal('0.00')
            )
            total_hours = time_entries_sum
        
        # Calculate total dollars using the total_revenue property directly
        total_dollars = Decimal('0.00')
        if reality_pricing:
            total_dollars = reality_pricing.total_revenue
        
        job_data.append({
            'job': job,
            'last_month_end_date': last_month_end_date,
            'total_hours': total_hours,
            'total_dollars': total_dollars,
        })
    
    if request.method == "POST":
        # Process selected jobs
        selected_job_ids = request.POST.getlist("job_ids")
        processed_jobs = []
        error_jobs = []
        
        for job_id in selected_job_ids:
            try:
                job = Job.objects.get(id=job_id)
                archive_and_reset_job_pricing(job_id)
                processed_jobs.append(job)
            except Job.DoesNotExist:
                logger.error(f"Job with ID {job_id} not found")
            except Exception as e:
                error_jobs.append((job_id, str(e)))
                logger.exception(f"Error processing job {job_id}: {str(e)}")
                messages.error(request, f"Error processing job {job_id}: {str(e)}")
        
        # Add success messages
        if processed_jobs:
            job_names = ", ".join([job.name for job in processed_jobs])
            messages.success(
                request, 
                f"Successfully processed {len(processed_jobs)} jobs: {job_names}"
            )
        
        if error_jobs:
            error_msg = ", ".join([f"Job {job_id}" for job_id, _ in error_jobs])
            messages.warning(
                request, 
                f"Errors occurred with {len(error_jobs)} jobs: {error_msg}"
            )
            
        # Redirect to same page to avoid form resubmission
        return redirect("month_end")
        
    # For GET requests, render the selection form
    context = {
        "job_data": job_data,
        "page_title": "Month-End Processing",
    }
    return render(request, "jobs/month_end.html", context) 