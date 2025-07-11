from logging import getLogger

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.serializers import (
    JobAgingQuerySerializer,
    JobAgingResponseSerializer,
    StandardErrorSerializer,
)
from apps.accounting.services import JobAgingService
from apps.workflow.services.error_persistence import persist_app_error

logger = getLogger(__name__)


class JobAgingAPIView(APIView):
    """API Endpoint to provide job aging data with financial and timing information"""

    def get_serializer_class(self):
        """Return the serializer class for documentation"""
        if self.request.method == "GET":
            return JobAgingResponseSerializer
        return JobAgingQuerySerializer

    def get(self, request, *args, **kwargs):
        """
        Get job aging data.

        Query Parameters:
            include_archived (bool): Whether to include archived jobs. Defaults to False.

        Returns:
            JSON response with job aging data structure
        """
        try:
            # Validate query parameters
            query_serializer = JobAgingQuerySerializer(data=request.query_params)
            if not query_serializer.is_valid():
                error_serializer = StandardErrorSerializer(
                    data={
                        "error": "Invalid query parameters",
                        "details": query_serializer.errors,
                    }
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get job aging data from service
            job_aging_data = JobAgingService.get_job_aging_data(
                include_archived=query_serializer.validated_data.get(
                    "include_archived", False
                )
            )

            # Serialize response
            response_serializer = JobAgingResponseSerializer(data=job_aging_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.error(f"Job Aging API Error: {str(exc)}")
            persist_app_error(exc)

            error_serializer = StandardErrorSerializer(
                data={"error": f"Error obtaining job aging data: {str(exc)}"}
            )
            error_serializer.is_valid(raise_exception=True)

            return Response(
                error_serializer.data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
