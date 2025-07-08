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
    kanban_view_api,
    workshop_view,
)
from apps.job.views.job_rest_views import get_company_defaults_api

app_name = "jobs"


urlpatterns = [
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
        "api/company_defaults/",
        get_company_defaults_api,
        name="company_defaults_api",
    ),
    path("api/job-files/", JobFileView.as_view(), name="job-files"),  # For POST/PUT
    path(
        "api/job-files/<int:job_number>", JobFileView.as_view(), name="get-job-file"
    ),  # To check if file already exists
    path(
        "api/job-files/<path:file_path>", JobFileView.as_view(), name="serve-job-file"
    ),  # For GET/download
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

urlpatterns += rest_urlpatterns
