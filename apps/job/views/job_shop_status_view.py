"""
Job Shop Status API View

Provides API endpoint to check if a job is a shop job.
"""

from logging import getLogger
from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.job.serializers.job_serializer import JobShopStatusResponseSerializer
from apps.workflow.services.error_persistence import persist_app_error

logger = getLogger(__name__)


class JobShopStatusView(APIView):
    """API endpoint to check if a job is a shop job"""

    def get(self, request: Request, job_id: str, *args: Any, **kwargs: Any) -> Response:
        """
        Get shop job status for a specific job.

        Args:
            request: The HTTP request
            job_id: UUID of the job to check

        Returns:
            Response containing shop job status
        """
        try:
            # Get the job
            job = get_object_or_404(Job, id=job_id)

            # Prepare response data
            response_data = {
                "job_id": str(job.id),
                "job_number": job.job_number,
                "is_shop_job": job.shop_job,
                "client_name": job.client.name if job.client else None,
            }

            # Serialize and return response
            serializer = JobShopStatusResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.error(f"Error checking job shop status for job {job_id}: {str(exc)}")
            persist_app_error(
                exc,
                additional_context={
                    "operation": "job_shop_status_check",
                    "job_id": job_id,
                },
            )
            error_data = {"error": "Failed to check job shop status"}
            return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
