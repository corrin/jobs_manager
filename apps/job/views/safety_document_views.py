"""
API views for SafetyDocument (JSA/SWP) management.

These views handle CRUD operations for safety documents.
JSA generation (from jobs) and SWP generation (standalone) are handled
in separate view files.
"""

import logging
import os

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import SafetyDocument
from apps.job.serializers.safety_document_serializer import (
    SafetyDocumentErrorResponseSerializer,
    SafetyDocumentListSerializer,
    SafetyDocumentSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class SafetyDocumentListView(APIView):
    """
    List all safety documents (JSAs and SWPs).

    GET: Returns a list of all safety documents with basic info.
    Query params:
        - type: Filter by document type ('jsa' or 'swp')
        - status: Filter by status ('draft' or 'final')
    """

    @extend_schema(
        operation_id="listSafetyDocuments",
        description="List all safety documents with optional filtering",
        responses={
            200: SafetyDocumentListSerializer(many=True),
        },
    )
    def get(self, request):
        """List all safety documents."""
        try:
            queryset = SafetyDocument.objects.all()

            # Apply filters
            doc_type = request.query_params.get("type")
            if doc_type in ("jsa", "swp"):
                queryset = queryset.filter(document_type=doc_type)

            doc_status = request.query_params.get("status")
            if doc_status in ("draft", "final"):
                queryset = queryset.filter(status=doc_status)

            # Search by title/description
            search = request.query_params.get("q")
            if search:
                queryset = queryset.filter(title__icontains=search) | queryset.filter(
                    description__icontains=search
                )

            serializer = SafetyDocumentListSerializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as exc:
            logger.exception("Error listing safety documents")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyDocumentDetailView(APIView):
    """
    Retrieve, update, or delete a specific safety document.

    GET: Retrieve full document details
    PUT: Full update of document (draft only)
    PATCH: Partial update of document (draft only)
    DELETE: Delete document (draft only)
    """

    @extend_schema(
        operation_id="getSafetyDocument",
        description="Retrieve a specific safety document",
        responses={
            200: SafetyDocumentSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def get(self, request, doc_id):
        """Retrieve a specific safety document."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)
            serializer = SafetyDocumentSerializer(
                document, context={"request": request}
            )
            return Response(serializer.data)

        except Exception as exc:
            logger.exception(f"Error retrieving safety document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="updateSafetyDocument",
        description="Full update of a draft safety document",
        request=SafetyDocumentSerializer,
        responses={
            200: SafetyDocumentSerializer,
            400: SafetyDocumentErrorResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def put(self, request, doc_id):
        """Full update of a safety document."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if document.status == "final":
                return Response(
                    {
                        "status": "error",
                        "message": "Cannot edit a finalized document",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = SafetyDocumentSerializer(
                document, data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(
                {"status": "error", "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            logger.exception(f"Error updating safety document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="partialUpdateSafetyDocument",
        description="Partial update of a draft safety document",
        request=SafetyDocumentSerializer,
        responses={
            200: SafetyDocumentSerializer,
            400: SafetyDocumentErrorResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def patch(self, request, doc_id):
        """Partial update of a safety document."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if document.status == "final":
                return Response(
                    {
                        "status": "error",
                        "message": "Cannot edit a finalized document",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = SafetyDocumentSerializer(
                document, data=request.data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(
                {"status": "error", "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            logger.exception(f"Error updating safety document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="deleteSafetyDocument",
        description="Delete a draft safety document",
        responses={
            204: None,
            400: SafetyDocumentErrorResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def delete(self, request, doc_id):
        """Delete a safety document."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if document.status == "final":
                return Response(
                    {
                        "status": "error",
                        "message": "Cannot delete a finalized document",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as exc:
            logger.exception(f"Error deleting safety document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyDocumentPDFView(APIView):
    """
    Download the generated PDF for a finalized safety document.

    GET: Returns the PDF file for download.
    """

    @extend_schema(
        operation_id="getSafetyDocumentPDF",
        description="Download the PDF for a finalized safety document",
        responses={
            200: {"type": "string", "format": "binary"},
            400: SafetyDocumentErrorResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def get(self, request, doc_id):
        """Download PDF for a safety document."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if not document.pdf_file_path:
                return Response(
                    {
                        "status": "error",
                        "message": "No PDF available. Document must be finalized first.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Construct full path
            full_path = os.path.join(
                settings.DROPBOX_WORKFLOW_FOLDER, document.pdf_file_path
            )

            if not os.path.exists(full_path):
                return Response(
                    {"status": "error", "message": "PDF file not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Return file for download
            filename = os.path.basename(document.pdf_file_path)
            response = FileResponse(
                open(full_path, "rb"),
                as_attachment=False,
                filename=filename,
                content_type="application/pdf",
            )
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response

        except Exception as exc:
            logger.exception(f"Error downloading PDF for safety document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyDocumentFinalizeView(APIView):
    """
    Finalize a draft safety document by generating PDF.

    POST: Generates PDF, saves to Dropbox, updates status to 'final'.
    """

    @extend_schema(
        operation_id="finalizeSafetyDocument",
        description="Finalize a draft safety document by generating PDF",
        responses={
            200: SafetyDocumentSerializer,
            400: SafetyDocumentErrorResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request, doc_id):
        """Finalize a safety document."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if document.status == "final":
                return Response(
                    {
                        "status": "error",
                        "message": "Document is already finalized",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.safety_document_service import (
                SafetyDocumentService,
            )

            service = SafetyDocumentService()
            pdf_buffer, file_path = service.finalize_document(document)

            # Refresh document from database
            document.refresh_from_db()

            serializer = SafetyDocumentSerializer(
                document, context={"request": request}
            )
            return Response(serializer.data)

        except ValueError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            logger.exception(f"Error finalizing safety document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyDocumentTaskHazardsView(APIView):
    """
    Generate hazards for a specific task using AI.

    POST: Generates hazards for the specified task.
    """

    @extend_schema(
        operation_id="generateTaskHazards",
        description="Generate hazards for a specific task using AI",
        responses={
            200: {"type": "object", "properties": {"hazards": {"type": "array"}}},
            400: SafetyDocumentErrorResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request, doc_id, task_num):
        """Generate hazards for a task."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if document.status == "final":
                return Response(
                    {
                        "status": "error",
                        "message": "Cannot modify finalized document",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # task_num is 1-based, convert to 0-based index
            task_index = task_num - 1

            if task_index < 0 or task_index >= len(document.tasks):
                return Response(
                    {"status": "error", "message": f"Invalid task number: {task_num}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.safety_document_service import (
                SafetyDocumentService,
            )

            service = SafetyDocumentService()
            hazards = service.update_task_hazards(document, task_index)

            return Response({"hazards": hazards})

        except Exception as exc:
            logger.exception(f"Error generating hazards for task {task_num}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyDocumentTaskControlsView(APIView):
    """
    Generate controls for a specific task's hazards using AI.

    POST: Generates control measures for the specified task's hazards.
    """

    @extend_schema(
        operation_id="generateTaskControls",
        description="Generate control measures for a task's hazards using AI",
        responses={
            200: {"type": "object", "properties": {"controls": {"type": "array"}}},
            400: SafetyDocumentErrorResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request, doc_id, task_num):
        """Generate controls for a task."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if document.status == "final":
                return Response(
                    {
                        "status": "error",
                        "message": "Cannot modify finalized document",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # task_num is 1-based, convert to 0-based index
            task_index = task_num - 1

            if task_index < 0 or task_index >= len(document.tasks):
                return Response(
                    {"status": "error", "message": f"Invalid task number: {task_num}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.safety_document_service import (
                SafetyDocumentService,
            )

            service = SafetyDocumentService()
            controls = service.update_task_controls(document, task_index)

            return Response({"controls": controls})

        except ValueError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            logger.exception(f"Error generating controls for task {task_num}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
