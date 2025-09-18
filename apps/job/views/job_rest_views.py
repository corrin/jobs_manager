"""
Job REST Views

REST views for the Job module following clean code principles:
- SRP (Single Responsibility Principle)
- Early return and guard clauses
- Delegation to service layer
- Views as orchestrators only
"""

import json
import logging
from typing import Any, Dict

from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.helpers import get_company_defaults
from apps.job.models import Job
from apps.job.serializers.job_serializer import (
    JobBasicInformationResponseSerializer,
    JobCostSummaryResponseSerializer,
    JobCreateRequestSerializer,
    JobCreateResponseSerializer,
    JobDeleteResponseSerializer,
    JobDetailResponseSerializer,
    JobEventCreateRequestSerializer,
    JobEventCreateResponseSerializer,
    JobEventsResponseSerializer,
    JobHeaderResponseSerializer,
    JobInvoicesResponseSerializer,
    JobPatchRequestSerializer,
    JobQuoteAcceptanceSerializer,
    JobRestErrorResponseSerializer,
    JobStatusChoicesResponseSerializer,
    QuoteSerializer,
    WeeklyMetricsSerializer,
)
from apps.job.services.job_rest_service import JobRestService

logger = logging.getLogger(__name__)


class BaseJobRestView(APIView):
    """
    Base view for Job REST operations.
    Implements common functionality like JSON parsing and error handling.
    Inherits from APIView for JWT authentication support.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """Remove manual authentication check - let DRF handle it."""
        return super().dispatch(request, *args, **kwargs)

    def parse_json_body(self, request) -> Dict[str, Any]:
        """
        Parse the JSON body of the request.
        Apply early return in case of error.
        """
        if not request.body:
            raise ValueError("Request body is empty")

        try:
            return json.loads(request.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def handle_service_error(self, error: Exception) -> Response:
        """
        Centralise service layer error handling with error persistence.
        """
        try:
            # Persist error for debugging
            from apps.workflow.services.error_persistence import persist_app_error

            persist_app_error(error)
            logger.error(
                f"[JOB-REST-VIEW] Handled and persisted error {str(error)} in database."
            )
        except Exception as persist_error:
            logger.error(f"Failed to persist error: {persist_error}")

        error_message = str(error)

        match type(error).__name__:
            case "ValueError":
                error_response = {"error": error_message}
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )
            case "PermissionError":
                error_response = {"error": error_message}
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(error_serializer.data, status=status.HTTP_403_FORBIDDEN)
            case "IntegrityError":
                # Handle database constraint violations (duplicates)
                error_response = {
                    "error": "Duplicate event prevented by database constraint"
                }
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(error_serializer.data, status=status.HTTP_409_CONFLICT)
            case "NotFound" | "Http404":
                error_response = {"error": "Resource not found"}
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)
            case _:
                logger.exception(f"Unhandled error: {error}")
                error_response = {"error": "Internal server error"}
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(
                    error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    def check_request_debounce(
        self, request, operation_key: str, debounce_seconds: int = 2
    ) -> bool:
        """
        Check if request is within debounce period.

        Args:
            request: HTTP request
            operation_key: Unique key for the operation
            debounce_seconds: Seconds to debounce

        Returns:
            bool: True if should be blocked (within debounce period)
        """
        user_id = str(request.user.id) if request.user.is_authenticated else "anonymous"
        cache_key = f"debounce:{operation_key}:{user_id}"

        # Check if entry exists in cache
        if cache.get(cache_key):
            return True  # Block - within debounce period

        # Set cache entry
        cache.set(cache_key, True, debounce_seconds)
        return False  # Allow - outside debounce period


@method_decorator(csrf_exempt, name="dispatch")
class JobCreateRestView(BaseJobRestView):
    """
    REST view for Job creation.
    Single responsibility: orchestrate job creation.
    """

    serializer_class = JobCreateResponseSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "POST":
            return JobCreateRequestSerializer
        return JobCreateResponseSerializer

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance for the request for OpenAPI compatibility"""
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    @extend_schema(
        request=JobCreateRequestSerializer,
        responses={
            201: JobCreateResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Create a new Job.",
        tags=["Jobs"],
    )
    def post(self, request):
        """
        Create a new Job.

        Expected JSON:
        {
            "name": "Job Name",
            "client_id": "client-uuid",
            "description": "Optional description",
            "order_number": "Optional order number",
            "notes": "Optional notes",
            "contact_id": "optional-contact-uuid"
            "pricing_methodology": "Optional methodology (defaults to T&M)"
        }
        """
        try:
            data = self.parse_json_body(request)

            # Validate input data
            input_serializer = JobCreateRequestSerializer(data=data)
            if not input_serializer.is_valid():
                error_response = {
                    "error": f"Validation failed: {input_serializer.errors}"
                }
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            job = JobRestService.create_job(
                input_serializer.validated_data, request.user
            )

            response_data = {
                "success": True,
                "job_id": str(job.id),
                "job_number": job.job_number,
                "message": "Job created successfully",
            }

            response_serializer = JobCreateResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobDetailRestView(BaseJobRestView):
    """
    REST view for CRUD operations on a specific Job.
    """

    serializer_class = JobDetailResponseSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "DELETE":
            return JobDeleteResponseSerializer
        return JobDetailResponseSerializer

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance for the request for OpenAPI compatibility"""
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    @extend_schema(
        responses={200: JobDetailResponseSerializer},
        description="Fetch complete job data including financial information",
        tags=["Jobs"],
        operation_id="getFullJob",
    )
    def get(self, request, job_id):
        """
        Fetch complete Job data for editing.
        """
        try:
            job_data = JobRestService.get_job_for_edit(job_id, request)

            # The service returns already-serialized data, so return it directly
            response_data = {"success": True, "data": job_data}
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)

    @extend_schema(
        request=JobDetailResponseSerializer,
        responses={
            200: JobDetailResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Update Job data (autosave).",
        tags=["Jobs"],
    )
    def put(self, request, job_id):
        """
        Update Job data (autosave).
        """
        try:
            data = self.parse_json_body(request)

            # Update the job using the service layer
            JobRestService.update_job(job_id, data, request.user)

            # Return complete job data for frontend reactivity
            job_data = JobRestService.get_job_for_edit(job_id, request)

            # The service returns already-serialized data, so wrap it properly
            response_data = {"success": True, "data": job_data}
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)

    @extend_schema(
        request=JobPatchRequestSerializer,
        responses={
            200: JobDetailResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Partially update Job data. Only updates the fields provided in the request body.",
        tags=["Jobs"],
    )
    def patch(self, request, job_id):
        """
        Partially update Job data.
        Only updates the fields provided in the request body.
        """
        try:
            data = self.parse_json_body(request)

            # Validate input data with PATCH-specific serializer
            input_serializer = JobPatchRequestSerializer(data=data)
            if not input_serializer.is_valid():
                error_response = {
                    "error": f"Validation failed: {input_serializer.errors}"
                }
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            # Update the job using the service layer (supports partial updates)
            JobRestService.update_job(
                job_id, input_serializer.validated_data, request.user
            )

            # Return complete job data for frontend reactivity
            job_data = JobRestService.get_job_for_edit(job_id, request)

            # The service returns already-serialized data, so wrap it properly
            response_data = {"success": True, "data": job_data}
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)

    @extend_schema(
        responses={
            200: JobDeleteResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Delete a Job if permitted.",
        tags=["Jobs"],
    )
    def delete(self, request, job_id):
        """
        Delete a Job if permitted.
        """
        try:
            result = JobRestService.delete_job(job_id, request.user)

            # Serialize the result properly
            response_serializer = JobDeleteResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as v:
            logger.error("Error deleting job: valid data found.")
            error = {"error": str(v)}
            return Response(
                JobRestErrorResponseSerializer(error).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobEventRestView(BaseJobRestView):
    """
    REST view for Job events.
    """

    serializer_class = JobEventCreateResponseSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "POST":
            return JobEventCreateRequestSerializer
        return JobEventCreateResponseSerializer

    @extend_schema(
        request=JobEventCreateRequestSerializer,
        responses={
            201: JobEventCreateResponseSerializer,
            409: JobRestErrorResponseSerializer,
            400: JobRestErrorResponseSerializer,
            429: JobRestErrorResponseSerializer,
        },
        description="Add a manual event to the Job with duplicate prevention.",
        tags=["Jobs"],
        operation_id="job_rest_jobs_events_create",
    )
    def post(self, request, job_id):
        """
        Add a manual event to the Job with duplicate prevention.

        Expected JSON:
        {
            "description": "Event description"
        }
        """
        try:
            # Debounce check - prevent rapid requests
            debounce_key = f"add_event:{job_id}"
            if self.check_request_debounce(request, debounce_key, debounce_seconds=2):
                logger.warning(
                    f"Request debounced for user {request.user.email} on job {job_id}"
                )
                error_response = {
                    "error": "Request too frequent. Please wait before adding another event."
                }
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(
                    error_serializer.data, status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            data = self.parse_json_body(request)

            # Validate input data
            input_serializer = JobEventCreateRequestSerializer(data=data)
            if not input_serializer.is_valid():
                error_response = {
                    "error": f"Validation failed: {input_serializer.errors}"
                }
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            # Additional duplicate check via cache
            description = input_serializer.validated_data["description"].strip()
            duplicate_check_key = (
                f"event_duplicate:{job_id}:{request.user.id}:{hash(description)}"
            )

            if cache.get(duplicate_check_key):
                logger.warning(
                    f"Duplicate event prevented via cache for user {request.user.email} on job {job_id}"
                )
                error_response = {
                    "error": "Duplicate event detected. An identical event was recently created."
                }
                error_serializer = JobRestErrorResponseSerializer(error_response)
                return Response(error_serializer.data, status=status.HTTP_409_CONFLICT)

            # Create event via service
            result = JobRestService.add_job_event(job_id, description, request.user)

            # Set duplicate prevention cache (5 minutes)
            cache.set(duplicate_check_key, True, 300)

            # Return appropriate status based on whether duplicate was prevented
            if result.get("duplicate_prevented"):
                response_serializer = JobEventCreateResponseSerializer(result)
                return Response(
                    response_serializer.data, status=status.HTTP_409_CONFLICT
                )
            else:
                response_serializer = JobEventCreateResponseSerializer(result)
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteAcceptRestView(BaseJobRestView):
    """
    REST view for accepting job quotes.
    """

    serializer_class = JobQuoteAcceptanceSerializer

    @extend_schema(
        responses={
            200: JobQuoteAcceptanceSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Accept a quote for the job. Sets the quote_acceptance_date to current datetime.",
        tags=["Jobs"],
    )
    def post(self, request, job_id):
        """
        Accept a quote for the job.
        Sets the quote_acceptance_date to current datetime.
        """
        try:
            result = JobRestService.accept_quote(job_id, request.user)

            # Create response with proper typing
            response_data = {
                "success": result["success"],
                "job_id": result["job_id"],
                "quote_acceptance_date": result["quote_acceptance_date"],
                "message": result["message"],
            }

            payload = JobQuoteAcceptanceSerializer(response_data).data

            return Response(payload, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class WeeklyMetricsRestView(BaseJobRestView):
    """
    REST view for fetching weekly metrics.
    """

    serializer = WeeklyMetricsSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="week",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Month (1-12). Defaults to current month.",
            ),
        ],
        responses={200: WeeklyMetricsSerializer(many=True)},
        description="Fetch weekly metrics data for jobs with time entries in the specified week.",
        tags=["Jobs"],
    )
    def get(self, request):
        """
        Fetch weekly metrics data.
        """
        try:
            week_param = request.query_params.get("week")
            week_date = None
            if week_param:
                from django.utils.dateparse import parse_date

                week_date = parse_date(week_param)
                if not week_date:
                    error_response = {
                        "error": "Invalid week date format. Use YYYY-MM-DD"
                    }
                    error_serializer = JobRestErrorResponseSerializer(error_response)
                    return Response(
                        error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                    )

            logger.info(
                f"WeeklyMetricsRestView: week_param={week_param}, week_date={week_date}"
            )

            metrics_data = JobRestService.get_weekly_metrics(week_date)

            serializer = WeeklyMetricsSerializer(metrics_data, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching weekly metrics: {e}")
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobHeaderRestView(BaseJobRestView):
    """
    REST view for Job header information.
    Returns essential job data for fast initial loading.
    """

    serializer_class = JobHeaderResponseSerializer

    @extend_schema(
        responses={
            200: JobHeaderResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Fetch essential job header information for fast loading",
        tags=["Jobs"],
    )
    def get(self, request, job_id):
        """
        Fetch essential job header data for fast initial loading.
        """
        try:
            job = Job.objects.select_related("client").get(id=job_id)

            # Build essential header data only
            header_data = {
                "job_id": str(job.id),
                "job_number": job.job_number,
                "name": job.name,
                "client": {"id": str(job.client.id), "name": job.client.name}
                if job.client
                else None,
                "status": job.status,
                "pricing_methodology": job.pricing_methodology,
                "fully_invoiced": job.fully_invoiced,
                "quoted": job.quoted,
                "quote_acceptance_date": job.quote_acceptance_date.isoformat()
                if job.quote_acceptance_date
                else None,
                "paid": job.paid,
            }

            return Response(header_data, status=status.HTTP_200_OK)

        except Job.DoesNotExist:
            raise ValueError(f"Job with id {job_id} not found")
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobInvoicesRestView(BaseJobRestView):
    """
    REST view for Job invoices.
    Returns list of invoices for a job.
    """

    serializer_class = JobInvoicesResponseSerializer

    @extend_schema(
        responses={
            200: JobInvoicesResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Fetch job invoices list",
        tags=["Jobs"],
    )
    def get(self, request, job_id):
        """
        Fetch job invoices.
        """
        try:
            invoices = JobRestService.get_job_invoices(job_id)

            serializer = JobInvoicesResponseSerializer({"invoices": invoices})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteRestView(BaseJobRestView):
    """
    REST view for Job quotes.
    Returns the xero quote for a job.
    """

    serializer_class = QuoteSerializer

    @extend_schema(
        responses={
            200: QuoteSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Fetch job quote",
        tags=["Jobs"],
    )
    def get(self, request, job_id):
        """
        Fetch job quote.
        """
        try:
            quote = JobRestService.get_job_quote(job_id)

            return Response(quote, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobCostSummaryRestView(BaseJobRestView):
    """
    REST view for Job cost summary.
    Returns cost summary across all cost sets.
    """

    serializer_class = JobCostSummaryResponseSerializer

    @extend_schema(
        responses={
            200: JobCostSummaryResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Fetch job cost summary across all cost sets",
        tags=["Jobs"],
    )
    def get(self, request, job_id):
        """
        Fetch job cost summary in frontend-expected format.
        """
        try:
            job = Job.objects.get(id=job_id)

            # Get summaries from all cost sets
            estimate = job.get_latest("estimate")
            quote = job.get_latest("quote")
            actual = job.get_latest("actual")

            def calculate_profit_margin(cost_set):
                """Calculate profit margin as (rev - cost) / cost * 100"""
                if not cost_set or not cost_set.summary:
                    return None
                summary = cost_set.summary
                cost = summary.get("cost", 0)
                rev = summary.get("rev", 0)
                if cost and cost > 0:
                    return ((rev - cost) / cost) * 100
                return 0

            # Build frontend-expected summary data with profitMargin
            summary_data = {
                "estimate": {
                    "cost": estimate.summary.get("cost", 0)
                    if estimate and estimate.summary
                    else 0,
                    "rev": estimate.summary.get("rev", 0)
                    if estimate and estimate.summary
                    else 0,
                    "hours": estimate.summary.get("hours", 0)
                    if estimate and estimate.summary
                    else 0,
                    "profitMargin": calculate_profit_margin(estimate),
                }
                if estimate and estimate.summary
                else None,
                "quote": {
                    "cost": quote.summary.get("cost", 0)
                    if quote and quote.summary
                    else 0,
                    "rev": quote.summary.get("rev", 0)
                    if quote and quote.summary
                    else 0,
                    "hours": quote.summary.get("hours", 0)
                    if quote and quote.summary
                    else 0,
                    "profitMargin": calculate_profit_margin(quote),
                }
                if quote and quote.summary
                else None,
                "actual": {
                    "cost": actual.summary.get("cost", 0)
                    if actual and actual.summary
                    else 0,
                    "rev": actual.summary.get("rev", 0)
                    if actual and actual.summary
                    else 0,
                    "hours": actual.summary.get("hours", 0)
                    if actual and actual.summary
                    else 0,
                    "profitMargin": calculate_profit_margin(actual),
                }
                if actual and actual.summary
                else None,
            }

            serializer = JobCostSummaryResponseSerializer(summary_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Job.DoesNotExist:
            raise ValueError(f"Job with id {job_id} not found")
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobStatusChoicesRestView(BaseJobRestView):
    """
    REST view for Job status choices.
    Returns available status choices for jobs.
    """

    serializer_class = JobStatusChoicesResponseSerializer

    @extend_schema(
        responses={
            200: JobStatusChoicesResponseSerializer,
        },
        description="Fetch job status choices",
        tags=["Jobs"],
    )
    def get(self, request):
        """
        Fetch job status choices.
        """
        try:
            from apps.job.models.job import Job

            # Get status choices from model
            status_choices = dict(Job.STATUS_CHOICES)

            response_data = {"statuses": status_choices}
            serializer = JobStatusChoicesResponseSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobEventListRestView(BaseJobRestView):
    """
    REST view for Job events list.
    Returns list of events for a job.
    """

    serializer_class = JobEventsResponseSerializer

    @extend_schema(
        responses={
            200: JobEventsResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Fetch job events list",
        tags=["Jobs"],
    )
    def get(self, request, job_id):
        """
        Fetch job events.
        """
        try:
            job = Job.objects.get(id=job_id)
            events = job.events.all().order_by("-timestamp")

            serializer = JobEventsResponseSerializer({"events": events})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Job.DoesNotExist:
            raise ValueError(f"Job with id {job_id} not found")
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobBasicInformationRestView(BaseJobRestView):
    """
    REST view for Job basic information.
    Returns description, delivery date, order number and internal notes.
    """

    serializer_class = JobBasicInformationResponseSerializer

    @extend_schema(
        responses={
            200: JobBasicInformationResponseSerializer,
            400: JobRestErrorResponseSerializer,
        },
        description="Fetch job basic information (description, delivery date, order number, notes)",
        tags=["Jobs"],
    )
    def get(self, request, job_id):
        """
        Fetch job basic information.
        """
        try:
            basic_info = JobRestService.get_job_basic_information(job_id)

            serializer = JobBasicInformationResponseSerializer(basic_info)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)


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
