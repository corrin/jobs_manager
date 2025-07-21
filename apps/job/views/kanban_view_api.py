"""
Kanban views - API endpoints for kanban board functionality.
All business logic delegated to KanbanService.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.job.serializers import (
    AdvancedSearchResponseSerializer,
    FetchAllJobsResponseSerializer,
    FetchJobsByColumnResponseSerializer,
    FetchJobsResponseSerializer,
    FetchStatusValuesResponseSerializer,
    JobReorderRequestSerializer,
    JobStatusUpdateRequestSerializer,
    KanbanErrorResponseSerializer,
    KanbanSuccessResponseSerializer,
)
from apps.job.services.kanban_service import KanbanService

logger = logging.getLogger(__name__)


class FetchAllJobsAPIView(APIView):
    """
    Fetch all jobs for Kanban board - API endpoint.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FetchAllJobsResponseSerializer

    def get(self, request: Request) -> Response:
        try:
            # Get active jobs
            active_jobs = KanbanService.get_all_active_jobs()

            # Get archived jobs
            archived_jobs = KanbanService.get_archived_jobs(50)

            # Serialize jobs
            active_job_data = [
                KanbanService.serialize_job_for_api(job, request) for job in active_jobs
            ]

            archived_job_data = [
                KanbanService.serialize_job_for_api(job, request)
                for job in archived_jobs
            ]

            response_data = {
                "success": True,
                "active_jobs": active_job_data,
                "archived_jobs": archived_job_data,
                "total_archived": Job.objects.filter(status="archived").count(),
            }

            success_serializer = FetchAllJobsResponseSerializer(data=response_data)
            success_serializer.is_valid(raise_exception=True)
            return Response(success_serializer.data)

        except Exception as e:
            logger.error(f"Error fetching all jobs: {e}")
            error_response = {
                "success": False,
                "error": str(e),
                "active_jobs": [],
                "archived_jobs": [],
                "total_archived": 0,
            }
            error_serializer = FetchAllJobsResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateJobStatusAPIView(APIView):
    """Update job status - API endpoint."""

    permission_classes = [IsAuthenticated]
    serializer_class = KanbanSuccessResponseSerializer

    def get_serializer_class(self):
        """Return the serializer class for documentation"""
        if self.request.method == "POST":
            return JobStatusUpdateRequestSerializer
        return KanbanSuccessResponseSerializer

    def post(self, request: Request, job_id: UUID) -> Response:
        try:
            # Validate input data
            serializer = JobStatusUpdateRequestSerializer(data=request.data)
            if not serializer.is_valid():
                error_response = {
                    "success": False,
                    "error": f"Invalid input data: {serializer.errors}",
                }
                error_serializer = KanbanErrorResponseSerializer(data=error_response)
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            new_status = serializer.validated_data["status"]

            KanbanService.update_job_status(job_id, new_status)

            # Return success response
            success_response = {
                "success": True,
                "message": "Job status updated successfully",
            }
            success_serializer = KanbanSuccessResponseSerializer(data=success_response)
            success_serializer.is_valid(raise_exception=True)
            return Response(success_serializer.data)

        except Job.DoesNotExist:
            error_response = {"success": False, "error": "Job not found"}
            error_serializer = KanbanErrorResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error updating job status: {e}")
            error_response = {"success": False, "error": str(e)}
            error_serializer = KanbanErrorResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReorderJobAPIView(APIView):
    """Reorder job within or between columns - API endpoint."""

    permission_classes = [IsAuthenticated]
    serializer_class = KanbanSuccessResponseSerializer

    def get_serializer_class(self):
        """Return the serializer class for documentation"""
        if self.request.method == "POST":
            return JobReorderRequestSerializer
        return KanbanSuccessResponseSerializer

    def post(self, request: Request, job_id: UUID) -> Response:
        try:
            # Validate input data
            serializer = JobReorderRequestSerializer(data=request.data)
            if not serializer.is_valid():
                error_response = {
                    "success": False,
                    "error": f"Invalid input data: {serializer.errors}",
                }
                error_serializer = KanbanErrorResponseSerializer(data=error_response)
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            validated_data = serializer.validated_data
            before_id = validated_data.get("before_id")
            after_id = validated_data.get("after_id")
            new_status = validated_data.get("status")

            KanbanService.reorder_job(job_id, before_id, after_id, new_status)

            # Return success response
            success_response = {
                "success": True,
                "message": "Job reordered successfully",
            }
            success_serializer = KanbanSuccessResponseSerializer(data=success_response)
            success_serializer.is_valid(raise_exception=True)
            return Response(success_serializer.data)

        except Job.DoesNotExist:
            error_response = {"success": False, "error": "Job not found"}
            error_serializer = KanbanErrorResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error reordering job: {e}")
            error_response = {"success": False, "error": str(e)}
            error_serializer = KanbanErrorResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FetchJobsAPIView(APIView):
    """Fetch jobs by status with optional search - API endpoint."""

    permission_classes = [IsAuthenticated]
    serializer_class = FetchJobsResponseSerializer

    def get(self, request: Request, status: str) -> Response:
        try:
            search_term = request.GET.get("search", "").strip()
            search_terms = search_term.split() if search_term else []

            jobs = KanbanService.get_jobs_by_status(status, search_terms)
            total_jobs = Job.objects.filter(status=status).count()

            job_data = [
                KanbanService.serialize_job_for_api(job, request) for job in jobs
            ]

            response_data = {
                "success": True,
                "jobs": job_data,
                "total": total_jobs,
                "filtered_count": len(job_data),
            }
            success_serializer = FetchJobsResponseSerializer(data=response_data)
            success_serializer.is_valid(raise_exception=True)
            return Response(success_serializer.data)

        except Exception as e:
            logger.error(f"Error fetching jobs by status {status}: {e}")
            error_response = {
                "success": False,
                "error": str(e),
                "jobs": [],
                "total": 0,
                "filtered_count": 0,
            }
            error_serializer = FetchJobsResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FetchStatusValuesAPIView(APIView):
    """Return available status values for Kanban - API endpoint."""

    permission_classes = [IsAuthenticated]
    serializer_class = FetchStatusValuesResponseSerializer

    def get(self, request: Request) -> Response:
        try:
            status_data = KanbanService.get_status_choices()
            response_data = {"success": True, **status_data}
            success_serializer = FetchStatusValuesResponseSerializer(data=response_data)
            success_serializer.is_valid(raise_exception=True)
            return Response(success_serializer.data)

        except Exception as e:
            logger.error(f"Error fetching status values: {e}")
            error_response = {
                "success": False,
                "error": str(e),
                "statuses": {},
                "tooltips": {},
            }
            error_serializer = FetchStatusValuesResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdvancedSearchAPIView(APIView):
    """Endpoint for advanced job search - API endpoint."""

    permission_classes = [IsAuthenticated]
    serializer_class = AdvancedSearchResponseSerializer

    def get(self, request: Request) -> Response:
        try:
            # Extract filters from GET parameters
            filters = {
                "job_number": request.GET.get("job_number", ""),
                "name": request.GET.get("name", ""),
                "description": request.GET.get("description", ""),
                "client_name": request.GET.get("client_name", ""),
                "contact_person": request.GET.get("contact_person", ""),
                "created_by": request.GET.get("created_by", ""),
                "created_after": request.GET.get("created_after", ""),
                "created_before": request.GET.get("created_before", ""),
                "status": request.GET.getlist("status"),
                "paid": request.GET.get("paid", ""),
                "xero_invoice_params": request.GET.get("xero_invoice_params", ""),
            }

            jobs = KanbanService.perform_advanced_search(filters)

            job_data = [
                KanbanService.serialize_job_for_api(job, request) for job in jobs
            ]

            response_data = {
                "success": True,
                "jobs": job_data,
                "total": len(job_data),
            }
            success_serializer = AdvancedSearchResponseSerializer(data=response_data)
            success_serializer.is_valid(raise_exception=True)
            return Response(success_serializer.data)

        except Exception as e:
            logger.error(f"Error in advanced search: {e}")
            error_response = {
                "success": False,
                "error": str(e),
                "jobs": [],
                "total": 0,
            }
            error_serializer = AdvancedSearchResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FetchJobsByColumnAPIView(APIView):
    """Fetch jobs by kanban column using new categorization system."""

    permission_classes = [IsAuthenticated]
    serializer_class = FetchJobsByColumnResponseSerializer

    def get(self, request: Request, column_id: str) -> Response:
        try:
            max_jobs = int(request.GET.get("max_jobs", 50))
            search_term = request.GET.get("search", "")

            # Use the new categorized kanban service
            result = KanbanService.get_jobs_by_kanban_column(
                column_id, max_jobs, search_term
            )

            # Serialize the response
            response_serializer = FetchJobsByColumnResponseSerializer(data=result)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data)

        except ValueError as e:
            logger.error(f"Invalid parameter in fetch_jobs_by_column: {e}")
            error_response = {
                "success": False,
                "error": "Invalid parameters",
                "jobs": [],
                "total": 0,
                "filtered_count": 0,
            }
            error_serializer = FetchJobsByColumnResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching jobs for column {column_id}: {e}")
            error_response = {
                "success": False,
                "error": str(e),
                "jobs": [],
                "total": 0,
                "filtered_count": 0,
            }
            error_serializer = FetchJobsByColumnResponseSerializer(data=error_response)
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
