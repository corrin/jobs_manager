from django.urls import path
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.process.views.form_viewsets import (
    FORM_CATEGORIES,
    FormEntryViewSet,
    FormFillView,
    FormViewSet,
)
from apps.process.views.procedure_viewsets import (
    PROCEDURE_CATEGORIES,
    AIGenerateControlsView,
    AIGenerateHazardsView,
    AIImproveDocumentView,
    AIImproveSectionView,
    JSAGenerateView,
    JSAListView,
    ProcedureContentView,
    ProcedureViewSet,
    SOPGenerateView,
    SWPGenerateView,
)


class CategoriesView(APIView):
    """Return available categories for procedures and forms."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=inline_serializer(
            "CategoriesResponse",
            fields={
                "procedures": serializers.ListField(child=serializers.CharField()),
                "forms": serializers.ListField(child=serializers.CharField()),
            },
        ),
    )
    def get(self, request):
        return Response(
            {
                "procedures": list(PROCEDURE_CATEGORIES.keys()),
                "forms": list(FORM_CATEGORIES.keys()),
            }
        )


rest_urlpatterns = [
    # ─── Categories (discovery endpoint for frontend navigation) ────────────
    path("rest/categories/", CategoriesView.as_view(), name="process_categories"),
    # ─── Procedures (written docs, Google Doc-backed) ───────────────────────
    # Generation endpoints must come BEFORE the <str:category> patterns
    path(
        "rest/procedures/safety/generate-sop/",
        SOPGenerateView.as_view(),
        name="sop_generate",
    ),
    path(
        "rest/procedures/safety/generate-swp/",
        SWPGenerateView.as_view(),
        name="swp_generate",
    ),
    path(
        "rest/procedures/<str:category>/",
        ProcedureViewSet.as_view({"get": "list", "post": "create"}),
        name="procedure_list",
    ),
    path(
        "rest/procedures/<str:category>/<uuid:pk>/",
        ProcedureViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="procedure_detail",
    ),
    path(
        "rest/procedures/<str:category>/<uuid:pk>/content/",
        ProcedureContentView.as_view(),
        name="procedure_content",
    ),
    # ─── Forms (definitions with entries) ──────────────────────────────────
    path(
        "rest/forms/<str:category>/",
        FormViewSet.as_view({"get": "list", "post": "create"}),
        name="form_list",
    ),
    path(
        "rest/forms/<str:category>/<uuid:pk>/",
        FormViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="form_detail",
    ),
    path(
        "rest/forms/<str:category>/<uuid:pk>/fill/",
        FormFillView.as_view(),
        name="form_fill",
    ),
    path(
        "rest/forms/<str:category>/<uuid:document_pk>/entries/",
        FormEntryViewSet.as_view({"get": "list", "post": "create"}),
        name="form_entries",
    ),
    path(
        "rest/forms/<str:category>/<uuid:document_pk>/entries/<uuid:pk>/",
        FormEntryViewSet.as_view(
            {"put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="form_entry_detail",
    ),
    # ─── JSA (nested under jobs) ──────────────────────────────────────────
    path(
        "rest/jobs/<uuid:job_id>/jsa/",
        JSAListView.as_view(),
        name="jsa_list",
    ),
    path(
        "rest/jobs/<uuid:job_id>/jsa/generate/",
        JSAGenerateView.as_view(),
        name="jsa_generate",
    ),
    # ─── Safety AI ────────────────────────────────────────────────────────
    path(
        "rest/safety-ai/generate-hazards/",
        AIGenerateHazardsView.as_view(),
        name="ai_generate_hazards",
    ),
    path(
        "rest/safety-ai/generate-controls/",
        AIGenerateControlsView.as_view(),
        name="ai_generate_controls",
    ),
    path(
        "rest/safety-ai/improve-section/",
        AIImproveSectionView.as_view(),
        name="ai_improve_section",
    ),
    path(
        "rest/safety-ai/improve-document/",
        AIImproveDocumentView.as_view(),
        name="ai_improve_document",
    ),
]
