"""
Safety document ViewSets (JSA/SWP/SOP).

Uses DRF ViewSets for automatic schema generation and reduced boilerplate.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job, SafetyDocument
from apps.job.permissions import IsOfficeStaff
from apps.job.serializers.safety_document_serializer import (
    SafetyDocumentListSerializer,
    SafetyDocumentSerializer,
    SWPGenerateRequestSerializer,
)


# Serializers for content endpoint (defined here to keep schema close to view)
class SafetyDocumentContentResponseSerializer(serializers.Serializer):
    """Response when reading safety document content from Google Docs."""

    title = serializers.CharField()
    document_type = serializers.CharField()
    description = serializers.CharField()
    site_location = serializers.CharField()
    ppe_requirements = serializers.ListField(child=serializers.CharField())
    tasks = serializers.ListField()
    additional_notes = serializers.CharField()
    raw_text = serializers.CharField()


class SafetyDocumentContentUpdateSerializer(serializers.Serializer):
    """Request body for updating safety document content in Google Docs."""

    title = serializers.CharField(required=False)
    site_location = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    ppe_requirements = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    tasks = serializers.ListField(required=False)
    additional_notes = serializers.CharField(required=False)


class SafetyDocumentContentView(APIView):
    """
    GET/PUT content for a safety document stored in Google Docs.

    - GET: Fetch current content from Google Docs
    - PUT: Push updated content to Google Docs
    """

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    def _get_document(self, pk):
        doc = get_object_or_404(SafetyDocument, pk=pk)
        if not doc.google_doc_id:
            return None, Response(
                {"error": "No Google Doc linked"}, status=status.HTTP_404_NOT_FOUND
            )
        return doc, None

    @extend_schema(responses=SafetyDocumentContentResponseSerializer)
    def get(self, request, pk):
        doc, error_response = self._get_document(pk)
        if error_response:
            return error_response

        from apps.job.services.google_docs_service import GoogleDocsService

        content = GoogleDocsService().read_document(doc.google_doc_id)
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

    @extend_schema(
        request=SafetyDocumentContentUpdateSerializer,
        responses=SafetyDocumentSerializer,
    )
    def put(self, request, pk):
        doc, error_response = self._get_document(pk)
        if error_response:
            return error_response

        from apps.job.services.google_docs_service import GoogleDocsService

        GoogleDocsService().update_document(doc.google_doc_id, request.data)
        doc.title = request.data.get("title", doc.title)
        doc.site_location = request.data.get("site_location", doc.site_location)
        doc.save()
        return Response(SafetyDocumentSerializer(doc).data)


class SafetyDocumentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for SafetyDocument CRUD operations.

    Endpoints:
    - GET    /rest/safety-documents/              - list all documents
    - GET    /rest/safety-documents/<id>/         - retrieve document
    - DELETE /rest/safety-documents/<id>/         - delete document

    Note: Content endpoints (GET/PUT) are handled by SafetyDocumentContentView.
    """

    queryset = SafetyDocument.objects.all()
    serializer_class = SafetyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    def get_serializer_class(self):
        if self.action == "list":
            return SafetyDocumentListSerializer
        return SafetyDocumentSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter by document type (jsa/swp/sop)",
                required=False,
            ),
            OpenApiParameter(name="q", description="Search by title", required=False),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = SafetyDocument.objects.all()
        if doc_type := self.request.query_params.get("type"):
            qs = qs.filter(document_type=doc_type)
        if query := self.request.query_params.get("q"):
            qs = qs.filter(title__icontains=query)
        return qs


class JSAListView(APIView):
    """List all JSAs for a job."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(responses=SafetyDocumentListSerializer(many=True))
    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        jsas = SafetyDocument.objects.filter(job=job, document_type="jsa")
        return Response(SafetyDocumentListSerializer(jsas, many=True).data)


class JSAGenerateView(APIView):
    """Generate a new JSA for a job."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(request=None, responses=SafetyDocumentSerializer)
    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        from apps.job.services.safety_document_service import SafetyDocumentService

        jsa = SafetyDocumentService().generate_jsa(job)
        return Response(
            SafetyDocumentSerializer(jsa).data, status=status.HTTP_201_CREATED
        )


