"""
Process document ViewSets (JSA/SWP/SOP).

Uses DRF ViewSets for automatic schema generation and reduced boilerplate.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job, ProcessDocument, ProcessDocumentEntry
from apps.job.permissions import IsOfficeStaff
from apps.job.serializers.process_document_serializer import (
    ProcessDocumentCreateSerializer,
    ProcessDocumentEntrySerializer,
    ProcessDocumentListSerializer,
    ProcessDocumentSerializer,
    ProcessDocumentUpdateSerializer,
    SWPGenerateRequestSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error


# Serializers for content endpoint (defined here to keep schema close to view)
class ProcessDocumentContentResponseSerializer(serializers.Serializer):
    """Response when reading process document content from Google Docs."""

    title = serializers.CharField()
    document_type = serializers.CharField()
    description = serializers.CharField()
    site_location = serializers.CharField()
    ppe_requirements = serializers.ListField(child=serializers.CharField())
    tasks = serializers.ListField()
    additional_notes = serializers.CharField()
    raw_text = serializers.CharField()


class ProcessDocumentContentUpdateSerializer(serializers.Serializer):
    """Request body for updating process document content in Google Docs."""

    title = serializers.CharField(required=False)
    site_location = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    ppe_requirements = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    tasks = serializers.ListField(required=False)
    additional_notes = serializers.CharField(required=False)


class ProcessDocumentContentView(APIView):
    """
    GET/PUT content for a process document stored in Google Docs.

    - GET: Fetch current content from Google Docs
    - PUT: Push updated content to Google Docs
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOfficeStaff()]

    def _get_document(self, pk):
        doc = get_object_or_404(ProcessDocument, pk=pk)
        if not doc.google_doc_id:
            return None, Response(
                {"error": "No Google Doc linked"}, status=status.HTTP_404_NOT_FOUND
            )
        return doc, None

    @extend_schema(responses=ProcessDocumentContentResponseSerializer)
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
        request=ProcessDocumentContentUpdateSerializer,
        responses=ProcessDocumentSerializer,
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
        return Response(ProcessDocumentSerializer(doc).data)


class ProcessDocumentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for ProcessDocument CRUD operations.

    Endpoints:
    - GET    /rest/process-documents/              - list all documents
    - POST   /rest/process-documents/              - create document
    - GET    /rest/process-documents/<id>/         - retrieve document
    - PUT    /rest/process-documents/<id>/         - update document
    - PATCH  /rest/process-documents/<id>/         - partial update document
    - DELETE /rest/process-documents/<id>/         - delete document

    Note: Content endpoints (GET/PUT) are handled by ProcessDocumentContentView.
    """

    queryset = ProcessDocument.objects.all()
    serializer_class = ProcessDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOfficeStaff()]

    def get_serializer_class(self):
        if self.action == "list":
            return ProcessDocumentListSerializer
        if self.action == "create":
            return ProcessDocumentCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ProcessDocumentUpdateSerializer
        return ProcessDocumentSerializer

    @extend_schema(
        request=ProcessDocumentCreateSerializer,
        responses={201: ProcessDocumentSerializer},
    )
    def create(self, request, *args, **kwargs):
        ser = ProcessDocumentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.job.services.process_document_service import ProcessDocumentService

        doc = ProcessDocumentService().create_blank_document(**ser.validated_data)
        return Response(
            ProcessDocumentSerializer(doc).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request=ProcessDocumentUpdateSerializer,
        responses=ProcessDocumentSerializer,
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        ser = ProcessDocumentUpdateSerializer(
            instance, data=request.data, partial=partial
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ProcessDocumentSerializer(instance).data)

    @extend_schema(
        request=ProcessDocumentUpdateSerializer,
        responses=ProcessDocumentSerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter by document type (procedure/form/register/reference)",
                required=False,
            ),
            OpenApiParameter(name="q", description="Search by title", required=False),
            OpenApiParameter(
                name="tags",
                description="Comma-separated tags; ALL must match",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                description="Filter by status (draft/active/completed/archived)",
                required=False,
            ),
            OpenApiParameter(
                name="is_template",
                description="Filter by template flag (true/false)",
                required=False,
            ),
            OpenApiParameter(
                name="parent_template_id",
                description="Filter by parent template UUID",
                required=False,
                type=str,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = ProcessDocument.objects.all()
        if doc_type := self.request.query_params.get("type"):
            qs = qs.filter(document_type=doc_type)
        if query := self.request.query_params.get("q"):
            qs = qs.filter(title__icontains=query)
        if tags_param := self.request.query_params.get("tags"):
            for tag in tags_param.split(","):
                tag = tag.strip()
                if tag:
                    qs = qs.filter(tags__contains=[tag])
        if status_param := self.request.query_params.get("status"):
            qs = qs.filter(status=status_param)
        if is_template_param := self.request.query_params.get("is_template"):
            qs = qs.filter(is_template=is_template_param.lower() == "true")
        if parent_template_id := self.request.query_params.get("parent_template_id"):
            qs = qs.filter(parent_template_id=parent_template_id)
        return qs


class ProcessDocumentEntryViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD endpoints for ProcessDocumentEntry, nested under a document.

    Endpoints:
    - GET    /rest/process-documents/<id>/entries/              - list entries
    - POST   /rest/process-documents/<id>/entries/              - create entry
    - PUT    /rest/process-documents/<id>/entries/<entry_id>/   - update entry
    - DELETE /rest/process-documents/<id>/entries/<entry_id>/   - delete entry
    """

    serializer_class = ProcessDocumentEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_document(self):
        return get_object_or_404(ProcessDocument, pk=self.kwargs["document_pk"])

    def get_queryset(self):
        return ProcessDocumentEntry.objects.filter(
            document_id=self.kwargs["document_pk"]
        ).order_by("-entry_date", "-created_at")

    @extend_schema(responses=ProcessDocumentEntrySerializer(many=True))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request=ProcessDocumentEntrySerializer,
        responses={201: ProcessDocumentEntrySerializer},
    )
    def create(self, request, *args, **kwargs):
        document = self.get_document()
        ser = ProcessDocumentEntrySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(document=document, entered_by=request.user)
        return Response(
            ProcessDocumentEntrySerializer(ser.instance).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=ProcessDocumentEntrySerializer,
        responses=ProcessDocumentEntrySerializer,
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request=ProcessDocumentEntrySerializer,
        responses=ProcessDocumentEntrySerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class JSAListView(APIView):
    """List all JSAs for a job."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=ProcessDocumentListSerializer(many=True))
    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        jsas = ProcessDocument.objects.filter(job=job, tags__contains=["jsa"])
        return Response(ProcessDocumentListSerializer(jsas, many=True).data)


class JSAGenerateView(APIView):
    """Generate a new JSA for a job."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(request=None, responses=ProcessDocumentSerializer)
    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        from apps.job.services.process_document_service import ProcessDocumentService

        jsa = ProcessDocumentService().generate_jsa(job)
        return Response(
            ProcessDocumentSerializer(jsa).data, status=status.HTTP_201_CREATED
        )


class SWPListView(APIView):
    """List all Safe Work Procedures."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=ProcessDocumentListSerializer(many=True))
    def get(self, request):
        swps = ProcessDocument.objects.filter(tags__contains=["swp"])
        return Response(ProcessDocumentListSerializer(swps, many=True).data)


class SWPGenerateView(APIView):
    """Generate a new Safe Work Procedure."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=SWPGenerateRequestSerializer, responses=ProcessDocumentSerializer
    )
    def post(self, request):
        ser = SWPGenerateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.job.services.process_document_service import ProcessDocumentService

        swp = ProcessDocumentService().generate_swp(**ser.validated_data)
        return Response(
            ProcessDocumentSerializer(swp).data, status=status.HTTP_201_CREATED
        )


class SOPListView(APIView):
    """List all Standard Operating Procedures."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=ProcessDocumentListSerializer(many=True))
    def get(self, request):
        sops = ProcessDocument.objects.filter(tags__contains=["sop"])
        return Response(ProcessDocumentListSerializer(sops, many=True).data)


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
        request=SOPGenerateRequestSerializer, responses=ProcessDocumentSerializer
    )
    def post(self, request):
        ser = SOPGenerateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.job.services.process_document_service import ProcessDocumentService

        sop = ProcessDocumentService().generate_sop(**ser.validated_data)
        return Response(
            ProcessDocumentSerializer(sop).data, status=status.HTTP_201_CREATED
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

    permission_classes = [permissions.IsAuthenticated]

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

    permission_classes = [permissions.IsAuthenticated]

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

    permission_classes = [permissions.IsAuthenticated]

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

    permission_classes = [permissions.IsAuthenticated]

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


class ProcessDocumentFillView(APIView):
    """Create a new record from a template."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=inline_serializer(
            "FillRequest",
            fields={
                "job_id": serializers.UUIDField(required=False, allow_null=True),
            },
        ),
        responses=ProcessDocumentSerializer,
    )
    def post(self, request, pk):
        try:
            from apps.job.services.process_document_service import (
                ProcessDocumentService,
            )

            record = ProcessDocumentService().fill_template(
                template_id=pk,
                job_id=request.data.get("job_id"),
            )
            return Response(
                ProcessDocumentSerializer(record).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            persist_app_error(exc)
            raise


class ProcessDocumentCompleteView(APIView):
    """Mark a document as completed (read-only)."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(request=None, responses=ProcessDocumentSerializer)
    def post(self, request, pk):
        try:
            from apps.job.services.process_document_service import (
                ProcessDocumentService,
            )

            doc = ProcessDocumentService().complete_document(pk)
            return Response(ProcessDocumentSerializer(doc).data)
        except Exception as exc:
            persist_app_error(exc)
            raise
