import debug_toolbar
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from workflow.api import server
from workflow.api.reports.pnl import CompanyProfitAndLossReport
from workflow.views import (
    client_view,
    edit_job_view_ajax,
    invoice_view,
    kanban_view,
    staff_view,
    submit_quote_view,
    time_entry_view,
    time_overview_view,
    workshop_view,
    xero_view,
)
from workflow.views.job_file_view import JobFileView
from workflow.views.report_view import CompanyProfitAndLossView, ReportsIndexView

urlpatterns = [
    # Redirect to Kanban board
    path("", RedirectView.as_view(url="/kanban/"), name="home"),
    path(
        "api/autosave-job/",
        edit_job_view_ajax.autosave_job_view,
        name="autosave_job_api",
    ),
    path(
        "api/autosave-timesheet/",
        time_entry_view.autosave_timesheet_view,
        name="autosave_timesheet-api",
    ),
    path("api/clients/all/", client_view.all_clients, name="all_clients_api"),
    path("api/client-search/", client_view.ClientSearch, name="client_search_api"),
    path(
        "api/quote/<uuid:job_id>/pdf-preview/",
        submit_quote_view.generate_quote_pdf,
        name="generate_quote_pdf",
    ),
    path(
        "api/quote/<uuid:job_id>/send-email/",
        submit_quote_view.send_quote_email,
        name="send_quote_email",
    ),
    path("api/get-env-variable/", server.get_env_variable, name="get_env_variable"),
    # path("api/get-job/", edit_job_view_ajax.get_job_api, name="get_job_api"),
    path("api/create-job/", edit_job_view_ajax.create_job_api, name="create_job_api"),
    path(
        "api/fetch_job_pricing/",
        edit_job_view_ajax.fetch_job_pricing_api,
        name="fetch_job_pricing_api",
    ),
    # API URLs
    path(
        "api/reports/company-profit-loss/",
        CompanyProfitAndLossReport.as_view(),
        name="api-company-profit-loss",
    ),
    path(
        "api/fetch_status_values/",
        edit_job_view_ajax.api_fetch_status_values,
        name="fetch_status_values",
    ),
    path(
        "api/job-event/<uuid:job_id>/add-event/",
        edit_job_view_ajax.add_job_event,
        name="add-event",
    ),
    path("api/job-files/", JobFileView.as_view(), name="job-files"),  # For POST/upload
    path(
        "api/job-files/<int:job_number>", JobFileView.as_view(), name="get-job-file"
    ),  # To check if file already exists
    path(
        "api/job-files/<path:file_path>", JobFileView.as_view(), name="serve-job-file"
    ),  # For GET/download
    path(
        "api/xero/authenticate/",
        xero_view.xero_authenticate,
        name="authenticate_xero",
    ),
    path(
        "api/xero/oauth/callback/",
        xero_view.xero_oauth_callback,
        name="oauth_callback_xero",
    ),
    path(
        "api/xero/success/",
        xero_view.success_xero_connection,
        name="success_xero_connection",
    ),
    path(
        "api/xero/refresh/",
        xero_view.refresh_xero_data,
        name="refresh_xero_data",
    ),
    path(
        "api/xero/disconnect/",
        xero_view.xero_disconnect,
        name="xero_disconnect",
    ),
    path(
        "api/xero/create_invoice/<uuid:job_id>",
        xero_view.create_xero_invoice,
        name="create_invoice",
    ),
    path(
        "api/xero/delete_invoice/<uuid:job_id>",
        xero_view.delete_xero_invoice,
        name="delete_invoice",
    ),
    path(
        "api/xero/create_quote/<uuid:job_id>",
        xero_view.create_xero_quote,
        name="create_quote",
    ),
    path(
        "api/xero/delete_quote/<uuid:job_id>",
        xero_view.delete_xero_quote,
        name="delete_quote",
    ),
    # Other URL patterns
    path("clients/", client_view.ClientListView.as_view(), name="list_clients"),
    path(
        "client/<uuid:pk>/",
        client_view.ClientUpdateView.as_view(),
        name="update_client",
    ),
    path("client/add/", client_view.AddClient, name="add_client"),
    path("invoices/", invoice_view.InvoiceListView.as_view(), name="list_invoices"),
    path(
        "invoices/<uuid:pk>",
        invoice_view.InvoiceUpdateView.as_view(),
        name="update_invoice",
    ),
    # Job URLs
    # Job Pricing URLs
    # Entry URLs
    path("job/", edit_job_view_ajax.create_job_view, name="create_job"),
    path("job/<uuid:job_id>/", edit_job_view_ajax.edit_job_view_ajax, name="edit_job"),
    path(
        "job/<uuid:job_id>/workshop-pdf/",
        workshop_view.WorkshopPDFView.as_view(),
        name="workshop-pdf",
    ),
    path("month-end/", edit_job_view_ajax.process_month_end, name="month_end"),
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
    path("reports/", ReportsIndexView.as_view(), name="reports_index"),
    path(
        "reports/company-profit-loss/",
        CompanyProfitAndLossView.as_view(),
        name="company-profit-loss-report",
    ),
    path(
        "api/company_defaults/",
        edit_job_view_ajax.get_company_defaults_api,
        name="company_defaults_api",
    ),
    path(
        "timesheets/day/<str:date>/<uuid:staff_id>/",
        time_entry_view.TimesheetEntryView.as_view(),
        name="timesheet_entry",
    ),
    path(
        "timesheets/overview/",
        time_overview_view.TimesheetOverviewView.as_view(),
        name="timesheet_overview",
    ),
    path(
        "timesheets/overview/<str:start_date>/",
        time_overview_view.TimesheetOverviewView.as_view(),
        name="timesheet_overview_with_date",
    ),
    # Edit timesheet entries for a specific day
    path(
        "timesheets/day/<str:date>/",
        time_overview_view.TimesheetDailyView.as_view(),
        name="timesheet_daily_view",
    ),
    path("xero/", xero_view.XeroIndexView.as_view(), name="xero_index"),
    # Login/Logout views
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # This URL doesn't match our naming pattern - need to fix.
    # Probably should be in api/internal?
    path(
        "staff/<uuid:staff_id>/get_rates/",
        staff_view.get_staff_rates,
        name="get_staff_rates",
    ),
    path("__debug__/", include(debug_toolbar.urls)),  # Add this line
]
