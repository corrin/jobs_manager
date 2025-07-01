"""
Kanban views - API endpoints for kanban board functionality.
All business logic delegated to KanbanService.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.job.models import Job
from apps.job.services.kanban_service import KanbanService

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fetch_all_jobs(request: Request) -> Response:
    """
    Fetch all jobs for Kanban board - API endpoint.
    """
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
            KanbanService.serialize_job_for_api(job, request) for job in archived_jobs
        ]

        return Response(
            {
                "success": True,
                "active_jobs": active_job_data,
                "archived_jobs": archived_job_data,
                "total_archived": Job.objects.filter(status="archived").count(),
            }
        )

    except Exception as e:
        logger.error(f"Error fetching all jobs: {e}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_job_status(request: Request, job_id: UUID) -> Response:
    """Update job status - API endpoint."""
    try:
        new_status = request.data.get("status")

        if not new_status:
            return Response(
                {"success": False, "error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        KanbanService.update_job_status(job_id, new_status)
        return Response({"success": True, "message": "Job status updated successfully"})

    except Job.DoesNotExist:
        return Response(
            {"success": False, "error": "Job not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reorder_job(request: Request, job_id: UUID) -> Response:
    """Reorder job within or between columns - API endpoint."""
    try:
        before_id = request.data.get("before_id")
        after_id = request.data.get("after_id")
        new_status = request.data.get("status")

        KanbanService.reorder_job(job_id, before_id, after_id, new_status)
        return Response({"success": True, "message": "Job reordered successfully"})

    except Job.DoesNotExist:
        return Response(
            {"success": False, "error": "Job not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error reordering job: {e}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fetch_jobs(request: Request, status: str) -> Response:
    """Fetch jobs by status with optional search - API endpoint."""
    try:
        search_term = request.GET.get("search", "").strip()
        search_terms = search_term.split() if search_term else []

        jobs = KanbanService.get_jobs_by_status(status, search_terms)
        total_jobs = Job.objects.filter(status=status).count()

        job_data = [KanbanService.serialize_job_for_api(job, request) for job in jobs]

        return Response(
            {
                "success": True,
                "jobs": job_data,
                "total": total_jobs,
                "filtered_count": len(job_data),
            }
        )

    except Exception as e:
        logger.error(f"Error fetching jobs by status {status}: {e}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fetch_status_values(request: Request) -> Response:
    """Return available status values for Kanban - API endpoint."""
    try:
        status_data = KanbanService.get_status_choices()
        return Response({"success": True, **status_data})

    except Exception as e:
        logger.error(f"Error fetching status values: {e}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def advanced_search(request: Request) -> Response:
    """Endpoint for advanced job search - API endpoint."""
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
        }

        jobs = KanbanService.perform_advanced_search(filters)

        job_data = [KanbanService.serialize_job_for_api(job, request) for job in jobs]

        return Response(
            {
                "success": True,
                "jobs": job_data,
                "total": len(job_data),
            }
        )

    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fetch_jobs_by_column(request: Request, column_id: str) -> Response:
    """Fetch jobs by kanban column using new categorization system."""
    try:
        max_jobs = int(request.GET.get("max_jobs", 50))
        search_term = request.GET.get("search", "")

        # Use the new categorized kanban service
        result = KanbanService.get_jobs_by_kanban_column(
            column_id, max_jobs, search_term
        )

        return Response(result)

    except ValueError as e:
        logger.error(f"Invalid parameter in fetch_jobs_by_column: {e}")
        return Response(
            {"success": False, "error": "Invalid parameters"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error fetching jobs for column {column_id}: {e}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
