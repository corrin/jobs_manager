"""
ViewSets for Safety Documents (JSA/SWP/SOP).

Provides:
- SafetyDocumentViewSet: CRUD for all safety documents
- JSAViewSet: JSA operations (nested under jobs)
- SWPViewSet: SWP operations (standalone)
- SOPViewSet: SOP operations (standalone)
- SafetyAIViewSet: AI-powered content generation
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.job.models import Job, SafetyDocument
from apps.job.serializers.safety_document_serializer import (
    SafetyDocumentErrorResponseSerializer,
    SafetyDocumentListSerializer,
    SafetyDocumentSerializer,
    SWPGenerateRequestSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Serializers
# ============================================================================


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
        choices=["jsa", "swp", "sop"], required=False, default="swp"
    )


class SOPGenerateRequestSerializer(serializers.Serializer):
    """Request serializer for generating a new SOP."""

    document_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Document number (e.g., '307' for section 3, doc 7)",
    )
    title = serializers.CharField(
        max_length=255,
        help_text="Name of the procedure",
    )
    description = serializers.CharField(
        help_text="Scope and description of the procedure",
    )


# ============================================================================
# SafetyDocumentViewSet - Base CRUD
# ============================================================================


@extend_schema_view(
    list=extend_schema(
        operation_id="listSafetyDocuments",
        description="List all safety documents with optional filtering by type",
    ),
    retrieve=extend_schema(
        operation_id="getSafetyDocument",
        description="Retrieve a specific safety document",
    ),
    destroy=extend_schema(
        operation_id="deleteSafetyDocument",
        description="Delete a safety document (Google Doc is not deleted)",
    ),
)
class SafetyDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SafetyDocument CRUD operations.

    Documents are created via generate actions on JSA/SWP/SOP viewsets.
    Content is stored in Google Docs.
    """

    queryset = SafetyDocument.objects.all()
    serializer_class = SafetyDocumentSerializer
    lookup_field = "pk"

    # Disable create/update - documents created via generate actions
    http_method_names = ["get", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return SafetyDocumentListSerializer
        return SafetyDocumentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by document type if requested
        doc_type = self.request.query_params.get("type")
        if doc_type in ("jsa", "swp", "sop"):
            qs = qs.filter(document_type=doc_type)
        # Search by title
        search = self.request.query_params.get("q")
        if search:
            qs = qs.filter(title__icontains=search)
        return qs

    @extend_schema(
        operation_id="getSafetyDocumentContent",
        description="Read content from the safety document's Google Doc",
        responses={200: DocumentContentResponseSerializer},
    )
    @action(detail=True, methods=["get"])
    def content(self, request, pk=None):
        """Read content from Google Doc."""
        document = self.get_object()

        if not document.google_doc_id:
            return Response(
                {"status": "error", "message": "Document has no Google Doc"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
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
            logger.exception(f"Error reading content for document {pk}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="updateSafetyDocumentContent",
        description="Update the safety document's Google Doc with new content",
        request=DocumentContentRequestSerializer,
        responses={200: SafetyDocumentSerializer},
    )
    @action(detail=True, methods=["put"], url_path="content", url_name="content-update")
    def update_content(self, request, pk=None):
        """Update Google Doc with new content."""
        document = self.get_object()

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

        try:
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
            logger.exception(f"Error updating content for document {pk}")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# JSAViewSet - Job-linked operations
# ============================================================================


class JSAViewSet(viewsets.ViewSet):
    """
    ViewSet for JSA (Job Safety Analysis) operations.

    JSAs are always linked to a specific job.
    """

    serializer_class = SafetyDocumentSerializer

    @extend_schema(
        operation_id="listJobJSAs",
        description="List all JSAs for a specific job",
        responses={200: SafetyDocumentListSerializer(many=True)},
    )
    def list(self, request, job_id=None):
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

    @extend_schema(
        operation_id="generateJobJSA",
        description="Generate a new JSA for a job using AI",
        responses={
            201: SafetyDocumentSerializer,
            404: SafetyDocumentErrorResponseSerializer,
            500: SafetyDocumentErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["post"])
    def generate(self, request, job_id=None):
        """Generate a new JSA for a job."""
        try:
            job = get_object_or_404(Job, pk=job_id)

            from apps.job.services.safety_document_service import SafetyDocumentService

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


# ============================================================================
# SWPViewSet - Standalone Safe Work Procedures
# ============================================================================


class SWPViewSet(viewsets.ViewSet):
    """
    ViewSet for SWP (Safe Work Procedure) operations.

    SWPs are standalone safety procedures not linked to any job.
    """

    serializer_class = SafetyDocumentSerializer

    @extend_schema(
        operation_id="listSWPs",
        description="List all Safe Work Procedures",
        responses={200: SafetyDocumentListSerializer(many=True)},
    )
    def list(self, request):
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

    @extend_schema(
        operation_id="generateSWP",
        description="Generate a new SWP using AI",
        request=SWPGenerateRequestSerializer,
        responses={
            201: SafetyDocumentSerializer,
            400: SafetyDocumentErrorResponseSerializer,
            500: SafetyDocumentErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["post"])
    def generate(self, request):
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
            document_number = serializer.validated_data.get("document_number", "")

            from apps.job.services.safety_document_service import SafetyDocumentService

            service = SafetyDocumentService()
            swp = service.generate_swp(
                title=title,
                description=description,
                site_location=site_location,
                document_number=document_number,
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


# ============================================================================
# SOPViewSet - Standalone Standard Operating Procedures
# ============================================================================


class SOPViewSet(viewsets.ViewSet):
    """
    ViewSet for SOP (Standard Operating Procedure) operations.

    SOPs are general procedures (not safety-specific), like "How to enter an invoice".
    """

    serializer_class = SafetyDocumentSerializer

    @extend_schema(
        operation_id="listSOPs",
        description="List all Standard Operating Procedures",
        responses={200: SafetyDocumentListSerializer(many=True)},
    )
    def list(self, request):
        """List all SOPs."""
        try:
            sops = SafetyDocument.objects.filter(document_type="sop").order_by(
                "-created_at"
            )
            serializer = SafetyDocumentListSerializer(sops, many=True)
            return Response(serializer.data)

        except Exception as exc:
            logger.exception("Error listing SOPs")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="generateSOP",
        description="Generate a new SOP using AI",
        request=SOPGenerateRequestSerializer,
        responses={
            201: SafetyDocumentSerializer,
            400: SafetyDocumentErrorResponseSerializer,
            500: SafetyDocumentErrorResponseSerializer,
        },
    )
    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Generate a new SOP."""
        try:
            serializer = SOPGenerateRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            title = serializer.validated_data["title"]
            description = serializer.validated_data["description"]
            document_number = serializer.validated_data.get("document_number", "")

            from apps.job.services.safety_document_service import SafetyDocumentService

            service = SafetyDocumentService()
            sop = service.generate_sop(
                title=title,
                description=description,
                document_number=document_number,
            )

            response_serializer = SafetyDocumentSerializer(
                sop, context={"request": request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Error generating SOP")
            persist_app_error(exc)
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# SafetyAIViewSet - AI-powered operations
# ============================================================================


class SafetyAIViewSet(viewsets.ViewSet):
    """
    ViewSet for AI-powered safety document operations.

    Provides granular AI endpoints for generating hazards, controls,
    and improving document sections.
    """

    serializer_class = GenerateHazardsResponseSerializer  # Default for schema

    @extend_schema(
        operation_id="generateHazards",
        description="Generate potential hazards for a task description",
        request=GenerateHazardsRequestSerializer,
        responses={200: GenerateHazardsResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="generate-hazards")
    def generate_hazards(self, request):
        """Generate hazards for a task."""
        try:
            serializer = GenerateHazardsRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

    @extend_schema(
        operation_id="generateControls",
        description="Generate control measures for specified hazards",
        request=GenerateControlsRequestSerializer,
        responses={200: GenerateControlsResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="generate-controls")
    def generate_controls(self, request):
        """Generate controls for hazards."""
        try:
            serializer = GenerateControlsRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

    @extend_schema(
        operation_id="improveSection",
        description="Improve a specific section of a safety document",
        request=ImproveSectionRequestSerializer,
        responses={200: ImproveSectionResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="improve-section")
    def improve_section(self, request):
        """Improve a section."""
        try:
            serializer = ImproveSectionRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

    @extend_schema(
        operation_id="improveDocument",
        description="AI improves an entire safety document",
        request=ImproveDocumentRequestSerializer,
        responses={200: DocumentContentRequestSerializer},
    )
    @action(detail=False, methods=["post"], url_path="improve-document")
    def improve_document(self, request):
        """Improve entire document."""
        try:
            serializer = ImproveDocumentRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"status": "error", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
