from django.http import HttpResponse
from django.urls import path
from rest_framework import status

from apps.job.views.data_quality_report_views import ArchivedJobsComplianceView
from apps.job.views.job_costing_views import JobCostSetView, JobQuoteRevisionView
from apps.job.views.job_costline_views import (
    CostLineCreateView,
    CostLineDeleteView,
    CostLineUpdateView,
)
from apps.job.views.job_file_upload import JobFileUploadView
from apps.job.views.job_file_view import JobFileThumbnailView, JobFileView
from apps.job.views.job_quote_chat_api import JobQuoteChatInteractionView
from apps.job.views.job_quote_chat_views import (
    JobQuoteChatHistoryView,
    JobQuoteChatMessageView,
)
from apps.job.views.job_rest_views import (
    JobBasicInformationRestView,
    JobCostSummaryRestView,
    JobCreateRestView,
    JobDeltaRejectionListRestView,
    JobDetailRestView,
    JobEventListRestView,
    JobEventRestView,
    JobHeaderRestView,
    JobInvoicesRestView,
    JobQuoteAcceptRestView,
    JobQuoteRestView,
    JobStatusChoicesRestView,
    JobTimelineRestView,
    JobUndoChangeRestView,
    WeeklyMetricsRestView,
)
from apps.job.views.modern_timesheet_views import (
    ModernTimesheetDayView,
    ModernTimesheetEntryView,
    ModernTimesheetJobView,
)
from apps.job.views.month_end_rest_view import MonthEndRestView
from apps.job.views.quote_import_views import QuoteImportStatusView
from apps.job.views.quote_sync_views import (
    ApplyQuoteAPIView,
    LinkQuoteSheetAPIView,
    PreviewQuoteAPIView,
)
from apps.job.views.workshop_view import WorkshopPDFView

