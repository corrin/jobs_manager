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

from job.views import (
    edit_job_view_ajax,
    kanban_view,
    workshop_view,
    job_management_view,
    ArchiveCompleteJobsViews,
    AssignJobView,
    JobFileView
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
        "api/job/advanced-search/", kanban_view.advanced_search, name="advanced-search"
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
        "api/job/toggle-pricing-methodology/",
        edit_job_view_ajax.toggle_pricing_methodology,
        name="toggle_pricing_methodology",
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
    path(
        "api/job/<uuid:job_id>/create-linked-quote/",
        edit_job_view_ajax.create_linked_quote_api,
        name="create_linked_quote_api",
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
    path(
        "jobs/<uuid:job_id>/update_status/",
        kanban_view.update_job_status,
        name="update_job_status",
    ),
    # Kanban views
    path("kanban/", kanban_view.kanban_view, name="view_kanban"),
    path(
        "kanban/fetch_jobs/<str:status>/",
        kanban_view.fetch_jobs,
        name="fetch_jobs",
    ),
]
