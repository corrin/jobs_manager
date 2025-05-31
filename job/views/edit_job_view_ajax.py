import json
import logging

from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from job.enums import JobPricingMethodology, JobPricingType
from job.helpers import DecimalEncoder, get_company_defaults
from workflow.models import Quote, Invoice
from job.serializers import JobPricingSerializer, JobSerializer

from job.models import Job, JobEvent

from job.services.file_service import sync_job_folder
from job.services.job_service import (
    get_historical_job_pricings,
    get_job_with_pricings,
    get_latest_job_pricings,
    archive_and_reset_job_pricing,
)
from workflow.services.google_sheets_service import create_quote_from_template

logger = logging.getLogger(__name__)
DEBUG_JSON = False  # Toggle for JSON debugging


def get_company_defaults_api(request):
    """
    API endpoint to fetch company default settings.
    Uses the get_company_defaults() helper function to ensure
    a single instance is retrieved or created if it doesn't exist.
    """
    defaults = get_company_defaults()
    return JsonResponse(
        {
            "materials_markup": float(defaults.materials_markup),
            "time_markup": float(defaults.time_markup),
            "charge_out_rate": float(defaults.charge_out_rate),
            "wage_rate": float(defaults.wage_rate),
        }
    )


def create_job_view(request):
    return render(request, "jobs/create_job_and_redirect.html")


def api_fetch_status_values(request):
    status_values = dict(Job.JOB_STATUS_CHOICES)
    return JsonResponse(status_values)


@require_http_methods(["POST"])
def create_job_api(request):
    try:
        # Create the job with default values using the service function
        new_job = Job()
        new_job.save(staff=request.user)

        # Log that the job and pricings have been created successfully
        logger.debug(f"New job created with ID: {new_job.id}")

        # Return the job_id as a JSON response
        return JsonResponse({"job_id": str(new_job.id)}, status=201)

    except Exception as e:
        # Catch all exceptions to ensure API always returns JSON response
        logger.exception("Error creating job")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def fetch_job_pricing_api(request):
    job_id = request.GET.get("job_id")
    pricing_type = request.GET.get("pricing_type")

    if not job_id or not pricing_type:
        return JsonResponse({"error": "Missing job_id or pricing_type"}, status=400)

    try:
        # Retrieve the job with related pricings using the service function
        job = get_job_with_pricings(job_id)

        # Retrieve the pricing data by filtering the job pricings based on pricing_type
        pricing_data = job.pricings.filter(pricing_type=pricing_type).values()

        if not pricing_data.exists():
            return JsonResponse(
                {"error": "No data found for the provided job_id and pricing_type"},
                status=404,
            )

        # Convert to a list since JsonResponse cannot serialize QuerySets
        return JsonResponse(list(pricing_data), safe=False)

    except Job.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    except Exception as e:
        # Log the unexpected error and return an error response
        logger.exception("Unexpected error during fetch_job_pricing_api")
        return JsonResponse({"error": str(e)}, status=500)


def form_to_dict(form):
    if form.is_valid():
        return form.cleaned_data
    else:
        return form.initial


