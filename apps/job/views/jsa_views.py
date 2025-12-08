"""
API views for JSA (Job Safety Analysis) generation.

JSAs are always linked to a specific job and use job context for AI generation.
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job, SafetyDocument
from apps.job.serializers.safety_document_serializer import (
    SafetyDocumentErrorResponseSerializer,
    SafetyDocumentListSerializer,
    SafetyDocumentSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class JobJSAListView(APIView):
    """
    List JSAs for a specific job.

    GET: Returns all JSAs linked to the specified job.
    """

    @extend_schema(
        operation_id="listJobJSAs",
        description="List all JSAs for a specific job",
        responses={
            200: SafetyDocumentListSerializer(many=True),
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def get(self, request, job_id):
        """List all JSAs for a job."""
        try:
            job = get_object_or_404(Job, pk=job_id)
            jsas = SafetyDocument.objects.filter(job=job, document_type="jsa").order_by(
                "-created_at"
            )
            serializer = SafetyDocumentListSerializer(jsas, many=True)
            return Response(serializer.data)

        except Exception as exc:
            logger.exception(f"Error listing JSAs for job {job_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobJSAGenerateView(APIView):
    """
    Generate a new JSA for a specific job using AI.

    POST: Generates a new draft JSA using job context and similar historical JSAs.
    """

    @extend_schema(
        operation_id="generateJobJSA",
        description="Generate a new draft JSA for a job using AI",
        responses={
            201: SafetyDocumentSerializer,
            404: SafetyDocumentErrorResponseSerializer,
            500: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request, job_id):
        """Generate a new JSA for a job."""
        try:
            job = get_object_or_404(Job, pk=job_id)

            # Import here to avoid circular imports
            from apps.job.services.safety_document_service import (
                SafetyDocumentService,
            )

            service = SafetyDocumentService()
            jsa = service.generate_jsa(job)

            serializer = SafetyDocumentSerializer(jsa, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception(f"Error generating JSA for job {job_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
