import json
import logging
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from workflow.models import Job, Client

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def create_job_form_view(request: HttpRequest) -> HttpResponse:
    """
    Renders the job creation form.
    """
    context = {
        "company_defaults": {
            "wage_rate": 0,  # These will be populated by the edit form
            "charge_out_rate": 0,
        }
    }
    return render(request, "jobs/create_job_form.html", context)


@require_http_methods(["POST"])
def create_job_api(request: HttpRequest) -> JsonResponse:
    """
    Creates a new job from the submitted form data.
    """
    try:
        data = json.loads(request.body)
        
        # Create a new job with the provided data
        job = Job.objects.create(
            name=data.get("name"),
            client_id=data.get("client_id"),  # This will handle the client relationship
            contact_person=data.get("contact_person"),
            contact_phone=data.get("contact_phone"),
            order_number=data.get("order_number"),
            description=data.get("description"),
            material_gauge_quantity=data.get("material_gauge_quantity"),
        )
        
        # Save the job and create an event
        job.save(staff=request.user)
        
        return JsonResponse({
            "success": True,
            "job_id": str(job.id),
            "message": "Job created successfully"
        }, status=201)
        
    except Exception as e:
        logger.exception("Error creating job: %s", str(e))
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500) 