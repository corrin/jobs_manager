"""
API views for SafetyDocument (JSA/SWP) management.

These views handle listing, retrieving, and deleting safety documents.
Document content is stored in Google Docs - editing happens there.
JSA generation (from jobs) and SWP generation (standalone) are handled
in separate view files.

Also provides:
- Content read/write endpoints for Google Docs
- AI endpoints for granular hazard/control generation
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
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


# Request/Response serializers for content and AI endpoints
class DocumentContentResponseSerializer(serializers.Serializer):
    """Response for reading document content."""

    title = serializers.CharField()
    document_type = serializers.CharField()
    description = serializers.CharField()
    site_location = serializers.CharField()
    ppe_requirements = serializers.ListField(child=serializers.CharField())
    tasks = serializers.ListField(child=serializers.DictField())
    additional_notes = serializers.CharField()
    raw_text = serializers.CharField()


class DocumentContentRequestSerializer(serializers.Serializer):
    """Request for updating document content."""

    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    site_location = serializers.CharField(required=False, allow_blank=True)
    ppe_requirements = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    tasks = serializers.ListField(child=serializers.DictField(), required=False)
    additional_notes = serializers.CharField(required=False, allow_blank=True)


class GenerateHazardsRequestSerializer(serializers.Serializer):
    """Request for generating hazards."""

    task_description = serializers.CharField()


class GenerateHazardsResponseSerializer(serializers.Serializer):
    """Response for generated hazards."""

    hazards = serializers.ListField(child=serializers.CharField())


class GenerateControlsRequestSerializer(serializers.Serializer):
    """Request for generating controls."""

    hazards = serializers.ListField(child=serializers.CharField())
    task_description = serializers.CharField(required=False, allow_blank=True)


class ControlMeasureSerializer(serializers.Serializer):
    """Serializer for a control measure."""

    measure = serializers.CharField()
    associated_hazard = serializers.CharField()


class GenerateControlsResponseSerializer(serializers.Serializer):
    """Response for generated controls."""

    controls = serializers.ListField(child=ControlMeasureSerializer())


class ImproveSectionRequestSerializer(serializers.Serializer):
    """Request for improving a section."""

    section_text = serializers.CharField()
    section_type = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)


class ImproveSectionResponseSerializer(serializers.Serializer):
    """Response for improved section."""

    improved_text = serializers.CharField()


class ImproveDocumentRequestSerializer(serializers.Serializer):
    """Request for improving an entire document."""

    raw_text = serializers.CharField()
    document_type = serializers.ChoiceField(
        choices=["jsa", "swp"], required=False, default="swp"
    )


class SafetyDocumentListView(APIView):
    """
    List all safety documents (JSAs and SWPs).

    GET: Returns a list of all safety documents with basic info.
    Query params:
        - type: Filter by document type ('jsa' or 'swp')
        - q: Search by title
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

            # Search by title
            search = request.query_params.get("q")
            if search:
                queryset = queryset.filter(title__icontains=search)

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
    Retrieve or delete a specific safety document.

    GET: Retrieve full document details including Google Docs URL
    DELETE: Delete document record (does not delete the Google Doc)
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
        operation_id="deleteSafetyDocument",
        description="Delete a safety document record (Google Doc is not deleted)",
        responses={
            204: None,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def delete(self, request, doc_id):
        """Delete a safety document."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as exc:
            logger.exception(f"Error deleting safety document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyDocumentContentView(APIView):
    """
    Read or update content of a safety document's Google Doc.

    GET: Read content from the Google Doc
    PUT: Update the Google Doc with new content
    """

    @extend_schema(
        operation_id="getSafetyDocumentContent",
        description="Read content from the safety document's Google Doc",
        responses={
            200: DocumentContentResponseSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def get(self, request, doc_id):
        """Read content from Google Doc."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if not document.google_doc_id:
                return Response(
                    {"status": "error", "message": "Document has no Google Doc"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Import here to avoid circular imports
            from apps.job.services.google_docs_service import GoogleDocsService

            service = GoogleDocsService()
            content = service.read_document(document.google_doc_id)

            return Response(
                {
                    "title": content.title,
                    "document_type": content.document_type,
                    "description": content.description,
                    "site_location": content.site_location,
                    "ppe_requirements": content.ppe_requirements,
                    "tasks": content.tasks,
                    "additional_notes": content.additional_notes,
                    "raw_text": content.raw_text,
                }
            )

        except Exception as exc:
            logger.exception(f"Error reading content for document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="updateSafetyDocumentContent",
        description="Update the safety document's Google Doc with new content",
        request=DocumentContentRequestSerializer,
        responses={
            200: SafetyDocumentSerializer,
            404: SafetyDocumentErrorResponseSerializer,
        },
    )
    def put(self, request, doc_id):
        """Update Google Doc with new content."""
        try:
            document = get_object_or_404(SafetyDocument, pk=doc_id)

            if not document.google_doc_id:
                return Response(
                    {"status": "error", "message": "Document has no Google Doc"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = DocumentContentRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.google_docs_service import GoogleDocsService

            service = GoogleDocsService()
            service.update_document(document.google_doc_id, serializer.validated_data)

            # Update document metadata if provided
            if "title" in serializer.validated_data:
                document.title = serializer.validated_data["title"]
            if "site_location" in serializer.validated_data:
                document.site_location = serializer.validated_data["site_location"]
            document.save()

            response_serializer = SafetyDocumentSerializer(
                document, context={"request": request}
            )
            return Response(response_serializer.data)

        except Exception as exc:
            logger.exception(f"Error updating content for document {doc_id}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyAIGenerateHazardsView(APIView):
    """Generate hazards for a task using AI."""

    @extend_schema(
        operation_id="generateHazards",
        description="Generate potential hazards for a task description",
        request=GenerateHazardsRequestSerializer,
        responses={
            200: GenerateHazardsResponseSerializer,
            400: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request):
        """Generate hazards for a task."""
        try:
            serializer = GenerateHazardsRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.safety_ai_service import SafetyAIService

            service = SafetyAIService()
            hazards = service.generate_hazards(
                serializer.validated_data["task_description"]
            )

            return Response({"hazards": hazards})

        except Exception as exc:
            logger.exception("Error generating hazards")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyAIGenerateControlsView(APIView):
    """Generate control measures for hazards using AI."""

    @extend_schema(
        operation_id="generateControls",
        description="Generate control measures for specified hazards",
        request=GenerateControlsRequestSerializer,
        responses={
            200: GenerateControlsResponseSerializer,
            400: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request):
        """Generate controls for hazards."""
        try:
            serializer = GenerateControlsRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.safety_ai_service import SafetyAIService

            service = SafetyAIService()
            controls = service.generate_controls(
                hazards=serializer.validated_data["hazards"],
                task_description=serializer.validated_data.get("task_description", ""),
            )

            return Response({"controls": controls})

        except Exception as exc:
            logger.exception("Error generating controls")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyAIImproveSectionView(APIView):
    """Improve a section of a safety document using AI."""

    @extend_schema(
        operation_id="improveSection",
        description="Improve a specific section of a safety document",
        request=ImproveSectionRequestSerializer,
        responses={
            200: ImproveSectionResponseSerializer,
            400: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request):
        """Improve a section."""
        try:
            serializer = ImproveSectionRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.safety_ai_service import SafetyAIService

            service = SafetyAIService()
            improved_text = service.improve_section(
                section_text=serializer.validated_data["section_text"],
                section_type=serializer.validated_data["section_type"],
                context=serializer.validated_data.get("context", ""),
            )

            return Response({"improved_text": improved_text})

        except Exception as exc:
            logger.exception("Error improving section")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SafetyAIImproveDocumentView(APIView):
    """Improve an entire safety document using AI."""

    @extend_schema(
        operation_id="improveDocument",
        description="AI improves an entire safety document",
        request=ImproveDocumentRequestSerializer,
        responses={
            200: DocumentContentRequestSerializer,
            400: SafetyDocumentErrorResponseSerializer,
        },
    )
    def post(self, request):
        """Improve entire document."""
        try:
            serializer = ImproveDocumentRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Import here to avoid circular imports
            from apps.job.services.safety_ai_service import SafetyAIService

            service = SafetyAIService()
            improved = service.improve_document(
                raw_text=serializer.validated_data["raw_text"],
                document_type=serializer.validated_data.get("document_type", "swp"),
            )

            return Response(improved)

        except Exception as exc:
            logger.exception("Error improving document")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
