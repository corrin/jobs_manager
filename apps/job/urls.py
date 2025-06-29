"""
URL Configuration for Job App

This module contains all URL patterns related to job management:
- Job CRUD operations
- Job events
- Job files
- Job status management
- etc.
"""

from django.urls import path

from apps.job.urls_rest import rest_urlpatterns
from apps.job.views import (
    ArchiveCompleteJobsViews,
    AssignJobView,
    JobFileView,
    edit_job_view_ajax,
    job_management_view,
    kanban_view_api,
    workshop_view,
)

app_name = "jobs"

urlpatterns = [
    # Job API endpoints
    path(
        "api/autosave-job/",
        edit_job_view_ajax.autosave_job_view,
        name="autosave_job_api",
    ),
    path("api/create-job/", edit_job_view_ajax.create_job_api, name="create_job_api"),
    path(
        "api/fetch_job_pricing/",
        edit_job_view_ajax.fetch_job_pricing_api,
        name="fetch_job_pricing_api",
    ),
    path(
        "api/fetch_status_values/",
        edit_job_view_ajax.api_fetch_status_values,
        name="fetch_status_values",
    ),
    path(
        "api/job/<uuid:job_id>/delete/",
        edit_job_view_ajax.delete_job,
        name="delete_job",
    ),
    path(
        "api/job/toggle-complex-job/",
        edit_job_view_ajax.toggle_complex_job,
        name="toggle_complex_job",
    ),
    path(
        "api/job/completed/",
        ArchiveCompleteJobsViews.ArchiveCompleteJobsListAPIView.as_view(),
        name="api_jobs_completed",
    ),
    path(
        "api/job/completed/archive",
        ArchiveCompleteJobsViews.ArchiveCompleteJobsAPIView.as_view(),
        name="api_jobs_archive",
    ),
    path(
        "api/job/<uuid:job_id>/assignment",
        AssignJobView.as_view(),
        name="api_job_assigment",
    ),
    path(
        "api/job-event/<uuid:job_id>/add-event/",
        edit_job_view_ajax.add_job_event,
        name="add-event",
    ),
    path("api/job-files/", JobFileView.as_view(), name="job-files"),  # For POST/PUT
    path(
        "api/job-files/<int:job_number>", JobFileView.as_view(), name="get-job-file"
    ),  # To check if file already exists
    path(
        "api/job-files/<path:file_path>", JobFileView.as_view(), name="serve-job-file"
    ),  # For GET/download
    path(
        "api/company_defaults/",
        edit_job_view_ajax.get_company_defaults_api,
        name="company_defaults_api",
    ),
    # Job view endpoints
    path("job/", edit_job_view_ajax.create_job_view, name="create_job"),
    path("job/<uuid:job_id>/", edit_job_view_ajax.edit_job_view_ajax, name="edit_job"),
    path(
        "job/<uuid:job_id>/workshop-pdf/",
        workshop_view.WorkshopPDFView.as_view(),
        name="workshop-pdf",
    ),
    path(
        "job/archive-complete",
        ArchiveCompleteJobsViews.ArchiveCompleteJobsTemplateView.as_view(),
        name="archive_complete_jobs",
    ),
    path("month-end/", job_management_view.month_end_view, name="month_end"),
    # New Kanban API endpoints
    path(
        "api/jobs/fetch-all/",
        kanban_view_api.fetch_all_jobs,
        name="api_fetch_all_jobs",
    ),
    path(
        "api/jobs/<str:job_id>/update-status/",
        kanban_view_api.update_job_status,
        name="api_update_job_status",
    ),
    path(
        "api/jobs/<uuid:job_id>/reorder/",
        kanban_view_api.reorder_job,
        name="api_reorder_job",
    ),
    path(
        "api/jobs/fetch/<str:status>/",
        kanban_view_api.fetch_jobs,
        name="api_fetch_jobs",
    ),
    path(
        "api/jobs/fetch-by-column/<str:column_id>/",
        kanban_view_api.fetch_jobs_by_column,
        name="api_fetch_jobs_by_column",
    ),
    path(
        "api/jobs/status-values/",
        kanban_view_api.fetch_status_values,
        name="api_fetch_status_values",
    ),
    path(
        "api/jobs/advanced-search/",
        kanban_view_api.advanced_search,
        name="api_advanced_search",
    ),
]

# Incluir URLs REST
urlpatterns += rest_urlpatterns
