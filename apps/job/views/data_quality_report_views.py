"""
Data Quality Report Views

REST views for data quality reporting.
Each data quality check has its own endpoint and response structure.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.serializers.data_quality_report_serializers import (
    ArchivedJobsComplianceResponseSerializer,
)
from apps.job.services.data_quality_report import ArchivedJobsComplianceService
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class ArchivedJobsComplianceView(APIView):
    """API view for checking archived jobs compliance."""

    @extend_schema(
        operation_id="check_archived_jobs_compliance",
        summary="Check archived jobs compliance",
        description="Verify that all archived jobs are either cancelled or fully invoiced and paid.",
        responses={
            200: ArchivedJobsComplianceResponseSerializer,
            500: dict,
        },
        tags=["Data Quality"],
    )
    def get(self, request) -> Response:
        """
        Check archived jobs compliance.

        Returns specific compliance information for archived jobs.
        """
        try:
            # Execute the check with the specific service
            service = ArchivedJobsComplianceService()
            result = service.get_compliance_report()

            # Serialize the response with the specific serializer
            serializer = ArchivedJobsComplianceResponseSerializer(data=result)
            serializer.is_valid(raise_exception=True)

            # Return the data directly without wrapping
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            persist_app_error(exc)
            logger.error(
                f"Error running archived jobs compliance check: {exc}", exc_info=True
            )
            return Response(
                {
                    "error": f"Failed to run archived jobs compliance check: {str(exc)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
