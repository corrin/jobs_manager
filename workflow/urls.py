"""
URL Configuration for Workflow App

URL Structure Patterns:
----------------------

1. Resource-based URL paths:
   - Primary resources have their own root path: /{resource}/
   - Examples: /xero/, /clients/, /invoices/, /job/, /kanban/

2. API Endpoints:
   - All API endpoints are prefixed with /api/
   - Follow pattern: /api/{resource}/{action}/
   - Examples: /api/xero/authenticate/, /api/clients/all/

3. Resource Actions:
   - List view: /{resource}/
   - Detail view: /{resource}/{id}/
   - Create: /{resource}/add/ or /api/{resource}/create/
   - Update: /{resource}/{id}/update/
   - Delete: /api/{resource}/{id}/delete/

4. Nested Resources:
   - Follow pattern: /{parent-resource}/{id}/{child-resource}/
   - Example: /job/{id}/workshop-pdf/

5. URL Names:
   - Use resource_action format
   - Examples: client_detail, job_create, invoice_update

6. Ordering:
   - URLs MUST be kept in strict alphabetical order by path
   - Group URLs logically (api/, resource roots) but maintain alphabetical order within each group
   - Comments may be used to denote logical groupings but do not break alphabetical ordering

Follow these patterns when adding new URLs to maintain consistency.
"""

import debug_toolbar
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from workflow.api import server
from workflow.api.reports.pnl import CompanyProfitAndLossReport
from workflow.views import (
    client_view,
    edit_job_view_ajax,
    kanban_view,
    staff_view,
    submit_quote_view,
    time_entry_view,
    time_overview_view,
    workshop_view,
    job_management_view,
)
from workflow.views.xero import xero_view
from workflow.views.job_file_view import JobFileView
from workflow.views.report_view import CompanyProfitAndLossView, ReportsIndexView
from workflow.views import password_views, stock_view, use_stock_view
from workflow.views.purchase_order_view import PurchaseOrderListView, PurchaseOrderCreateView, autosave_purchase_order_view
from workflow.views.delivery_receipt_view import DeliveryReceiptListView, DeliveryReceiptCreateView

urlpatterns = [
    # Redirect to Kanban board
    path("", RedirectView.as_view(url="/kanban/"), name="home"),
    
    # API endpoints
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
    path(
        "api/autosave-purchase-order/",
        autosave_purchase_order_view,
        name="autosave_purchase_order_api",
    ),
    path("api/clients/all/", client_view.all_clients, name="all_clients_api"),
    path("api/client-search/", client_view.ClientSearch, name="client_search_api"),
    path("api/client-detail/", client_view.client_detail, name="client_detail"),
    path("api/staff/all/", staff_view.StaffListAPIView.as_view(), name="all_staff_api"),
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
    # Stock APIs
    path(
        "api/stock/consume/",
        stock_view.consume_stock_api_view,
        name="consume_stock_api"
    ),
    path(
        "api/stock/create/",
        stock_view.create_stock_api_view,
        name="create_stock_api"
    ),
    path(
        "api/stock/<uuid:stock_id>/deactivate/",
        stock_view.deactivate_stock_api_view,
        name="deactivate_stock_api"
    ),
    # Stock Search API (for autocomplete)
    path(
        "api/stock/search/",
        stock_view.search_available_stock_api,
        name="search_stock_api"
    ),
    path(
        "api/job/advanced-search/",
        kanban_view.advanced_search,
        name="advanced-search"
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
        "api/job/toggle-pricing-type/",
        edit_job_view_ajax.toggle_pricing_type,
        name="toggle_pricing_type",
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
        "api/xero/authenticate/",
        xero_view.xero_authenticate,
        name="api_xero_authenticate",
    ),
    path(
        "api/xero/oauth/callback/",
        xero_view.xero_oauth_callback,
        name="xero_oauth_callback",
    ),
        path(
        "api/xero/disconnect/",
        xero_view.xero_disconnect,
        name="xero_disconnect",
    ),
    path(
        "api/xero/purchase-order/<uuid:purchase_order_id>/create/",
        xero_view.create_xero_purchase_order,
        name="create_xero_purchase_order",
    ),
    path(
        "api/xero/refresh/",
        xero_view.refresh_xero_data,
        name="refresh_xero_data",
    ),
    path(
        "api/xero/success/",
        xero_view.success_xero_connection,
        name="xero_success",
    ),
    path(
        "api/xero/sync-stream/",
        xero_view.stream_xero_sync,
        name="stream_xero_sync",
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
    path(
        "api/xero/sync-info/",
        xero_view.get_xero_sync_info,
        name="xero_sync_info",
    ),
    path(
        "api/xero/delete_purchase_order/<uuid:purchase_order_id>",  # <-- New URL
        xero_view.delete_xero_purchase_order,
        name="delete_xero_purchase_order",
    ),
    path(
        "api/xero/sync/",
        xero_view.start_xero_sync,
        name="synchronise_xero_data",
    ),
    # Other URL patterns
    path("clients/", client_view.ClientListView.as_view(), name="list_clients"),
    path(
        "client/<uuid:pk>/",
        client_view.ClientUpdateView.as_view(),
        name="update_client",
    ),
    path("client/add/", client_view.AddClient, name="add_client"),
    path("clients/unused/", client_view.UnusedClientsView.as_view(), name="unused_clients"),
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
    path(
        "timesheets/export_to_ims/",
        time_overview_view.TimesheetOverviewView.as_view(),
        name="timesheet_export_to_ims",
    ),
    # Edit timesheet entries for a specific day
    path(
        "timesheets/day/<str:date>/",
        time_overview_view.TimesheetDailyView.as_view(),
        name="timesheet_daily_view",
    ),
    path("xero/", xero_view.XeroIndexView.as_view(), name="xero_index"),
    path(
        "xero/sync-progress/",
        xero_view.xero_sync_progress_page,
        name="xero_sync_progress",
    ),
    path("xero/unused-clients/", client_view.UnusedClientsView.as_view(), name="xero_unused_clients"),

    # Login/Logout views
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Password reset views
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # Password change views
    path(
        "password_change/",
        password_views.SecurityPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
    # Purchase Order URLs with purchases prefix
    path('purchases/purchase-orders/', PurchaseOrderListView.as_view(), name='purchase_orders'),
    path('purchases/purchase-orders/new/', PurchaseOrderCreateView.as_view(), name='new_purchase_order'),
    path('purchases/purchase-orders/<uuid:pk>/', PurchaseOrderCreateView.as_view(), name='edit_purchase_order'),

    # Delivery Receipt URLs with purchases prefix
    path('purchases/delivery-receipts/', DeliveryReceiptListView.as_view(), name='delivery_receipts'),
    path('purchases/delivery-receipts/<uuid:pk>/', DeliveryReceiptCreateView.as_view(), name='edit_delivery_receipt'),
    
    # Stock Management URLs with purchases prefix
    path('purchases/use-stock/', use_stock_view.use_stock_view, name='use_stock'),
    
    # This URL doesn't match our naming pattern - need to fix.
    # Probably should be in api/internal?
    path(
        "staff/<uuid:staff_id>/get_rates/",
        staff_view.get_staff_rates,
        name="get_staff_rates",
    ),
    path("__debug__/", include(debug_toolbar.urls)),
]
