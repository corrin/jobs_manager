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

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.helpers import get_company_defaults
from apps.job.serializers.job_serializer import (
    JobCreateRequestSerializer,
    JobCreateResponseSerializer,
    JobDeleteResponseSerializer,
    JobDetailResponseSerializer,
    JobRestErrorResponseSerializer,
    JobSerializer,
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
        Centralise service layer error handling.
        """
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

    def get(self, request, job_id):
        """
        Fetch complete Job data for editing.
        """
        try:
            job_data = JobRestService.get_job_for_edit(job_id, request)

            response_data = {"success": True, "data": job_data}
            response_serializer = JobDetailResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)

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

            # Since this returns the job data directly, we'll serialize it properly
            job_serializer = JobSerializer(job_data, context={"request": request})
            return Response(job_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)

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

    serializer_class = JobRestErrorResponseSerializer

    def post(self, request, job_id):
        """
        Add a manual event to the Job.

        Expected JSON:
        {
            "description": "Event description"
        }
        """
        try:
            data = self.parse_json_body(request)

            # Guard clause
            if "description" not in data:
                raise ValueError("description is required")

            result = JobRestService.add_job_event(
                job_id, data["description"], request.user
            )

            return JsonResponse(result, status=201)

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
