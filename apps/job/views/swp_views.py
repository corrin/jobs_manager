"""
API views for SWP (Safe Work Procedure) generation.

SWPs are standalone documents not linked to any job.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import SafetyDocument
from apps.job.serializers.safety_document_serializer import (
    SafetyDocumentErrorResponseSerializer,
    SafetyDocumentListSerializer,
    SafetyDocumentSerializer,
    SWPGenerateRequestSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class SWPListView(APIView):
    """
    List all SWPs (Safe Work Procedures).

    GET: Returns all SWPs (not linked to any job).
    """

    @extend_schema(
        operation_id="listSWPs",
        description="List all Safe Work Procedures",
        responses={
            200: SafetyDocumentListSerializer(many=True),
        },
    )
    def get(self, request):
        """List all SWPs."""
        try:
            swps = SafetyDocument.objects.filter(document_type="swp").order_by(
                "-created_at"
            )
            serializer = SafetyDocumentListSerializer(swps, many=True)
            return Response(serializer.data)

        except Exception as exc:
            logger.exception("Error listing SWPs")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SWPGenerateView(APIView):
    """
    Generate a new SWP (Safe Work Procedure) using AI.

    POST: Generates a new draft SWP using provided title/description.
    """

    @extend_schema(
        operation_id="generateSWP",
        description="Generate a new draft SWP using AI",
        request=SWPGenerateRequestSerializer,
        responses={
            201: SafetyDocumentSerializer,
            400: SafetyDocumentErrorResponseSerializer,
            500: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request):
        """Generate a new SWP."""
        try:
            serializer = SWPGenerateRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            title = serializer.validated_data["title"]
            description = serializer.validated_data["description"]
            site_location = serializer.validated_data.get("site_location", "")

            # Import here to avoid circular imports
            from apps.job.services.safety_document_service import (
                SafetyDocumentService,
            )

            service = SafetyDocumentService()
            swp = service.generate_swp(
                title=title,
                description=description,
                site_location=site_location,
            )

            response_serializer = SafetyDocumentSerializer(
                swp, context={"request": request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Error generating SWP")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