@require_http_methods(["GET", "POST"])
def edit_job_view_ajax(request, job_id=None):
    if job_id:
        # Fetch the existing Job along with pricings
        job = get_job_with_pricings(job_id)
        logger.debug(f"Editing existing job with ID: {job.id}")
    else:
        raise ValueError("Job ID is required to edit a job")

    # Fetch related Quote and Invoice if they exist
    related_quote = Quote.objects.filter(job=job).first()
    related_invoice = Invoice.objects.filter(job=job).first()
    job_quoted = related_quote is not None
    job_invoiced = related_invoice is not None
    quote_online_url = related_quote.online_url if related_quote else None
    invoice_online_url = related_invoice.online_url if related_invoice else None

    # Fetch All Job Pricing Revisions for Each Pricing Stage
    historical_job_pricings = get_historical_job_pricings(job)

    # Expand the serialization to include all necessary data for historical view
    historical_job_pricings_serialized = []
    for pricing in historical_job_pricings:
        # Create the base structure with FLAT prefixed fields
        pricing_data = {
            'id': str(pricing.id),
            'created_at': pricing.created_at.isoformat(),
        }
        
        # Determine which pricing section this historical record belongs to
        section_prefix = pricing.pricing_type
        
        # Process time entries
        time_entries = []
        time_cost_total = 0
        time_revenue_total = 0
        
        for entry in pricing.time_entries.all():
            # Calculate cost and revenue
            cost = entry.wage_rate * entry.hours if hasattr(entry, 'wage_rate') and hasattr(entry, 'hours') else 0
            revenue = entry.charge_out_rate * entry.hours if hasattr(entry, 'charge_out_rate') and hasattr(entry, 'hours') else 0
            
            # Add to totals
            time_cost_total += cost
            time_revenue_total += revenue
            
            # Create entry object
            time_entries.append({
                'id': str(entry.id),
                'description': entry.description if hasattr(entry, 'description') else '',
                'hours': entry.hours if hasattr(entry, 'hours') else 0,
                'cost': cost,
                'revenue': revenue,
            })
        
        # Assign with prefixed keys - THIS IS THE KEY CHANGE
        pricing_data[f'{section_prefix}_time_entries'] = time_entries
        pricing_data[f'{section_prefix}_time_cost'] = time_cost_total
        pricing_data[f'{section_prefix}_time_revenue'] = time_revenue_total
        
        # Process material entries
        material_entries = []
        material_cost_total = 0
        material_revenue_total = 0
        
        for entry in pricing.material_entries.all():
            # Calculate cost and revenue
            quantity = entry.quantity if hasattr(entry, 'quantity') else 0
            unit_cost = entry.unit_cost if hasattr(entry, 'unit_cost') else 0
            unit_revenue = entry.unit_revenue if hasattr(entry, 'unit_revenue') else 0
            
            cost = quantity * unit_cost
            revenue = quantity * unit_revenue
            
            # Add to totals
            material_cost_total += cost
            material_revenue_total += revenue

            # Generate PO URL if applicable
            po_url = None
            if entry.purchase_order_line and entry.purchase_order_line.purchase_order:
                try:
                    po_url = reverse('edit_purchase_order', kwargs={'pk': entry.purchase_order_line.purchase_order.id})
                except Exception as e:
                    logger.error(f"Error generating PO URL for material entry {entry.id}: {e}")
            
            # Create entry object
            material_entries.append({
                'id': str(entry.id),
                'description': entry.description if hasattr(entry, 'description') else '',
                'quantity': quantity,
                'cost': cost,
                'revenue': revenue,
                'unit_cost': unit_cost,
                'unit_revenue': unit_revenue,
                'po_url': po_url,  # <-- Add the PO URL here
            })
        
        # Assign with prefixed keys
        pricing_data[f'{section_prefix}_material_entries'] = material_entries
        pricing_data[f'{section_prefix}_material_cost'] = material_cost_total
        pricing_data[f'{section_prefix}_material_revenue'] = material_revenue_total
        
        # Process adjustment entries
        adjustment_entries = []
        adjustment_cost_total = 0
        adjustment_revenue_total = 0
        
        for entry in pricing.adjustment_entries.all():
            # Get cost and revenue adjustments
            cost_adjustment = entry.cost_adjustment if hasattr(entry, 'cost_adjustment') else 0
            price_adjustment = entry.price_adjustment if hasattr(entry, 'price_adjustment') else 0
            
            # Add to totals
            adjustment_cost_total += cost_adjustment
            adjustment_revenue_total += price_adjustment
            
            # Create entry object
            adjustment_entries.append({
                'id': str(entry.id),
                'description': entry.description if hasattr(entry, 'description') else '',
                'cost': cost_adjustment,
                'revenue': price_adjustment,
            })
        
        # Assign with prefixed keys
        pricing_data[f'{section_prefix}_adjustment_entries'] = adjustment_entries
        pricing_data[f'{section_prefix}_adjustment_cost'] = adjustment_cost_total
        pricing_data[f'{section_prefix}_adjustment_revenue'] = adjustment_revenue_total
        
        # Calculate and assign total cost and revenue with prefixed keys
        pricing_data[f'{section_prefix}_total_cost'] = time_cost_total + material_cost_total + adjustment_cost_total
        pricing_data[f'{section_prefix}_total_revenue'] = time_revenue_total + material_revenue_total + adjustment_revenue_total
        
        # Add this fully structured historical pricing record to the array
        historical_job_pricings_serialized.append(pricing_data)
    
    # Fetch the Latest Revision for Each Pricing Stage
    latest_job_pricings = get_latest_job_pricings(job)

    sync_job_folder(job)
    job_files = job.files.all()
    
    # Verify if there's only JobSummary.pdf
    has_only_summary = False
    if job_files.count() == 0:
        has_only_summary = True
    elif job_files.count() == 1 and job_files.first().filename == "JobSummary.pdf":
        has_only_summary = True

    # Serialize the job files data to JSO
    # Include the Latest Revision Data
    latest_job_pricings_serialized = {
        section_name: JobPricingSerializer(latest_pricing).data
        for section_name, latest_pricing in latest_job_pricings.items()
    }

    # Serialize the job pricings data to JSON
    historical_job_pricings_json = json.dumps(
        historical_job_pricings_serialized, cls=DecimalEncoder
    )
    latest_job_pricings_json = json.dumps(
        latest_job_pricings_serialized, cls=DecimalEncoder
    )

    # Get company defaults for any shared settings or values
    company_defaults = get_company_defaults()

    # Get job events related to this job
    events = JobEvent.objects.filter(job=job).order_by("-timestamp")

    # Prepare the context to pass to the template
    context = {
        "job": job,
        "job_id": job.id,
        # Ensure job.contact_person and job.contact_email are available for initial hidden field values
        # These are already available via the 'job' object itself
        "events": events,
        "quoted": job_quoted,
        "invoiced": job_invoiced,
        "quote_url": quote_online_url,
        "invoice_url": invoice_online_url,
        "client_name": job.client.name if job.client else "No Client",
        "created_at": job.created_at.isoformat(),
        "complex_job": job.complex_job,
        "pricing_methodology": job.pricing_methodology,
        "company_defaults": company_defaults,
        "job_files": job_files,
        "has_only_summary_pdf": has_only_summary,
        "historical_job_pricings_json": historical_job_pricings_json,  # Revisions
        "latest_job_pricings_json": latest_job_pricings_json,  # Latest version
        "job_status_choices": Job.JOB_STATUS_CHOICES,
    }

    logger.debug(
        f"Rendering template for job {job.id} with job number {job.job_number}"
    )

    if DEBUG_JSON:
        try:
            # Dump the context to JSON for logging
            logger.debug(
                "Historical pricing template data: %s",
                json.dumps(historical_job_pricings_json),
            )
            logger.debug(
                "Latest pricing being passed to template: %s",
                json.dumps(latest_job_pricings_json),
            )
        except Exception as e:
            logger.error(f"Error while dumping context: {e}")

    # Render the Template
    return render(request, "jobs/edit_job_ajax.html", context)


