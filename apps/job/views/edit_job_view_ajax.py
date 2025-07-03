import json
import logging

from django.db import transaction
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounting.models import Invoice, Quote
from apps.job.enums import JobPricingStage
from apps.job.helpers import DecimalEncoder, get_company_defaults
from apps.job.models import Job, JobEvent
from apps.job.serializers import JobPricingSerializer, JobSerializer
from apps.job.services.file_service import sync_job_folder
from apps.job.services.job_service import (
    archive_and_reset_job_pricing,
    get_historical_job_pricings,
    get_job_with_pricings,
    get_latest_job_pricings,
)
from apps.job.services.quote_sync_service import link_quote_sheet

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
    """
    Render the create job template page.
    
    Returns a simple template that handles the job creation workflow,
    typically redirecting to the job editing interface after creation.
    """
    return render(request, "jobs/create_job_and_redirect.html")


def api_fetch_status_values(request):
    """
    API endpoint to fetch all available job status values.
    
    Returns the complete list of job status choices as defined in the Job model,
    formatted as a JSON object where keys are status codes and values are
    human-readable status labels.
    
    Args:
        request (HttpRequest): The HTTP request object (GET method expected)
    
    Returns:
        JsonResponse: JSON object containing job status choices:
            {
                "quoting": "Quoting",
                "accepted_quote": "Accepted Quote",
                "awaiting_materials": "Awaiting Materials",
                "in_progress": "In Progress",
                "on_hold": "On Hold",
                "special": "Special",
                "completed": "Completed",
                "rejected": "Rejected",
                "archived": "Archived"
            }
    
    Example:
        GET /api/job/status-values/
        
        Response:
        {
            "quoting": "Quoting",
            "in_progress": "In Progress",
            ...
        }
    """
    status_values = dict(Job.JOB_STATUS_CHOICES)
    return JsonResponse(status_values)


