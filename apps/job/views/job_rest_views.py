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
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.helpers import get_company_defaults
from apps.job.serializers.job_serializer import (
    JobCreateRequestSerializer,
    JobCreateResponseSerializer,
    JobDeleteResponseSerializer,
    JobDetailResponseSerializer,
    JobEventCreateRequestSerializer,
    JobEventCreateResponseSerializer,
    JobRestErrorResponseSerializer,
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

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class WeeklyMetricsRestView(BaseJobRestView):
    """
    REST view for fetching weekly metrics.
    """

    serializer = WeeklyMetricsSerializer

    @extend_schema(
        responses={200: WeeklyMetricsSerializer(many=True)},
        description="Fetch weekly metrics data.",
        tags=["Jobs"],
    )
    def get(self, request):
        """
        Fetch weekly metrics data.
        """
        try:
            # Optional week parameter for filtering
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

            metrics_data = JobRestService.get_weekly_metrics(week_date)

            serializer = WeeklyMetricsSerializer(metrics_data, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching weekly metrics: {e}")
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
