from logging import getLogger
from typing import Any, Type

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.accounting.serializers import (
    JobAgingQuerySerializer,
    JobAgingResponseSerializer,
    StandardErrorSerializer,
)
from apps.accounting.services import JobAgingService
from apps.workflow.services.error_persistence import (
    extract_request_context,
    persist_app_error,
)

logger = getLogger(__name__)


class JobAgingAPIView(APIView):
    """API Endpoint to provide job aging data with financial and timing information"""

    def get_serializer_class(self) -> Type[Serializer[Any]]:
        """Return the serializer class for documentation"""
        if self.request.method == "GET":
            return JobAgingResponseSerializer
        return JobAgingQuerySerializer

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Get job aging data.

        Query Parameters:
            include_archived (bool): Whether to include archived jobs.
                Defaults to False.

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

            # Extract request context
            request_context = extract_request_context(request)

            persist_app_error(
                exc,
                user_id=request_context["user_id"],
                additional_context={
                    "operation": "job_aging_api_endpoint",
                    "request_path": request_context["request_path"],
                    "request_method": request_context["request_method"],
                    "include_archived": request.query_params.get(
                        "include_archived", "false"
                    ),
                    "query_params": dict(request.query_params),
                },
            )

            error_serializer = StandardErrorSerializer(
                data={"error": f"Error obtaining job aging data: {str(exc)}"}
            )
            error_serializer.is_valid(raise_exception=True)

            return Response(
                error_serializer.data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