class SWPListView(APIView):
    """List all Safe Work Procedures."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(responses=SafetyDocumentListSerializer(many=True))
    def get(self, request):
        swps = SafetyDocument.objects.filter(document_type="swp")
        return Response(SafetyDocumentListSerializer(swps, many=True).data)


class SWPGenerateView(APIView):
    """Generate a new Safe Work Procedure."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=SWPGenerateRequestSerializer, responses=SafetyDocumentSerializer
    )
    def post(self, request):
        ser = SWPGenerateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.job.services.safety_document_service import SafetyDocumentService

        swp = SafetyDocumentService().generate_swp(**ser.validated_data)
        return Response(
            SafetyDocumentSerializer(swp).data, status=status.HTTP_201_CREATED
        )


class SOPListView(APIView):
    """List all Standard Operating Procedures."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(responses=SafetyDocumentListSerializer(many=True))
    def get(self, request):
        sops = SafetyDocument.objects.filter(document_type="sop")
        return Response(SafetyDocumentListSerializer(sops, many=True).data)


# Request serializer for SOP generation
class SOPGenerateRequestSerializer(serializers.Serializer):
    """Request body for generating a new SOP."""

    title = serializers.CharField()
    description = serializers.CharField(required=False, default="")
    document_number = serializers.CharField(required=False, default="")


class SOPGenerateView(APIView):
    """Generate a new Standard Operating Procedure."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=SOPGenerateRequestSerializer, responses=SafetyDocumentSerializer
    )
    def post(self, request):
        ser = SOPGenerateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.job.services.safety_document_service import SafetyDocumentService

        sop = SafetyDocumentService().generate_sop(**ser.validated_data)
        return Response(
            SafetyDocumentSerializer(sop).data, status=status.HTTP_201_CREATED
        )


# Request/Response serializers for AI endpoints
class GenerateHazardsRequestSerializer(serializers.Serializer):
    task_description = serializers.CharField()


class GenerateHazardsResponseSerializer(serializers.Serializer):
    hazards = serializers.ListField(child=serializers.CharField())


class GenerateControlsRequestSerializer(serializers.Serializer):
    hazards = serializers.ListField(child=serializers.CharField())
    task_description = serializers.CharField(required=False, default="")


class GenerateControlsResponseSerializer(serializers.Serializer):
    controls = serializers.ListField(child=serializers.CharField())


class ImproveSectionRequestSerializer(serializers.Serializer):
    section_text = serializers.CharField()
    section_type = serializers.CharField()
    context = serializers.CharField(required=False, default="")


class ImproveSectionResponseSerializer(serializers.Serializer):
    improved_text = serializers.CharField()


class ImproveDocumentRequestSerializer(serializers.Serializer):
    raw_text = serializers.CharField()
    document_type = serializers.CharField(default="swp")


class ImproveDocumentResponseSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    site_location = serializers.CharField()
    ppe_requirements = serializers.ListField(child=serializers.CharField())
    tasks = serializers.ListField()
    additional_notes = serializers.CharField()


class AIGenerateHazardsView(APIView):
    """Generate hazards for a task description using AI."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=GenerateHazardsRequestSerializer,
        responses=GenerateHazardsResponseSerializer,
    )
    def post(self, request):
        from apps.job.services.safety_ai_service import SafetyAIService

        hazards = SafetyAIService().generate_hazards(
            request.data.get("task_description", "")
        )
        return Response({"hazards": hazards})


class AIGenerateControlsView(APIView):
    """Generate controls for hazards using AI."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=GenerateControlsRequestSerializer,
        responses=GenerateControlsResponseSerializer,
    )
    def post(self, request):
        from apps.job.services.safety_ai_service import SafetyAIService

        controls = SafetyAIService().generate_controls(
            hazards=request.data.get("hazards", []),
            task_description=request.data.get("task_description", ""),
        )
        return Response({"controls": controls})


class AIImproveSectionView(APIView):
    """Improve a section of text using AI."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=ImproveSectionRequestSerializer,
        responses=ImproveSectionResponseSerializer,
    )
    def post(self, request):
        from apps.job.services.safety_ai_service import SafetyAIService

        text = SafetyAIService().improve_section(
            section_text=request.data.get("section_text", ""),
            section_type=request.data.get("section_type", ""),
            context=request.data.get("context", ""),
        )
        return Response({"improved_text": text})


class AIImproveDocumentView(APIView):
    """Improve an entire document using AI."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=ImproveDocumentRequestSerializer,
        responses=ImproveDocumentResponseSerializer,
    )
    def post(self, request):
        from apps.job.services.safety_ai_service import SafetyAIService

        improved = SafetyAIService().improve_document(
            raw_text=request.data.get("raw_text", ""),
            document_type=request.data.get("document_type", "swp"),
        )
        return Response(improved)
