"""
Process document ViewSets and views.

Organized by interaction model:
- ProcedureViewSet: Written documents people read (Google Doc-backed)
- FormViewSet: Fillable templates with entries (form_schema, no Google Docs)
- JSA/AI views: Unchanged
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job, ProcessDocument, ProcessDocumentEntry
from apps.job.permissions import IsOfficeStaff
from apps.job.serializers.process_document_serializer import (
    FormCreateSerializer,
    FormDetailSerializer,
    FormListSerializer,
    FormUpdateSerializer,
    ProcedureCreateSerializer,
    ProcedureDetailSerializer,
    ProcedureListSerializer,
    ProcedureUpdateSerializer,
    ProcessDocumentEntrySerializer,
    SWPGenerateRequestSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error

# ─── Category → queryset filter mappings ──────────────────────────────────────

PROCEDURE_CATEGORIES = {
    "safety": {"document_type": "procedure", "tags": ["safety"]},
    "training": {"document_type": "procedure", "tags": ["training"]},
    "reference": {"document_type": "reference", "tags": []},
}

FORM_CATEGORIES = {
    "safety": {
        "document_type": "form",
        "tags_any": ["safety", "inspection", "hazard-id", "maintenance"],
    },
    "training": {"document_type": "form", "tags": ["training"]},
    "incident": {"document_type": "form", "tags": ["incident"]},
    "meeting": {
        "document_type": "form",
        "tags_any": ["meeting", "administration"],
    },
    "register": {"document_type": "register", "tags": []},
}


def _apply_category_filter(qs, category_map, category):
    """Apply category-specific filters to a queryset."""
    config = category_map.get(category)
    if config is None:
        return None  # signals invalid category

    qs = qs.select_related("job", "parent_template").filter(
        document_type=config["document_type"]
    )

    if tags := config.get("tags"):
        for tag in tags:
            qs = qs.filter(tags__contains=[tag])
    elif tags_any := config.get("tags_any"):
        tag_q = Q()
        for tag in tags_any:
            tag_q |= Q(tags__contains=[tag])
        qs = qs.filter(tag_q)

    return qs


def _apply_common_filters(qs, request):
    """Apply shared query-param filters (q, tags, status, is_template, parent_template_id)."""
    if query := request.query_params.get("q"):
        qs = qs.filter(title__icontains=query)
    if tags_param := request.query_params.get("tags"):
        for tag in tags_param.split(","):
            tag = tag.strip()
            if tag:
                qs = qs.filter(tags__contains=[tag])
    if status_param := request.query_params.get("status"):
        qs = qs.filter(status=status_param)
    if is_template_param := request.query_params.get("is_template"):
        qs = qs.filter(is_template=is_template_param.lower() == "true")
    if parent_template_id := request.query_params.get("parent_template_id"):
        qs = qs.filter(parent_template_id=parent_template_id)
    return qs


# ─── Procedure ViewSet ────────────────────────────────────────────────────────


class ProcedureViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD for procedure documents (Google Doc-backed written documents).

    Category is taken from the URL kwarg, e.g. /rest/procedures/safety/.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOfficeStaff()]

    def get_serializer_class(self):
        if self.action == "list":
            return ProcedureListSerializer
        if self.action == "create":
            return ProcedureCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ProcedureUpdateSerializer
        return ProcedureDetailSerializer

    def _get_category(self):
        return self.kwargs.get("category", "")

    def get_queryset(self):
        category = self._get_category()
        qs = _apply_category_filter(
            ProcessDocument.objects.all(), PROCEDURE_CATEGORIES, category
        )
        if qs is None:
            return ProcessDocument.objects.none()
        return _apply_common_filters(qs, self.request)

    @extend_schema(
        parameters=[
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
        ]
    )
    def list(self, request, *args, **kwargs):
        category = self._get_category()
        if category not in PROCEDURE_CATEGORIES:
            return Response(
                {"error": f"Unknown procedure category: {category}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        category = self._get_category()
        if category not in PROCEDURE_CATEGORIES:
            return Response(
                {"error": f"Unknown procedure category: {category}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        request=ProcedureCreateSerializer,
        responses={201: ProcedureDetailSerializer},
    )
    def create(self, request, *args, **kwargs):
        category = self._get_category()
        if category not in PROCEDURE_CATEGORIES:
            return Response(
                {"error": f"Unknown procedure category: {category}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        ser = ProcedureCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        config = PROCEDURE_CATEGORIES[category]
        from apps.job.services.process_document_service import ProcessDocumentService

        # Merge category tags with any user-supplied tags
        tags = list(ser.validated_data.get("tags") or [])
        for tag in config.get("tags", []):
            if tag not in tags:
                tags.append(tag)

        doc = ProcessDocumentService().create_blank_document(
            document_type=config["document_type"],
            title=ser.validated_data["title"],
            document_number=ser.validated_data.get("document_number", ""),
            tags=tags,
            is_template=ser.validated_data.get("is_template", False),
            site_location=ser.validated_data.get("site_location", ""),
        )
        return Response(
            ProcedureDetailSerializer(doc).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request=ProcedureUpdateSerializer,
        responses=ProcedureDetailSerializer,
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        ser = ProcedureUpdateSerializer(instance, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ProcedureDetailSerializer(instance).data)

    @extend_schema(
        request=ProcedureUpdateSerializer,
        responses=ProcedureDetailSerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


# ─── Form ViewSet ─────────────────────────────────────────────────────────────


class FormViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD for form/register documents (fillable templates with entries, no Google Docs).

    Category is taken from the URL kwarg, e.g. /rest/forms/safety/.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOfficeStaff()]

    def get_serializer_class(self):
        if self.action == "list":
            return FormListSerializer
        if self.action == "create":
            return FormCreateSerializer
        if self.action in {"update", "partial_update"}:
            return FormUpdateSerializer
        return FormDetailSerializer

    def _get_category(self):
        return self.kwargs.get("category", "")

    def get_queryset(self):
        category = self._get_category()
        qs = _apply_category_filter(
            ProcessDocument.objects.all(), FORM_CATEGORIES, category
        )
        if qs is None:
            return ProcessDocument.objects.none()
        return _apply_common_filters(qs, self.request)

    @extend_schema(
        parameters=[
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
        category = self._get_category()
        if category not in FORM_CATEGORIES:
            return Response(
                {"error": f"Unknown form category: {category}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        category = self._get_category()
        if category not in FORM_CATEGORIES:
            return Response(
                {"error": f"Unknown form category: {category}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        request=FormCreateSerializer,
        responses={201: FormDetailSerializer},
    )
    def create(self, request, *args, **kwargs):
        category = self._get_category()
        if category not in FORM_CATEGORIES:
            return Response(
                {"error": f"Unknown form category: {category}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        ser = FormCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        config = FORM_CATEGORIES[category]
        from apps.job.services.process_document_service import ProcessDocumentService

        # Merge category tags with any user-supplied tags
        tags = list(ser.validated_data.get("tags") or [])
        # For tags_any categories, add only the primary tag (first in list) to new documents
        for tag in config.get("tags", config.get("tags_any", []))[:1]:
            if tag not in tags:
                tags.append(tag)

        doc = ProcessDocumentService().create_form_document(
            document_type=config["document_type"],
            title=ser.validated_data["title"],
            document_number=ser.validated_data.get("document_number", ""),
            tags=tags,
            is_template=ser.validated_data.get("is_template", False),
            form_schema=ser.validated_data.get("form_schema", {}),
        )
        return Response(FormDetailSerializer(doc).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=FormUpdateSerializer,
        responses=FormDetailSerializer,
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        ser = FormUpdateSerializer(instance, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(FormDetailSerializer(instance).data)

    @extend_schema(
        request=FormUpdateSerializer,
        responses=FormDetailSerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


# ─── Content View (unchanged, used by procedures) ─────────────────────────────


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
        responses=ProcedureDetailSerializer,
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
        return Response(ProcedureDetailSerializer(doc).data)


# ─── Entry ViewSet (used by forms) ────────────────────────────────────────────


class ProcessDocumentEntryViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD endpoints for ProcessDocumentEntry, nested under a form document.

    Endpoints:
    - GET    /rest/forms/<category>/<id>/entries/              - list entries
    - POST   /rest/forms/<category>/<id>/entries/              - create entry
    - PUT    /rest/forms/<category>/<id>/entries/<entry_id>/   - update entry
    - DELETE /rest/forms/<category>/<id>/entries/<entry_id>/   - delete entry
    """

    serializer_class = ProcessDocumentEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_document(self):
        return get_object_or_404(ProcessDocument, pk=self.kwargs["document_pk"])

    def get_queryset(self):
        return ProcessDocumentEntry.objects.filter(
            document_id=self.kwargs["document_pk"],
            is_active=True,
        ).order_by("-entry_date", "-created_at")

    def perform_destroy(self, instance):
        """Soft delete - set is_active=False instead of actually deleting."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @extend_schema(responses=ProcessDocumentEntrySerializer(many=True))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request=ProcessDocumentEntrySerializer,
        responses={201: ProcessDocumentEntrySerializer},
    )
    def create(self, request, *args, **kwargs):
        document = self.get_document()
        if document.document_type not in ("form", "register"):
            return Response(
                {"error": "Entries can only be added to form or register documents"},
                status=status.HTTP_400_BAD_REQUEST,
            )
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


# ─── JSA views (unchanged) ────────────────────────────────────────────────────


class JSAListView(APIView):
    """List all JSAs for a job."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=ProcedureListSerializer(many=True))
    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        jsas = ProcessDocument.objects.filter(job=job, tags__contains=["jsa"])
        return Response(ProcedureListSerializer(jsas, many=True).data)