@require_http_methods(["POST"])
def autosave_job_view(request):
    try:
        logger.info("Autosave request received")

        # Step 1: Parse the incoming JSON data
        data = json.loads(request.body)
        logger.info(f"Parsed data: {data}")

        # Step 2: Retrieve the job by ID
        job_id = data.get("job_id")
        if not job_id:
            logger.error("Job ID missing in data")
            return JsonResponse({"error": "Job ID missing"}, status=400)

        # Fetch the existing job along with all pricings
        job = get_job_with_pricings(job_id)
        logger.info(f"Job found: {job}")

        # Step 3: Pass the job and incoming data to a dedicated serializer
        # Add context with request
        serializer = JobSerializer(
            instance=job, data=data, partial=True, context={"request": request}
        )

        if DEBUG_JSON:
            logger.info(f"Initial serializer data: {serializer.initial_data}")

        if serializer.is_valid():
            if DEBUG_JSON:
                logger.debug(f"Validated data: {serializer.validated_data}")
            serializer.save(staff=request.user)
            job.latest_estimate_pricing.display_entries()  # Just for debugging

            # Logging client name for better traceability
            client_name = job.client.name if job.client else "No Client"

            logger.info(
                "Job %(id)s successfully autosaved. "
                "Current Client: %(client)s, "
                "contact_person: %(contact)s",
                {
                    "id": job_id,
                    "client": client_name,
                    "contact": job.contact_person,
                },
            )
            logger.info(
                "job_name=%(name)s, order_number=%(order)s, contact_phone=%(phone)s",
                {
                    "name": job.name,
                    "order": job.order_number,
                    "phone": job.contact_phone,
                },
            )

            return JsonResponse({"success": True, "job_id": job.id})
        else:
            logger.error(f"Validation errors: {serializer.errors}")
            return JsonResponse(
                {"success": False, "errors": serializer.errors}, status=400
            )

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        logger.exception(f"Unexpected error during autosave: {str(e)}")
        return JsonResponse({"error": "Unexpected error"}, status=500)