# URLs for new REST views
rest_urlpatterns = [
    # Job CRUD operations (REST style)
    path("rest/jobs/", JobCreateRestView.as_view(), name="job_create_rest"),
    path("rest/month-end/", MonthEndRestView.as_view(), name="month_end_rest"),
    path(
        "rest/jobs/<uuid:job_id>/", JobDetailRestView.as_view(), name="job_detail_rest"
    ),
    path(
        "rest/jobs/<uuid:job_id>/undo-change/",
        JobUndoChangeRestView.as_view(),
        name="job_undo_change_rest",
    ),
    # Job header (essential info only)
    path(
        "rest/jobs/<uuid:job_id>/header/",
        JobHeaderRestView.as_view(),
        name="job_header_rest",
    ),
    # Job basic information (description, delivery date, order number, notes)
    path(
        "rest/jobs/<uuid:job_id>/basic-info/",
        JobBasicInformationRestView.as_view(),
        name="job_basic_info_rest",
    ),
    # Job events (list)
    path(
        "rest/jobs/<uuid:job_id>/events/",
        JobEventListRestView.as_view(),
        name="job_events_list_rest",
    ),
    # Job delta rejections (readonly)
    path(
        "rest/jobs/delta-rejections/",
        JobDeltaRejectionListRestView.as_view(),
        name="job_delta_rejections_rest",
    ),
    # Job events (create)
    path(
        "rest/jobs/<uuid:job_id>/events/create/",
        JobEventRestView.as_view(),
        name="job_events_rest",
    ),
    # Job timeline (unified events + cost lines)
    path(
        "rest/jobs/<uuid:job_id>/timeline/",
        JobTimelineRestView.as_view(),
        name="job_timeline_rest",
    ),
    # Job invoices and quotes
    path(
        "rest/jobs/<uuid:job_id>/invoices/",
        JobInvoicesRestView.as_view(),
        name="job_invoices_rest",
    ),
    path(
        "rest/jobs/<uuid:job_id>/quote/",
        JobQuoteRestView.as_view(),
        name="job_quote_rest",
    ),
    # Job cost summary
    path(
        "rest/jobs/<uuid:job_id>/costs/summary/",
        JobCostSummaryRestView.as_view(),
        name="job_cost_summary_rest",
    ),
    # Job status choices
    path(
        "rest/jobs/status-choices/",
        JobStatusChoicesRestView.as_view(),
        name="job_status_choices_rest",
    ),
    # Quote acceptance endpoint
    path(
        "rest/jobs/<uuid:job_id>/quote/accept/",
        JobQuoteAcceptRestView.as_view(),
        name="job_quote_accept_rest",
    ),
    # Job entries
    # Use CostLine endpoints instead of JobTimeEntryRestView,
    # JobMaterialEntryRestView, JobAdjustmentEntryRestView
    # Job costing
    path(
        "rest/jobs/<uuid:pk>/cost_sets/<str:kind>/",
        JobCostSetView.as_view(),
        name="job_cost_set_rest",
    ),
    # Quote revision endpoint - creates new revision by archiving current data
    path(
        "rest/jobs/<uuid:job_id>/cost_sets/quote/revise/",
        JobQuoteRevisionView.as_view(),
        name="job_quote_revision_rest",
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
        "rest/cost_lines/<str:cost_line_id>/",
        CostLineUpdateView.as_view(),
        name="costline_update_rest",
    ),
    path(
        "rest/cost_lines/<str:cost_line_id>/delete/",
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
        "rest/jobs/files/<uuid:file_id>/thumbnail/",
        JobFileThumbnailView.as_view(),
        name="job_file_thumbnail",
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
    # Quote Import (NEW - Google Sheets sync)
    path(
        "rest/jobs/<uuid:pk>/quote/link/",
        LinkQuoteSheetAPIView.as_view(),
        name="quote_link_sheet",
    ),
    path(
        "rest/jobs/<uuid:pk>/quote/preview/",
        PreviewQuoteAPIView.as_view(),
        name="quote_preview",
    ),
    path(
        "rest/jobs/<uuid:pk>/quote/apply/",
        ApplyQuoteAPIView.as_view(),
        name="quote_apply",
    ),
    # Quote Import
    path(
        "rest/jobs/<uuid:job_id>/quote/import/preview/",
        lambda request, *args, **kwargs: HttpResponse(
            (
                '{"error": "This endpoint has been deprecated. '
                'Use /quote/link/, /quote/preview/, and /quote/apply/ instead."}'
            ),
            status=status.HTTP_410_GONE,
            content_type="application/json",
        ),
        name="quote_import_preview_deprecated",
    ),
    path(
        "rest/jobs/<uuid:job_id>/quote/import/",
        lambda request, *args, **kwargs: HttpResponse(
            (
                '{"error": "This endpoint has been deprecated. '
                'Use /quote/link/, /quote/preview/, and /quote/apply/ instead."}'
            ),
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
    # Weekly Metrics for WeeklyTimesheetView
    path(
        "rest/jobs/weekly-metrics/",
        WeeklyMetricsRestView.as_view(),
        name="weekly_metrics_rest",
    ),
    # Job Quote Chat APIs
    path(
        "api/jobs/<uuid:job_id>/quote-chat/",
        JobQuoteChatHistoryView.as_view(),
        name="job_quote_chat_history",
    ),
    # AI-powered chat interaction (LLM call + tool execution)
    # Must be ABOVE the generic <message_id> route to avoid being
    # captured by it.
    path(
        "api/jobs/<uuid:job_id>/quote-chat/interaction/",
        JobQuoteChatInteractionView.as_view(),
        name="job_quote_chat_interaction",
    ),
    path(
        "api/jobs/<uuid:job_id>/quote-chat/<str:message_id>/",
        JobQuoteChatMessageView.as_view(),
        name="job_quote_chat_message",
    ),
    # Data Quality Reports
    path(
        "rest/data-quality/archived-jobs-compliance/",
        ArchivedJobsComplianceView.as_view(),
        name="data_quality_archived_jobs_compliance",
    ),
]