class JSAGenerateView(APIView):
    """Generate a new JSA for a job."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(request=None, responses=ProcedureDetailSerializer)
    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        from apps.job.services.process_document_service import ProcessDocumentService

        jsa = ProcessDocumentService().generate_jsa(job)
        return Response(
            ProcedureDetailSerializer(jsa).data, status=status.HTTP_201_CREATED
        )


# ─── SWP/SOP Generate views (moved under /rest/procedures/safety/) ────────────


class SWPGenerateView(APIView):
    """Generate a new Safe Work Procedure."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(
        request=SWPGenerateRequestSerializer, responses=ProcedureDetailSerializer
    )
    def post(self, request):
        ser = SWPGenerateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.job.services.process_document_service import ProcessDocumentService

        swp = ProcessDocumentService().generate_swp(**ser.validated_data)
        return Response(
            ProcedureDetailSerializer(swp).data, status=status.HTTP_201_CREATED
        )


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
        request=SOPGenerateRequestSerializer, responses=ProcedureDetailSerializer
    )
    def post(self, request):
        ser = SOPGenerateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.job.services.process_document_service import ProcessDocumentService

        sop = ProcessDocumentService().generate_sop(**ser.validated_data)
        return Response(
            ProcedureDetailSerializer(sop).data, status=status.HTTP_201_CREATED
        )


# ─── Fill / Complete views (moved under /rest/forms/) ─────────────────────────


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
        responses=FormDetailSerializer,
    )
    def post(self, request, pk, **kwargs):
        try:
            from apps.job.services.process_document_service import (
                ProcessDocumentService,
            )

            record = ProcessDocumentService().fill_template(
                template_id=pk,
                job_id=request.data.get("job_id"),
            )
            return Response(
                FormDetailSerializer(record).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            persist_app_error(exc)
            raise


class ProcessDocumentCompleteView(APIView):
    """Mark a document as completed (read-only)."""

    permission_classes = [permissions.IsAuthenticated, IsOfficeStaff]

    @extend_schema(request=None, responses=FormDetailSerializer)
    def post(self, request, pk, **kwargs):
        try:
            from apps.job.services.process_document_service import (
                ProcessDocumentService,
            )

            doc = ProcessDocumentService().complete_document(pk)
            return Response(FormDetailSerializer(doc).data)
        except Exception as exc:
            persist_app_error(exc)
            raise


# ─── AI views (unchanged) ─────────────────────────────────────────────────────


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
