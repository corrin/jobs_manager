"""
URLs REST para o módulo Job

Novas rotas REST seguindo padrões modernos para integração com frontend Vue.js
"""

from django.http import HttpResponse
from django.urls import path
from rest_framework import status

from apps.job.views.job_costing_views import JobCostSetView
from apps.job.views.job_costline_views import (
    CostLineCreateView,
    CostLineDeleteView,
    CostLineUpdateView,
)
from apps.job.views.job_file_upload import JobFileUploadView
from apps.job.views.job_file_view import JobFileThumbnailView, JobFileView
from apps.job.views.job_quote_chat_views import (
    JobQuoteChatHistoryView,
    JobQuoteChatMessageView,
)
from apps.job.views.job_rest_views import (
    JobAdjustmentEntryRestView,
    JobCreateRestView,
    JobDetailRestView,
    JobEventRestView,
    JobMaterialEntryRestView,
    JobTimeEntryRestView,
    JobToggleComplexRestView,
    JobTogglePricingMethodologyRestView,
)
from apps.job.views.modern_timesheet_views import (
    ModernTimesheetDayView,
    ModernTimesheetEntryView,
    ModernTimesheetJobView,
)
from apps.job.views.quote_import_views import QuoteImportStatusView
from apps.job.views.quote_sync_views import apply_quote, link_quote_sheet, preview_quote
from apps.job.views.workshop_view import WorkshopPDFView

# URLs for new REST views
rest_urlpatterns = [
    # Job CRUD operations (REST style)
    path("rest/jobs/", JobCreateRestView.as_view(), name="job_create_rest"),
    path(
        "rest/jobs/<uuid:job_id>/", JobDetailRestView.as_view(), name="job_detail_rest"
    ),
    # Job toggles
    path(
        "rest/jobs/toggle-complex/",
        JobToggleComplexRestView.as_view(),
        name="job_toggle_complex_rest",
    ),
    path(
        "rest/jobs/toggle-pricing-methodology/",
        JobTogglePricingMethodologyRestView.as_view(),
        name="job_toggle_pricing_methodology_rest",
    ),
    # Job events
    path(
        "rest/jobs/<uuid:job_id>/events/",
        JobEventRestView.as_view(),
        name="job_events_rest",
    ),
    # Job entries
    path(
        "rest/jobs/<uuid:job_id>/time-entries/",
        JobTimeEntryRestView.as_view(),
        name="job_time_entries_rest",
    ),
    path(
        "rest/jobs/<uuid:job_id>/material-entries/",
        JobMaterialEntryRestView.as_view(),
        name="job_material_entries_rest",
    ),
    path(
        "rest/jobs/<uuid:job_id>/adjustment-entries/",
        JobAdjustmentEntryRestView.as_view(),
        name="job_adjustment_entries_rest",
    ),
    # Job costing
    path(
        "rest/jobs/<uuid:pk>/cost_sets/<str:kind>/",
        JobCostSetView.as_view(),
        name="job_cost_set_rest",
    ),  # CostLine CRUD operations for modern timesheet
    path(
        "rest/jobs/<uuid:job_id>/cost_sets/actual/cost_lines/",
        CostLineCreateView.as_view(),
        name="costline_create_rest",
    ),
    path(
        "rest/jobs/<uuid:job_id>/cost_sets/<str:kind>/cost_lines/",
        CostLineCreateView.as_view(),
        name="costline_create_any_rest",
    ),
    path(
        "rest/cost_lines/<int:cost_line_id>/",
        CostLineUpdateView.as_view(),
        name="costline_update_rest",
    ),
    path(
        "rest/cost_lines/<int:cost_line_id>/delete/",
        CostLineDeleteView.as_view(),
        name="costline_delete_rest",
    ),
    # Modern Timesheet API endpoints
    path(
        "rest/timesheet/entries/",
        ModernTimesheetEntryView.as_view(),
        name="modern_timesheet_entry_rest",
    ),
    path(
        "rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/",
        ModernTimesheetDayView.as_view(),
        name="modern_timesheet_day_rest",
    ),
    path(
        "rest/timesheet/jobs/<uuid:job_id>/",
        ModernTimesheetJobView.as_view(),
        name="modern_timesheet_job_rest",
    ),
    # Workshop PDF
    path(
        "rest/jobs/<uuid:job_id>/workshop-pdf/",
        WorkshopPDFView.as_view(),
        name="workshop-pdf",
    ),
    # Job files
    path(
        "rest/jobs/files/upload/", JobFileUploadView.as_view(), name="job_file_upload"
    ),
    path(
        "rest/jobs/files/<int:job_number>/",
        JobFileView.as_view(),
        name="job_files_list",
    ),
    path("rest/jobs/files/", JobFileView.as_view(), name="job_file_base"),
    path(
        "rest/jobs/files/<path:file_path>/",
        JobFileView.as_view(),
        name="job_file_download",
    ),
    path(
        "rest/jobs/files/<int:file_path>/",
        JobFileView.as_view(),
        name="job_file_delete",
    ),
    path(
        "rest/jobs/files/<uuid:file_id>/thumbnail/",
        JobFileThumbnailView.as_view(),
        name="job_file_thumbnail",
    ),
    # Quote Import (NEW - Google Sheets sync)
    path("rest/jobs/<uuid:pk>/quote/link/", link_quote_sheet, name="quote_link_sheet"),
    path("rest/jobs/<uuid:pk>/quote/preview/", preview_quote, name="quote_preview"),
    path("rest/jobs/<uuid:pk>/quote/apply/", apply_quote, name="quote_apply"),
    # Quote Import (DEPRECATED - file upload based)
    path(
        "rest/jobs/<uuid:job_id>/quote/import/preview/",
        lambda request, *args, **kwargs: HttpResponse(
            '{"error": "This endpoint has been deprecated. Use /quote/link/, /quote/preview/, and /quote/apply/ instead."}',
            status=status.HTTP_410_GONE,
            content_type="application/json",
        ),
        name="quote_import_preview_deprecated",
    ),
    path(
        "rest/jobs/<uuid:job_id>/quote/import/",
        lambda request, *args, **kwargs: HttpResponse(
            '{"error": "This endpoint has been deprecated. Use /quote/link/, /quote/preview/, and /quote/apply/ instead."}',
            status=status.HTTP_410_GONE,
            content_type="application/json",
        ),
        name="quote_import_deprecated",
    ),
    path(
        "rest/jobs/<uuid:job_id>/quote/status/",
        QuoteImportStatusView.as_view(),
        name="quote_import_status",
    ),
    # Job Quote Chat APIs
    path(
        "api/jobs/<uuid:job_id>/quote-chat/",
        JobQuoteChatHistoryView.as_view(),
        name="job_quote_chat_history",
    ),
    path(
        "api/jobs/<uuid:job_id>/quote-chat/<str:message_id>/",
        JobQuoteChatMessageView.as_view(),
        name="job_quote_chat_message",
    ),
]
