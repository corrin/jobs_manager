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
                return Response(
                    {"error": error_message}, status=status.HTTP_400_BAD_REQUEST
                )
            case "PermissionError":
                return Response(
                    {"error": error_message}, status=status.HTTP_403_FORBIDDEN
                )
            case "NotFound" | "Http404":
                return Response(
                    {"error": "Resource not found"}, status=status.HTTP_404_NOT_FOUND
                )
            case _:
                logger.exception(f"Unhandled error: {error}")
                return Response(
                    {"error": "Internal server error"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


@method_decorator(csrf_exempt, name="dispatch")
class JobCreateRestView(BaseJobRestView):
    """
    REST view for Job creation.
    Single responsibility: orchestrate job creation.
    """

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
            job = JobRestService.create_job(data, request.user)
            return Response(
                {
                    "success": True,
                    "job_id": str(job.id),
                    "job_number": job.job_number,
                    "message": "Job created successfully",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobDetailRestView(BaseJobRestView):
    """
    REST view for CRUD operations on a specific Job.
    """

    def get(self, request, job_id):
        """
        Fetch complete Job data for editing.
        """
        try:
            job_data = JobRestService.get_job_for_edit(job_id, request)

            return Response(
                {"success": True, "data": job_data}, status=status.HTTP_200_OK
            )

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
            return Response(job_data, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)

    def delete(self, request, job_id):
        """
        Delete a Job if permitted.
        """
        try:
            result = JobRestService.delete_job(job_id, request.user)
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobToggleComplexRestView(BaseJobRestView):
    """
    REST view for toggling Job complex mode.
    """

    def post(self, request):
        """
        Toggle the complex_job mode.

        Expected JSON:
        {
            "job_id": "job-uuid",
            "complex_job": true/false
        }
        """
        try:
            data = self.parse_json_body(request)

            # Guard clauses - validate required data
            if "job_id" not in data:
                raise ValueError("job_id is required")

            if "complex_job" not in data:
                raise ValueError("complex_job is required")

            result = JobRestService.toggle_complex_job(
                data["job_id"], data["complex_job"], request.user
            )

            return JsonResponse(result)

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobTogglePricingMethodologyRestView(BaseJobRestView):
    """
    DEPRECATED: This view is deprecated as pricing methodologies are not toggled.
    JobPricings are automatically created for all three stages (estimate, quote, reality)
    when a Job is created. Users interact with the existing JobPricings directly.
    """

    def post(self, request):
        """
        This endpoint is deprecated and should not be used.
        """
        return JsonResponse(
            {
                "success": False,
                "error": "This endpoint is deprecated. Pricing methodologies are not toggled - all pricing stages are created automatically.",
            },
            status=400,
        )


@method_decorator(csrf_exempt, name="dispatch")
class JobEventRestView(BaseJobRestView):
    """
    REST view for Job events.
    """

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


@method_decorator(csrf_exempt, name="dispatch")
class JobTimeEntryRestView(BaseJobRestView):
    """
    REST view for Job time entries.
    """

    def post(self, request, job_id):
        """
        Add a time entry to the Job.

        Expected JSON:
        {
            "description": "Task description",
            "hours": 4.5,
            "charge_out_rate": 105.0,
            "wage_rate": 32.0
        }
        """
        try:
            data = self.parse_json_body(request)

            # Create the time entry
            JobRestService.create_time_entry(job_id, data, request.user)

            # Get updated job data for frontend
            job_data = JobRestService.get_job_for_edit(job_id, request)

            return Response(
                {"success": True, "data": job_data}, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobMaterialEntryRestView(BaseJobRestView):
    """
    REST view for Job material entries.
    """

    def post(self, request, job_id):
        """
        Add a material entry to the Job.

        Expected JSON:
        {
            "description": "Material description",
            "quantity": 5,
            "unit_cost": 25.0,
            "unit_revenue": 35.0
        }
        """
        try:
            data = self.parse_json_body(request)

            # Create the material entry
            JobRestService.create_material_entry(job_id, data, request.user)

            # Get updated job data for frontend
            job_data = JobRestService.get_job_for_edit(job_id, request)

            return Response(
                {"success": True, "data": job_data}, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobAdjustmentEntryRestView(BaseJobRestView):
    """
    REST view for Job adjustment entries.
    """

    def post(self, request, job_id):
        """
        Add an adjustment entry to the Job.

        Expected JSON:
        {
            "description": "Adjustment description",
            "amount": 100.0
        }
        """
        try:
            data = self.parse_json_body(request)

            # Create the adjustment entry
            JobRestService.create_adjustment_entry(job_id, data, request.user)

            # Get updated job data for frontend
            job_data = JobRestService.get_job_for_edit(job_id, request)

            return Response(
                {"success": True, "data": job_data}, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return self.handle_service_error(e)
