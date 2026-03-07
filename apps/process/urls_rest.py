from django.urls import path

from apps.process.views.process_document_viewsets import (
    AIGenerateControlsView,
    AIGenerateHazardsView,
    AIImproveDocumentView,
    AIImproveSectionView,
    FormViewSet,
    JSAGenerateView,
    JSAListView,
    ProcedureViewSet,
    ProcessDocumentCompleteView,
    ProcessDocumentContentView,
    ProcessDocumentEntryViewSet,
    ProcessDocumentFillView,
    SOPGenerateView,
    SWPGenerateView,
)

rest_urlpatterns = [
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
        ProcessDocumentContentView.as_view(),
        name="procedure_content",
    ),
    # ─── Forms (fillable templates with entries) ──────────────────────────
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
        ProcessDocumentFillView.as_view(),
        name="form_fill",
    ),
    path(
        "rest/forms/<str:category>/<uuid:pk>/complete/",
        ProcessDocumentCompleteView.as_view(),
        name="form_complete",
    ),
    path(
        "rest/forms/<str:category>/<uuid:document_pk>/entries/",
        ProcessDocumentEntryViewSet.as_view({"get": "list", "post": "create"}),
        name="form_entries",
    ),
    path(
        "rest/forms/<str:category>/<uuid:document_pk>/entries/<uuid:pk>/",
        ProcessDocumentEntryViewSet.as_view(
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