@require_http_methods(["POST"])
def process_month_end(request):
    """Handles month-end processing for selected jobs."""
    try:
        data = json.loads(request.body)
        job_ids = data.get("jobs", [])
        for job_id in job_ids:
            archive_and_reset_job_pricing(job_id)
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def add_job_event(request, job_id):
    """
    Create a new job event for a specific job.

    This view handles the creation of manual note events for jobs. It requires
    authentication and accepts only POST requests with JSON payload.

    Args:
        request (HttpRequest): The HTTP request object containing:
            - body (JSON): Request body with a 'description' field
            - user: Authenticated user who will be set as staff
        job_id (int): The ID of the job to create an event for

    Returns:
        JsonResponse: Response with different status codes:
            - 201: Successfully created event, includes event details
            - 400: Missing description or invalid JSON payload
            - 404: Job not found
            - 500: Unexpected server error

    Response Format (201):
        {
            "success": true,
            "event": {
                "timestamp": "ISO-8601 formatted timestamp",
                "event_type": "manual_note",
                "description": "Event description",
                "staff": "Staff display name or System"
            }
        }

    Raises:
        Job.DoesNotExist: When job_id doesn't match any job
        json.JSONDecodeError: When request body contains invalid JSON
    """
    try:
        logger.debug(f"Adding job event for job ID: {job_id}")
        job = get_object_or_404(Job, id=job_id)

        data = json.loads(request.body)
        description = data.get("description")
        if not description:
            logger.warning(f"Missing description for job event on job {job_id}")
            return JsonResponse({"error": "Description required"}, status=400)

        logger.debug(
            f"Creating job event for job {job_id} with description: {description}"
        )
        event = JobEvent.objects.create(
            job=job,
            staff=request.user,
            description=description,
            event_type="manual_note",
        )

        logger.info(f"Successfully created job event {event.id} for job {job_id}")
        return JsonResponse(
            {
                "success": True,
                "event": {
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": "manual_note",
                    "description": event.description,
                    "staff": (
                        request.user.get_display_full_name() if request.user else "System"
                    ),
                },
            },
            status=201,
        )

    except Job.DoesNotExist:
        logger.error(f"Job {job_id} not found when creating event")
        return JsonResponse({"error": "Job not found"}, status=404)

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON payload for job {job_id}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        logger.exception(
            f"Unexpected error creating job event for job {job_id}: {str(e)}"
        )
        return JsonResponse({"error": "An unexpected error occurred"}, status=500)