@require_http_methods(["POST"])
def create_job_api(request):
    """
    API endpoint to create a new job with default values.
    
    Creates a new Job instance with minimal default values and automatically
    generates associated pricing records. The job is created with empty/default
    values for most fields and can be populated later via the autosave endpoint.
    
    Args:
        request (HttpRequest): The HTTP request object containing:
            - user: Authenticated user who will be set as the job creator
            - method: Must be POST
    
    Returns:
        JsonResponse: Response with different status codes:
            - 201: Successfully created job, includes job_id
            - 500: Server error during job creation
    
    Response Formats:
        Success (201):
        {
            "job_id": "uuid-string-of-new-job"
        }
        
        Error (500):
        {
            "error": "Error description"
        }
    
    Side Effects:
        - Creates new Job record in database
        - Automatically creates associated JobPricing records for estimate/quote/reality stages
        - Logs job creation event
        - Assigns incremental job number
    
    Example:
        POST /api/job/create/
        
        Response:
        {
            "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        }
    """
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
    """
    API endpoint to fetch job pricing data filtered by pricing methodology.
    
    Retrieves pricing records for a specific job that match the requested
    pricing methodology. This is used to get pricing data for specific
    calculation approaches (e.g., time_materials vs fixed_price).
    
    Args:
        request (HttpRequest): The HTTP request object containing:
            - GET parameters:
                - job_id (str): UUID of the job to fetch pricing for
                - pricing_methodology (str): Pricing method to filter by
                  (e.g., 'time_materials', 'fixed_price')
    
    Returns:
        JsonResponse: Response with different status codes:
            - 200: Successfully retrieved pricing data, returns array of pricing records
            - 400: Missing required parameters
            - 404: Job not found or no pricing data matches criteria
            - 500: Server error during data retrieval
    
    Response Formats:
        Success (200):
        [
            {
                "id": "pricing-uuid",
                "pricing_stage": "estimate",
                "pricing_methodology": "time_materials",
                "total_cost": "150.00",
                "total_revenue": "200.00",
                "created_at": "2024-01-15T10:30:00Z",
                ...
            },
            ...
        ]
        
        Error responses:
        {
            "error": "Error description"
        }
    
    Example:
        GET /api/job/pricing/?job_id=f47ac10b-58cc-4372-a567-0e02b2c3d479&pricing_methodology=time_materials
    """
    job_id = request.GET.get("job_id")
    pricing_methodology = request.GET.get("pricing_methodology")

    if not job_id or not pricing_methodology:
        return JsonResponse(
            {"error": "Missing job_id or pricing_methodology"}, status=400
        )

    try:
        # Retrieve the job with related pricings using the service function
        job = get_job_with_pricings(job_id)

        # Retrieve the pricing data by filtering the job pricings based on pricing_methodology
        pricing_data = job.pricings.filter(
            pricing_methodology=pricing_methodology
        ).values()

        if not pricing_data.exists():
            return JsonResponse(
                {
                    "error": "No data found for the provided job_id and pricing_methodology"
                },
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
    """
    Main view for editing jobs with comprehensive job data and pricing information.
    
    Renders the job editing interface with complete job details, pricing history,
    related quotes/invoices, job files, and events for a specified job.
    
    Args:
        request: HTTP request object
        job_id: UUID of the job to edit (required)
        
    Returns:
        Rendered job editing template with full job context
        
    Raises:
        ValueError: If job_id is not provided
    """
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
            "id": str(pricing.id),
            "created_at": pricing.created_at.isoformat(),
        }

        # Determine which pricing section this historical record belongs to
        section_prefix = pricing.pricing_stage

        # Process time entries
        time_entries = []
        time_cost_total = 0
        time_revenue_total = 0

        for entry in pricing.time_entries.all():
            # Calculate cost and revenue
            cost = (
                entry.wage_rate * entry.hours
                if hasattr(entry, "wage_rate") and hasattr(entry, "hours")
                else 0
            )
            revenue = (
                entry.charge_out_rate * entry.hours
                if hasattr(entry, "charge_out_rate") and hasattr(entry, "hours")
                else 0
            )

            # Add to totals
            time_cost_total += cost
            time_revenue_total += revenue

            # Create entry object
            time_entries.append(
                {
                    "id": str(entry.id),
                    "description": (
                        entry.description if hasattr(entry, "description") else ""
                    ),
                    "hours": entry.hours if hasattr(entry, "hours") else 0,
                    "cost": cost,
                    "revenue": revenue,
                }
            )

        # Assign with prefixed keys - THIS IS THE KEY CHANGE
        pricing_data[f"{section_prefix}_time_entries"] = time_entries
        pricing_data[f"{section_prefix}_time_cost"] = time_cost_total
        pricing_data[f"{section_prefix}_time_revenue"] = time_revenue_total

        # Process material entries
        material_entries = []
        material_cost_total = 0
        material_revenue_total = 0

        for entry in pricing.material_entries.all():
            # Calculate cost and revenue
            quantity = entry.quantity if hasattr(entry, "quantity") else 0
            unit_cost = entry.unit_cost if hasattr(entry, "unit_cost") else 0
            unit_revenue = entry.unit_revenue if hasattr(entry, "unit_revenue") else 0

            cost = quantity * unit_cost
            revenue = quantity * unit_revenue

            # Add to totals
            material_cost_total += cost
            material_revenue_total += revenue

            # Generate PO URL if applicable
            po_url = None
            if entry.purchase_order_line and entry.purchase_order_line.purchase_order:
                try:
                    po_url = reverse(
                        "purchasing:purchase_orders_detail",
                        kwargs={"pk": entry.purchase_order_line.purchase_order.id},
                    )
                except Exception as e:
                    logger.error(
                        f"Error generating PO URL for material entry {entry.id}: {e}"
                    )

            # Create entry object
            material_entries.append(
                {
                    "id": str(entry.id),
                    "description": (
                        entry.description if hasattr(entry, "description") else ""
                    ),
                    "quantity": quantity,
                    "cost": cost,
                    "revenue": revenue,
                    "unit_cost": unit_cost,
                    "unit_revenue": unit_revenue,
                    "po_url": po_url,  # <-- Add the PO URL here
                }
            )

        # Assign with prefixed keys
        pricing_data[f"{section_prefix}_material_entries"] = material_entries
        pricing_data[f"{section_prefix}_material_cost"] = material_cost_total
        pricing_data[f"{section_prefix}_material_revenue"] = material_revenue_total

        # Process adjustment entries
        adjustment_entries = []
        adjustment_cost_total = 0
        adjustment_revenue_total = 0

        for entry in pricing.adjustment_entries.all():
            # Get cost and revenue adjustments
            cost_adjustment = (
                entry.cost_adjustment if hasattr(entry, "cost_adjustment") else 0
            )
            price_adjustment = (
                entry.price_adjustment if hasattr(entry, "price_adjustment") else 0
            )

            # Add to totals
            adjustment_cost_total += cost_adjustment
            adjustment_revenue_total += price_adjustment

            # Create entry object
            adjustment_entries.append(
                {
                    "id": str(entry.id),
                    "description": (
                        entry.description if hasattr(entry, "description") else ""
                    ),
                    "cost": cost_adjustment,
                    "revenue": price_adjustment,
                }
            )

        # Assign with prefixed keys
        pricing_data[f"{section_prefix}_adjustment_entries"] = adjustment_entries
        pricing_data[f"{section_prefix}_adjustment_cost"] = adjustment_cost_total
        pricing_data[f"{section_prefix}_adjustment_revenue"] = adjustment_revenue_total

        # Calculate and assign total cost and revenue with prefixed keys
        pricing_data[f"{section_prefix}_total_cost"] = (
            time_cost_total + material_cost_total + adjustment_cost_total
        )
        pricing_data[f"{section_prefix}_total_revenue"] = (
            time_revenue_total + material_revenue_total + adjustment_revenue_total
        )

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
        # Job contact information is available via job.contact relationship
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
    """
    API endpoint for automatically saving job data during form editing.
    
    This endpoint handles real-time job updates as users edit job forms,
    providing seamless autosave functionality. It accepts partial job data
    and updates only the provided fields while maintaining data integrity.
    
    The endpoint supports updating all job fields including:
    - Basic job information (name, description, status, priority)
    - Client and contact information
    - Pricing methodology and rates
    - Job settings (complex_job flag, delivery dates, etc.)
    - Nested pricing entries (time, material, adjustment entries)
    
    Args:
        request (HttpRequest): The HTTP request object containing:
            - body (JSON): Job data to update, must include 'job_id'
            - user: Authenticated user performing the update
            - method: Must be POST
    
    Required JSON Fields:
        - job_id (str): UUID of the job to update
    
    Optional JSON Fields:
        - Any valid job field (name, description, status, etc.)
        - Nested pricing data for time/material/adjustment entries
        - Client and contact information
    
    Returns:
        JsonResponse: Response with different status codes:
            - 200: Successfully saved job data
            - 400: Invalid JSON payload, missing job_id, or validation errors
            - 500: Server error during save operation
    
    Response Formats:
        Success (200):
        {
            "success": true,
            "job_id": "uuid-of-updated-job"
        }
        
        Validation Error (400):
        {
            "success": false,
            "errors": {
                "field_name": ["Error message"],
                ...
            }
        }
        
        Error (400/500):
        {
            "error": "Error description"
        }
    
    Side Effects:
        - Updates job record and related pricing entries
        - Creates job event log entry for audit trail
        - May create/update client contacts if provided
        - Triggers pricing recalculations
    
    Example:
        POST /api/job/autosave/
        {
            "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "name": "Updated Job Name",
            "status": "in_progress",
            "estimate_time_entries": [
                {
                    "description": "Welding work",
                    "hours": 5.5,
                    "charge_out_rate": 85.00
                }
            ]
        }
    
    Notes:
        - Uses partial updates to avoid overwriting unchanged fields
        - Validates all data through JobSerializer before saving
        - Maintains referential integrity for related objects
        - Logs detailed information for debugging and audit purposes
    """
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
                    "contact": job.contact.name if job.contact else None,
                },
            )
            logger.info(
                "job_name=%(name)s, order_number=%(order)s, contact_phone=%(phone)s",
                {
                    "name": job.name,
                    "order": job.order_number,
                    "phone": job.contact.phone if job.contact else None,
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
                        request.user.get_display_full_name()
                        if request.user
                        else "System"
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
    """
    API endpoint to toggle the complex job mode for a specific job.
    
    Complex job mode (also called "itemised billing") determines whether a job
    can have multiple pricing entries per category (time, materials, adjustments)
    or is limited to single entries per category for simplified billing.
    
    When disabling complex mode, the system validates that the job doesn't have
    multiple pricing entries that would be incompatible with simple mode.
    
    Args:
        request (HttpRequest): The HTTP request object containing:
            - body (JSON): Request data with job_id and complex_job flag
            - user: Authenticated user (for audit logging)
            - method: Must be POST
    
    Required JSON Fields:
        - job_id (str): UUID of the job to update
        - complex_job (bool): New value for complex job mode
    
    Returns:
        JsonResponse: Response with different status codes:
            - 200: Successfully toggled complex job mode
            - 400: Invalid request format, missing fields, validation errors
            - 500: Server error during update
    
    Response Formats:
        Success (200):
        {
            "success": true,
            "job_id": "uuid-of-job",
            "complex_job": true,
            "message": "Job updated successfully"
        }
        
        Validation Error (400):
        {
            "error": "Cannot disable complex mode with more than one pricing row",
            "valid_job": false
        }
        
        Error (400/500):
        {
            "error": "Error description"
        }
    
    Business Rules:
        - Complex mode can always be enabled
        - Complex mode can only be disabled if ALL pricing stages have ≤1 entry per type
        - Uses database locking to prevent race conditions
        - Creates audit log entry for the change
    
    Side Effects:
        - Updates job.complex_job field
        - May create job event for audit trail
        - Validates pricing entry constraints
    
    Example:
        POST /api/job/toggle-complex/
        {
            "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "complex_job": false
        }
    
    Notes:
        - Uses select_for_update() to prevent concurrent modifications
        - Validates business rules before making changes
        - Atomic transaction ensures data consistency
    """
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
def delete_job(request, job_id):
    """
    Deletes a job if it doesn't have any reality job pricing with actual data.
    """
    job = get_object_or_404(Job, id=job_id)

    # Get the latest reality pricing record
    reality_pricing = job.pricings.filter(
        pricing_stage=JobPricingStage.REALITY, is_historical=False
    ).first()

    # If there's a reality pricing with a total above zero, it has real costs or revenue
    if reality_pricing and (
        reality_pricing.total_revenue > 0 or reality_pricing.total_cost > 0
    ):
        return JsonResponse(
            {
                "success": False,
                "message": "You can't delete this job because it has real costs or revenue.",
            },
            status=400,
        )

    try:
        with transaction.atomic():
            # Job pricings and job files will be deleted automatically due to CASCADE
            job_number = job.job_number
            job_name = job.name
            job.delete()

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Job #{job_number} '{job_name}' has been permanently deleted.",
                }
            )
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "message": f"An error occurred while deleting the job: {str(e)}",
            },
            status=500,
        )


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

        # Create a new quote from the template
        quote_spreadsheet = link_quote_sheet(job)

        # Update the job with the new quote URL
        job.linked_quote = quote_spreadsheet.url
        job.save(staff=request.user)  # Create a job event to record this action
        JobEvent.objects.create(
            job=job,
            event_type="quote_created",
            description="Quote spreadsheet created and linked",
            staff=request.user,
        )

        # Return the URL of the new quote
        return JsonResponse(
            {
                "success": True,
                "quote_url": quote_spreadsheet.url,
                "message": "Linked quote created successfully",
            }
        )

    except ValueError as e:
        # This will catch the error if the master template URL is not set
        logger.error(f"Error creating linked quote: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    except Exception as e:
        # Catch all other exceptions
        logger.exception(f"Unexpected error creating linked quote: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "error": "An unexpected error occurred creating a linked quote.",
            },
            status=500,
        )