@require_http_methods(["POST"])
@transaction.atomic
def toggle_complex_job(request):
    try:
        # Validate input data
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return JsonResponse({"error": "Invalid request format"}, status=400)

        job_id = data.get("job_id")
        new_value = data.get("complex_job")

        # Validate required fields
        if job_id is None or new_value is None:
            return JsonResponse(
                {"error": "Missing required fields: job_id and complex_job"}, status=400
            )

        # Type validation
        if not isinstance(new_value, bool):
            return JsonResponse(
                {"error": "complex_job must be a boolean value"}, status=400
            )

        # Get job with select_for_update to prevent race conditions
        job = get_object_or_404(Job.objects.select_for_update(), id=job_id)

        if not new_value:
            valid_job: bool = False
            for pricing in job.pricings.all():
                if pricing and (
                    pricing.time_entries.count() > 1 
                    or pricing.material_entries.count() > 1 
                    or pricing.adjustment_entries.count() > 1
                ):
                    valid_job = False
                else:
                    valid_job = True
            if not valid_job:
                return JsonResponse(
                    {
                        "error": "Cannot disable complex mode with more than one pricing row",
                        "valid_job": valid_job,
                    },
                    status=400,
                )

        # Update job
        job.complex_job = new_value
        job.save()

        return JsonResponse(
            {
                "success": True,
                "job_id": job_id,
                "complex_job": new_value,
                "message": "Job updated successfully",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )


@require_http_methods(["POST"])
@transaction.atomic
def toggle_pricing_methodology(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return JsonResponse({"error": "Invalid request format"}, status=400)

        job_id = data.get("job_id")
        new_method = data.get("pricing_methodology")

        logger.info(f"[toggle_pricing_method]: data: {data}")

        if job_id is None or new_method is None:
            return JsonResponse(
                {"error": "Missing required fields: job_id and pricing_methodology"}, status=400
            )

        if new_method not in [choice[0] for choice in JobPricingMethodology.choices]:
            return JsonResponse(
                {"error": "Invalid pricing methodology value"}, status=400
            )

        job = get_object_or_404(Job.objects.select_for_update(), id=job_id)

        match (new_method):
            case JobPricingMethodology.TIME_AND_MATERIALS:
                new_method = JobPricingMethodology.TIME_AND_MATERIALS
            case JobPricingMethodology.FIXED_PRICE:
                new_method = JobPricingMethodology.FIXED_PRICE
            case _:
                return JsonResponse(
                    {"error": "Invalid pricing method value"}, status=400
                )

        # Update job
        job.pricing_methodology = new_method
        job.save()

        return JsonResponse(
            {
                "success": True,
                "job_id": job_id,
                "pricing_methodology": new_method,
                "message": "Pricing type updated successfully",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )


@require_http_methods(["POST"])
def delete_job(request, job_id):
    """
    Deletes a job if it doesn't have any reality job pricing with actual data.
    """
    job = get_object_or_404(Job, id=job_id)
    
    # Get the latest reality pricing record
    reality_pricing = job.pricings.filter(pricing_type=JobPricingType.REALITY, is_historical=False).first()
    
    # If there's a reality pricing with a total above zero, it has real costs or revenue
    if reality_pricing and (reality_pricing.total_revenue > 0 or reality_pricing.total_cost > 0):
        return JsonResponse({
            "success": False,
            "message": "You can't delete this job because it has real costs or revenue."
        }, status=400)
    
    try:
        with transaction.atomic():
            # Job pricings and job files will be deleted automatically due to CASCADE
            job_number = job.job_number
            job_name = job.name
            job.delete()
            
            return JsonResponse({
                "success": True,
                "message": f"Job #{job_number} '{job_name}' has been permanently deleted."
            })
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"An error occurred while deleting the job: {str(e)}"
        }, status=500)


@require_http_methods(["POST"])
def create_linked_quote_api(request, job_id):
    """
    Create a new linked quote from the master template for a job.
    
    Args:
        request: The HTTP request
        job_id: The UUID of the job
        
    Returns:
        JsonResponse with the URL of the newly created quote
    """
    try:
        # Get the job
        job = get_object_or_404(Job, id=job_id)
        
        # Get the client name
        client_name = job.client.name if job.client else "No Client"
        
        # Create a new quote from the template
        quote_url = create_quote_from_template(job.job_number, client_name)
        
        # Update the job with the new quote URL
        job.linked_quote = quote_url
        job.save(staff=request.user)
        
        # Create a job event to record this action
        JobEvent.objects.create(
            job=job,
            event_type="linked_quote_created",
            description=f"Created linked quote spreadsheet",
            staff=request.user,
        )
        
        # Return the URL of the new quote
        return JsonResponse({
            "success": True,
            "quote_url": quote_url,
            "message": "Linked quote created successfully"
        })
        
    except ValueError as e:
        # This will catch the error if the master template URL is not set
        logger.error(f"Error creating linked quote: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=400)
        
    except Exception as e:
        # Catch all other exceptions
        logger.exception(f"Unexpected error creating linked quote: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": "An unexpected error occurred creating a linked quote."
        }, status=500)
